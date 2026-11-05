import pytest
import subprocess
from src.adapters import ghostscript as gs_module
from src.adapters.ghostscript import GhostscriptEngine
from src.adapters.sqlite_history import SqliteHistory
from src.models import CompressionResult, Mode, Status
from src.ports import EngineError
from src.services import FileCompressor
from tests.helpers import write_pdf

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

requires_gs = pytest.mark.skipif(
    not GhostscriptEngine().is_available(), reason="Ghostscript não instalado"
)


def make_engine(monkeypatch, run):
    engine = GhostscriptEngine(command="gs", timeout=300)
    engine._available = True
    monkeypatch.setattr(gs_module.subprocess, "run", run)
    return engine


def test_missing_ghostscript_raises_engine_error(tmp_path, monkeypatch):
    def not_found(command, **kwargs):
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(gs_module.subprocess, "run", not_found)
    engine = GhostscriptEngine(command="gs-inexistente")

    assert not engine.is_available()
    with pytest.raises(EngineError, match="Ghostscript not found"):
        engine.compress(tmp_path / "a.pdf", tmp_path / "b.pdf", "ebook")


def test_timeout_raises_engine_error(tmp_path, monkeypatch):
    def timeout(command, **kwargs):
        assert kwargs["timeout"] == 300
        raise subprocess.TimeoutExpired(cmd=command, timeout=300)

    engine = make_engine(monkeypatch, timeout)
    with pytest.raises(EngineError, match="(?i)timeout"):
        engine.compress(tmp_path / "a.pdf", tmp_path / "b.pdf", "ebook")


def test_ghostscript_error_includes_stderr(tmp_path, monkeypatch):
    def fail(command, **kwargs):
        assert kwargs["check"] is True
        raise subprocess.CalledProcessError(
            returncode=1, cmd=command, stderr="invalid PDF"
        )

    engine = make_engine(monkeypatch, fail)
    with pytest.raises(EngineError, match="invalid PDF"):
        engine.compress(tmp_path / "a.pdf", tmp_path / "b.pdf", "ebook")


def test_command_line_uses_pdfwrite_and_quality(tmp_path, monkeypatch):
    captured = {}

    def run(command, **kwargs):
        captured["cmd"] = command
        return subprocess.CompletedProcess(command, 0)

    engine = make_engine(monkeypatch, run)
    source, destination = tmp_path / "a.pdf", tmp_path / "b.pdf"
    engine.compress(source, destination, "screen")

    cmd = captured["cmd"]
    assert cmd[0] == "gs"
    assert "-sDEVICE=pdfwrite" in cmd and "-dPDFSETTINGS=/screen" in cmd
    assert "-dSAFER" in cmd
    assert f"-sOutputFile={destination}" in cmd and cmd[-1] == str(source)


@requires_gs
@pytest.mark.integration
@pytest.mark.parametrize(
    "quality", ["screen", "ebook", "printer", "prepress", "default"]
)
def test_real_ghostscript_generates_pdf(tmp_path, quality):
    source = tmp_path / "sample.pdf"
    source.write_bytes(MINIMAL_PDF)
    destination = tmp_path / f"out_{quality}.pdf"

    result = FileCompressor(GhostscriptEngine()).compress_to(
        source, destination, quality
    )

    assert result.success, result.error
    assert destination.read_bytes().startswith(b"%PDF-")


def test_sqlite_history_records_and_queries(tmp_path):
    source = write_pdf(tmp_path / "a.pdf", 2048)
    history = SqliteHistory(tmp_path / "hist" / "h.db")
    ok = CompressionResult(
        file_name="a.pdf",
        file_path=str(source),
        status=Status.COMPRESSED,
        mode=Mode.IN_PLACE,
        success=True,
        original_size=4096,
        compressed_size=source.stat().st_size,
    )
    failed = CompressionResult(
        file_name="b.pdf",
        file_path=str(tmp_path / "b.pdf"),
        status=Status.FAILED,
        mode=Mode.OUTPUT_DIR,
        success=False,
        original_size=10,
        error="invalid PDF",
    )

    history.record(ok, "ebook")
    history.record(failed, "ebook")

    assert history.is_already_compressed(source, "ebook")
    assert not history.is_already_compressed(source, "screen")
    rows = history.query()
    assert [r["status"] for r in rows] == ["failed", "compressed"]
    assert rows[0]["error"] == "invalid PDF" and rows[0]["file_mtime_ns"] is None


@requires_gs
@pytest.mark.integration
def test_end_to_end_batch_with_real_ghostscript_and_sqlite(tmp_path):
    from src.services import BatchCompressor

    (tmp_path / "in").mkdir()
    (tmp_path / "in" / "sample.pdf").write_bytes(MINIMAL_PDF)
    history = SqliteHistory(tmp_path / "h.db")
    batch = BatchCompressor(FileCompressor(GhostscriptEngine()), history)

    summary = batch.run(tmp_path / "in", tmp_path / "out", "ebook", max_workers=1)

    assert (summary.successful, summary.failed) == (1, 0)
    assert (tmp_path / "out" / "sample_compress.pdf").read_bytes().startswith(b"%PDF-")
    rows = history.query()
    assert len(rows) == 1 and rows[0]["status"] == "compressed"
