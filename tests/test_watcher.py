from concurrent.futures import Future
from pathlib import Path

import src.history as history
import src.watcher as watcher_module
from src.history import STATUS_COMPRESSED, STATUS_FAILED, get_history
from src.watcher import DirectoryWatcher


class ImmediateExecutor:
    def __init__(self, max_workers=1):
        self.max_workers = max_workers

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def submit(self, fn, *args, **kwargs):
        future = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except Exception as exc:
            future.set_exception(exc)
        return future


def _redirect_history(monkeypatch, database: Path):
    orig_record = history.record_compression
    orig_check = history.is_already_compressed

    def record_in_db(*args, **kwargs):
        return orig_record(*args, db_path=database, **kwargs)

    def check_in_db(*args, **kwargs):
        return orig_check(*args, db_path=database, **kwargs)

    monkeypatch.setattr(watcher_module, "record_compression", record_in_db)
    monkeypatch.setattr(watcher_module, "is_already_compressed", check_in_db)


def test_watcher_compresses_new_pdf_in_document_subfolder_and_avoids_loop(
    tmp_path, monkeypatch
):
    database = tmp_path / "history.db"
    _redirect_history(monkeypatch, database)

    patient_dir = tmp_path / "exames" / "999970"
    patient_dir.mkdir(parents=True)
    pdf_file = patient_dir / "retinografia.pdf"
    pdf_file.write_bytes(b"a" * 4096)

    calls = []

    def fake_wrapper(args):
        target = args[0]
        calls.append(target)
        target.write_bytes(b"b" * 2048)
        stat = target.stat()
        return {
            "file_name": target.name,
            "file_path": str(target),
            "status": STATUS_COMPRESSED,
            "mode": "in_place",
            "output_path": None,
            "success": True,
            "error": None,
            "original_size": 4096,
            "compressed_size": stat.st_size,
            "file_mtime_ns": stat.st_mtime_ns,
        }

    monkeypatch.setattr(watcher_module, "compress_single_file_wrapper", fake_wrapper)

    watcher = DirectoryWatcher(
        patient_dir.parent,
        quality="ebook",
        max_workers=1,
        settle_time=0.0,
        poll_interval=0.05,
    )

    with ImmediateExecutor() as executor:
        # 1º ciclo: detecta e comprime na própria pasta do documento
        assert watcher.run_once(executor, full_scan=True) == (1, 0)
        # 2º ciclo: arquivo já está no histórico com mesmo mtime/tamanho -> não entra em loop
        assert watcher.run_once(executor, full_scan=True) == (0, 0)

    assert calls == [pdf_file]
    assert pdf_file.read_bytes() == b"b" * 2048
    rows = get_history(db_path=database)
    assert len(rows) == 1
    assert rows[0]["status"] == STATUS_COMPRESSED
    assert rows[0]["folder"] == str(patient_dir.resolve())


def test_watcher_waits_for_settle_time_while_file_is_being_written(
    tmp_path, monkeypatch
):
    database = tmp_path / "history.db"
    _redirect_history(monkeypatch, database)

    watch_dir = tmp_path / "exames"
    watch_dir.mkdir()
    pdf_file = watch_dir / "novo.pdf"
    pdf_file.write_bytes(b"part1" * 400)

    def fake_wrapper(args):
        target = args[0]
        target.write_bytes(b"c" * 1500)
        stat = target.stat()
        return {
            "file_name": target.name,
            "file_path": str(target),
            "status": STATUS_COMPRESSED,
            "mode": "in_place",
            "output_path": None,
            "success": True,
            "error": None,
            "original_size": args[5],
            "compressed_size": stat.st_size,
            "file_mtime_ns": stat.st_mtime_ns,
        }

    monkeypatch.setattr(watcher_module, "compress_single_file_wrapper", fake_wrapper)

    watcher = DirectoryWatcher(
        watch_dir,
        quality="ebook",
        max_workers=1,
        settle_time=3.0,
        poll_interval=0.1,
    )

    with ImmediateExecutor() as executor:
        # t=10.0s: primeira vez que vê o arquivo -> aguarda estabilizar
        assert watcher.run_once(executor, full_scan=True, now=10.0) == (0, 0)

        # t=11.5s: arquivo ainda está crescendo pela rede -> reinicia contagem de estabilização
        pdf_file.write_bytes(b"part1_and_part2" * 400)
        assert watcher.run_once(executor, full_scan=True, now=11.5) == (0, 0)

        # t=13.0s: apenas 1.5s desde a última escrita (< 3.0s) -> ainda aguarda
        assert watcher.run_once(executor, full_scan=True, now=13.0) == (0, 0)

        # t=14.6s: 3.1s estável -> comprime agora!
        assert watcher.run_once(executor, full_scan=True, now=14.6) == (1, 0)


def test_watcher_ignores_tmp_files_and_does_not_retry_unchanged_failed_file(
    tmp_path, monkeypatch
):
    database = tmp_path / "history.db"
    _redirect_history(monkeypatch, database)

    watch_dir = tmp_path / "exames"
    watch_dir.mkdir()
    temp_file = watch_dir / "em_andamento.pdf.tmp"
    temp_file.write_bytes(b"x" * 2048)
    corrupted = watch_dir / "corrompido.pdf"
    corrupted.write_bytes(b"not a pdf")

    attempts = []

    def fail_wrapper(args):
        target = args[0]
        attempts.append(target)
        return {
            "file_name": target.name,
            "file_path": str(target),
            "status": STATUS_FAILED,
            "mode": "in_place",
            "output_path": None,
            "success": False,
            "error": "Ghostscript error",
            "original_size": target.stat().st_size,
            "compressed_size": 0,
            "file_mtime_ns": None,
        }

    monkeypatch.setattr(watcher_module, "compress_single_file_wrapper", fail_wrapper)

    watcher = DirectoryWatcher(
        watch_dir, quality="ebook", max_workers=1, settle_time=0.0
    )

    with ImmediateExecutor() as executor:
        # 1ª rodada: tenta comprimir corrompido.pdf (e ignora .pdf.tmp)
        assert watcher.run_once(executor, full_scan=True) == (0, 1)
        # 2ª rodada: como corrompido.pdf não mudou no disco, não fica repetindo sem parar
        assert watcher.run_once(executor, full_scan=True) == (0, 0)

    assert attempts == [corrupted]


def test_watcher_skips_pdf_already_compressed_in_another_folder(tmp_path, monkeypatch):
    database = tmp_path / "history.db"
    _redirect_history(monkeypatch, database)

    server_dir = tmp_path / "servidor"
    watch_dir = tmp_path / "teste_compressor"
    server_dir.mkdir()
    watch_dir.mkdir()

    # Simula arquivo que já foi comprimido anteriormente no servidor
    server_pdf = server_dir / "exame_antigo.pdf"
    server_pdf.write_bytes(b"pdf-ja-comprimido" * 120)
    history.record_compression(
        server_pdf,
        status=STATUS_COMPRESSED,
        mode="in_place",
        quality="prepress",
        original_size=5000000,
        compressed_size=server_pdf.stat().st_size,
        db_path=database,
    )

    # Usuário copia esse PDF já comprimido para a pasta observada pelo --watch
    copied_pdf = watch_dir / "exame_antigo.pdf"
    copied_pdf.write_bytes(server_pdf.read_bytes())

    called = []
    monkeypatch.setattr(
        watcher_module,
        "compress_single_file_wrapper",
        lambda args: called.append(args),
    )

    watcher = DirectoryWatcher(
        watch_dir, quality="prepress", max_workers=1, settle_time=3.0
    )

    with ImmediateExecutor() as executor:
        assert watcher.run_once(executor, full_scan=True) == (0, 0)

    assert called == []

