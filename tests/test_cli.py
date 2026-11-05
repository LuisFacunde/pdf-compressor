import importlib
from pathlib import Path
from src import cli
from src.adapters.sqlite_history import SqliteHistory
from src.settings import Settings
from tests.helpers import FakeEngine, write_pdf


def test_settings_defaults_have_no_side_effects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import src.settings as settings_module

    importlib.reload(settings_module)
    settings = settings_module.Settings.from_env({})

    assert settings.timeout == 300 and settings.min_output_size == 1024
    assert settings.ghostscript_cmd is None
    assert settings.history_db.name == "historico.db"
    # carregar as configurações não pode criar arquivos nem pastas
    assert list(tmp_path.iterdir()) == []


def test_settings_from_env_overrides(tmp_path):
    settings = Settings.from_env(
        {
            "PDF_COMPRESSOR_INPUT_DIR": str(tmp_path / "in"),
            "PDF_COMPRESSOR_OUTPUT_DIR": str(tmp_path / "out"),
            "PDF_COMPRESSOR_HISTORY_DB": str(tmp_path / "h.db"),
            "PDF_COMPRESSOR_LOG_FILE": str(tmp_path / "l.log"),
            "PDF_COMPRESSOR_GS_CMD": "gs-custom",
            "PDF_COMPRESSOR_TIMEOUT": "42",
            "PDF_COMPRESSOR_MIN_OUTPUT_SIZE": "10",
        }
    )

    assert settings.input_dir == tmp_path / "in"
    assert settings.output_dir == tmp_path / "out"
    assert settings.history_db == tmp_path / "h.db"
    assert settings.log_file == tmp_path / "l.log"
    assert settings.ghostscript_cmd == "gs-custom"
    assert settings.timeout == 42 and settings.min_output_size == 10


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        input_dir=tmp_path / "in",
        output_dir=tmp_path / "out",
        history_db=tmp_path / "h.db",
        log_file=tmp_path / "l.log",
    )


def run_cli(tmp_path, *argv, engine=None):
    return cli.main(
        list(argv),
        settings=make_settings(tmp_path),
        engine=engine or FakeEngine(size=2048),
        configure_logging=False,
    )


def test_cli_history_is_empty_initially(tmp_path, capsys):
    assert run_cli(tmp_path, "--history") == 0
    assert "Histórico vazio." in capsys.readouterr().out


def test_cli_single_compresses_and_records_history(tmp_path, capsys):
    source = write_pdf(tmp_path / "exame.pdf")
    output = tmp_path / "exame_comprimido.pdf"

    code = run_cli(tmp_path, "--single", str(source), str(output), "-q", "ebook")

    assert code == 0 and output.exists()
    rows = SqliteHistory(tmp_path / "h.db").query()
    assert len(rows) == 1
    assert rows[0]["mode"] == "single" and rows[0]["quality"] == "ebook"
    assert rows[0]["status"] == "compressed"
    assert "Compressão concluída" in capsys.readouterr().out


def test_cli_single_failure_returns_error_code(tmp_path, capsys):
    code = run_cli(
        tmp_path, "--single", str(tmp_path / "nope.pdf"), str(tmp_path / "o.pdf")
    )

    assert code == 1
    assert "Falha na compressão" in capsys.readouterr().out
    assert SqliteHistory(tmp_path / "h.db").query()[0]["status"] == "failed"


def test_cli_rejects_invalid_jobs(tmp_path, capsys):
    assert run_cli(tmp_path, "-j", "0") == 1
    assert "--jobs" in capsys.readouterr().out


def test_cli_batch_in_place_end_to_end_with_fake_engine(tmp_path):
    settings = make_settings(tmp_path)
    settings.input_dir.mkdir()
    pdf = write_pdf(settings.input_dir / "a.pdf", 4096)

    code = cli.main(
        ["--in-place", "-j", "1", "--no-progress", "-i", str(settings.input_dir)],
        settings=settings,
        engine=FakeEngine(size=2048),
        configure_logging=False,
    )
    assert code == 0
    assert pdf.stat().st_size == 2048
