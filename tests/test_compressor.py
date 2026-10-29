import pytest
import subprocess
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
