from concurrent.futures import Future
from pathlib import Path
import subprocess

import pytest

import src.compressor as compressor
from src.compressor import compress_single_file_wrapper
from src.compressor import check_ghostscript_available, compress_pdf
from src.history import (
    STATUS_COMPRESSED,
    STATUS_FAILED,
    STATUS_KEPT_ORIGINAL,
)

requires_gs = pytest.mark.skipif(
    not check_ghostscript_available(), reason="Ghostscript não instalado"
)

MINIMAL_PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 24 Tf 20 100 Td (Teste PDF) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
trailer<</Root 1 0 R/Size 6>>
%%EOF
"""


@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "sample.pdf"
    path.write_bytes(MINIMAL_PDF)
    return path


@requires_gs
@pytest.mark.parametrize("q", ["screen", "ebook", "printer", "prepress", "default"])
def test_compress(tmp_path, sample_pdf, q):
    out = tmp_path / f"out_{q}.pdf"
    success, error = compress_pdf(sample_pdf, out, quality=q)
    assert success, error
    assert out.exists() and out.stat().st_size > 0


def test_missing_input_returns_error(tmp_path):
    success, error = compress_pdf(tmp_path / "nao_existe.pdf", tmp_path / "out.pdf")
    assert not success
    assert error is not None
    assert "does not exist" in error


def test_non_pdf_input_returns_error(tmp_path, monkeypatch):
    source = tmp_path / "document.txt"
    source.write_text("not a PDF")
    monkeypatch.setattr(compressor, "check_ghostscript_available", lambda: True)

    success, error = compress_pdf(source, tmp_path / "out.pdf")

    assert not success
    assert error is not None
    assert "not a PDF" in error
    assert not (tmp_path / "out.pdf").exists()


def test_existing_output_is_not_overwritten_by_default(tmp_path, sample_pdf):
    output = tmp_path / "result.pdf"
    original_output = b"existing output"
    output.write_bytes(original_output)

    success, error = compress_pdf(sample_pdf, output)

    assert not success
    assert error is not None
    assert "already exists" in error
    assert output.read_bytes() == original_output


def test_missing_ghostscript_returns_error(tmp_path, sample_pdf, monkeypatch):
    monkeypatch.setattr(compressor, "check_ghostscript_available", lambda: False)

    success, error = compress_pdf(sample_pdf, tmp_path / "result.pdf")

    assert not success
    assert error is not None
    assert "Ghostscript not found" in error


def test_timeout_returns_error(tmp_path, sample_pdf, monkeypatch):
    monkeypatch.setattr(compressor, "check_ghostscript_available", lambda: True)

    def timeout(command, **kwargs):
        assert kwargs["timeout"] == 300
        raise subprocess.TimeoutExpired(cmd=command, timeout=300)

    monkeypatch.setattr(compressor.subprocess, "run", timeout)

    success, error = compress_pdf(sample_pdf, tmp_path / "result.pdf")

    assert not success
    assert error is not None
    assert "timeout" in error.lower()


def test_ghostscript_error_returns_stderr(tmp_path, sample_pdf, monkeypatch):
    monkeypatch.setattr(compressor, "check_ghostscript_available", lambda: True)

    def fail(command, **kwargs):
        assert kwargs["check"] is True
        raise subprocess.CalledProcessError(
            returncode=1, cmd=command, stderr="invalid PDF"
        )

    monkeypatch.setattr(compressor.subprocess, "run", fail)

    success, error = compress_pdf(sample_pdf, tmp_path / "result.pdf")

    assert not success
    assert error is not None
    assert "invalid PDF" in error


def test_empty_output_is_treated_as_failure(tmp_path, sample_pdf, monkeypatch):
    monkeypatch.setattr(compressor, "check_ghostscript_available", lambda: True)

    def return_empty_success(command, **kwargs):
        assert kwargs["check"] is True
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        compressor.subprocess,
        "run",
        return_empty_success,
    )
    output = tmp_path / "result.pdf"

    success, error = compress_pdf(sample_pdf, output)

    assert not success
    assert error == "Compression failed, output file is missing or empty."
    assert not output.exists()


def test_in_place_replaces_original_with_smaller_output(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    original = b"a" * 4096
    source.write_bytes(original)

    def compress_to_smaller_file(input_path, output_path, quality, overwrite):
        assert input_path == source
        assert quality == "ebook"
        assert overwrite is True
        output_path.write_bytes(b"b" * 2048)
        return True, None

    monkeypatch.setattr(compressor, "compress_pdf", compress_to_smaller_file)

    result = compress_single_file_wrapper((source, tmp_path, "ebook", False, True))

    assert result["success"]
    assert result["status"] == STATUS_COMPRESSED
    assert source.read_bytes() == b"b" * 2048
    assert not source.with_name("source.pdf.tmp").exists()


def test_in_place_keeps_original_when_output_is_not_smaller(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    original = b"a" * 2048
    source.write_bytes(original)

    def compress_to_same_size(input_path, output_path, quality, overwrite):
        assert input_path == source
        assert quality == "ebook"
        assert overwrite is True
        output_path.write_bytes(b"b" * 2048)
        return True, None

    monkeypatch.setattr(compressor, "compress_pdf", compress_to_same_size)

    result = compress_single_file_wrapper((source, tmp_path, "ebook", False, True))

    assert result["success"]
    assert result["status"] == STATUS_KEPT_ORIGINAL
    assert source.read_bytes() == original
    assert not source.with_name("source.pdf.tmp").exists()


def test_in_place_rejects_too_small_output_and_keeps_original(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    original = b"a" * 2048
    source.write_bytes(original)

    def compress_to_tiny_file(input_path, output_path, quality, overwrite):
        assert input_path == source
        assert quality == "ebook"
        assert overwrite is True
        output_path.write_bytes(b"bad")
        return True, None

    monkeypatch.setattr(compressor, "compress_pdf", compress_to_tiny_file)

    result = compress_single_file_wrapper((source, tmp_path, "ebook", False, True))

    assert not result["success"]
    assert result["status"] == STATUS_FAILED
    assert "too small" in result["error"]
    assert source.read_bytes() == original
    assert not source.with_name("source.pdf.tmp").exists()


def test_batch_writes_compressed_pdf_and_history(tmp_path, sample_pdf, monkeypatch):
    import src.history as history

    if not check_ghostscript_available():
        pytest.skip("Ghostscript não instalado")

    database = tmp_path / "history" / "compressions.db"
    record = history.record_compression

    def record_in_test_database(*args, **kwargs):
        record(*args, db_path=database, **kwargs)

    monkeypatch.setattr(compressor, "record_compression", record_in_test_database)
    output_dir = tmp_path / "output"

    successful, failed = compressor.compress_pdf_batch(
        sample_pdf.parent,
        output_dir,
        quality="ebook",
        max_workers=1,
        show_progress=False,
    )

    output = output_dir / "sample_compress.pdf"
    assert (successful, failed) == (1, 0)
    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF-")

    rows = history.get_history(db_path=database)
    assert len(rows) == 1
    assert rows[0]["file_path"] == str(sample_pdf.resolve())
    assert rows[0]["output_path"] == str(output)
    assert rows[0]["status"] == "compressed"
    assert rows[0]["original_size"] == sample_pdf.stat().st_size
    assert rows[0]["compressed_size"] == output.stat().st_size
    assert rows[0]["error"] is None


def test_batch_compresses_while_discovering_pdfs(tmp_path, monkeypatch):
    first_pdf = tmp_path / "first.pdf"
    second_pdf = tmp_path / "second.pdf"
    first_pdf.write_bytes(b"first PDF")
    second_pdf.write_bytes(b"second PDF")
    recorded_files = []
    progress_updates = []
    database = tmp_path / "history.db"

    class ProgressBarWithoutTotal:
        def __init__(self, **kwargs):
            assert "total" not in kwargs

        def __bool__(self):
            raise TypeError("bool() undefined when iterable == total == None")

        def update(self, amount):
            progress_updates.append(amount)

        def close(self):
            pass

    def lazy_pdf_paths():
        yield first_pdf
        assert recorded_files == [first_pdf.resolve()]
        yield second_pdf

    def lazy_glob(path, pattern):
        assert path == tmp_path
        assert pattern == "*.pdf"
        return lazy_pdf_paths()

    class ImmediateExecutor:
        def __init__(self, max_workers):
            assert max_workers == 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, _exc_value, _traceback):
            assert exc_type is None
            assert _exc_value is None
            assert _traceback is None
            return False

        def submit(self, function, args):
            future = Future()
            future.set_result(function(args))
            return future

    def fake_compression(args):
        pdf_file = args[0]
        return {
            "file_name": pdf_file.name,
            "file_path": str(pdf_file),
            "status": STATUS_COMPRESSED,
            "mode": "output_dir",
            "output_path": None,
            "success": True,
            "error": None,
            "original_size": pdf_file.stat().st_size,
            "compressed_size": pdf_file.stat().st_size,
        }

    def fake_history_record(file_path, **kwargs):
        assert kwargs["status"] == STATUS_COMPRESSED
        recorded_files.append(Path(file_path).resolve())
        history.record_compression(file_path, db_path=database, **kwargs)

    import src.history as history

    monkeypatch.setattr(Path, "glob", lazy_glob)
    monkeypatch.setattr(
        compressor.concurrent.futures,
        "ProcessPoolExecutor",
        ImmediateExecutor,
    )
    monkeypatch.setattr(compressor, "compress_single_file_wrapper", fake_compression)
    monkeypatch.setattr(compressor, "record_compression", fake_history_record)
    monkeypatch.setattr(compressor, "tqdm", ProgressBarWithoutTotal)

    successful, failed = compressor.compress_pdf_batch(
        tmp_path,
        tmp_path / "output",
        max_workers=1,
        show_progress=True,
    )

    assert (successful, failed) == (2, 0)
    assert recorded_files == [first_pdf.resolve(), second_pdf.resolve()]
    assert progress_updates == [1, 1]
    rows = history.get_history(db_path=database)
    assert len(rows) == 2
    assert {row["file_path"] for row in rows} == {
        str(first_pdf.resolve()),
        str(second_pdf.resolve()),
    }
    assert all(row["status"] == STATUS_COMPRESSED for row in rows)


def test_failed_compression_can_be_recorded_in_history(tmp_path):
    from src.history import get_history, record_compression

    source = tmp_path / "broken.pdf"
    source.write_bytes(b"not a valid PDF")
    database = tmp_path / "history.db"

    record_compression(
        source,
        status=STATUS_FAILED,
        mode="single",
        quality="prepress",
        original_size=source.stat().st_size,
        error="invalid PDF",
        db_path=database,
    )

    rows = get_history(db_path=database)
    assert len(rows) == 1
    assert rows[0]["status"] == STATUS_FAILED
    assert rows[0]["error"] == "invalid PDF"
    assert rows[0]["reduction_percent"] == 0
    assert rows[0]["file_mtime_ns"] is None
