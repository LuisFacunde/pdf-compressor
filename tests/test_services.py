import os
import pytest
from src.ports import EngineError
from src.models import Mode, Status
from src.services import FileCompressor
from tests.helpers import FailingEngine, FakeEngine, write_pdf


def test_compress_to_writes_destination_without_leftovers(tmp_path):
    source = write_pdf(tmp_path / "a.pdf")
    destination = tmp_path / "out" / "a_compress.pdf"

    result = FileCompressor(FakeEngine(size=2048)).compress_to(
        source, destination, "ebook"
    )

    assert result.success and result.status == Status.COMPRESSED
    assert result.mode == Mode.OUTPUT_DIR
    assert result.output_path == str(destination)
    assert result.compressed_size == 2048
    assert destination.read_bytes() == b"b" * 2048
    assert source.stat().st_size == 4096
    assert not destination.with_name("a_compress.pdf.tmp").exists()


def test_missing_input_returns_error(tmp_path):
    result = FileCompressor(FakeEngine()).compress_to(
        tmp_path / "nao_existe.pdf", tmp_path / "out.pdf", "ebook"
    )
    assert not result.success
    assert "does not exist" in result.error


def test_non_pdf_input_returns_error(tmp_path):
    source = tmp_path / "document.txt"
    source.write_text("not a PDF")
    engine = FakeEngine()

    result = FileCompressor(engine).compress_to(source, tmp_path / "out.pdf", "ebook")

    assert not result.success
    assert "not a PDF" in result.error
    assert engine.calls == []
    assert not (tmp_path / "out.pdf").exists()


def test_existing_output_is_not_overwritten_by_default(tmp_path):
    source = write_pdf(tmp_path / "a.pdf")
    output = tmp_path / "result.pdf"
    output.write_bytes(b"existing output")
    engine = FakeEngine()

    result = FileCompressor(engine).compress_to(source, output, "ebook")

    assert not result.success
    assert "already exists" in result.error
    assert output.read_bytes() == b"existing output"
    assert engine.calls == []


def test_overwrite_replaces_existing_output(tmp_path):
    source = write_pdf(tmp_path / "a.pdf")
    output = tmp_path / "result.pdf"
    output.write_bytes(b"old")

    result = FileCompressor(FakeEngine(size=2048)).compress_to(
        source, output, "ebook", overwrite=True
    )

    assert result.success
    assert output.read_bytes() == b"b" * 2048


def test_engine_failure_keeps_existing_output_and_cleans_temp(tmp_path):
    source = write_pdf(tmp_path / "a.pdf")
    output = tmp_path / "result.pdf"
    output.write_bytes(b"previous good output")

    result = FileCompressor(FailingEngine("invalid PDF")).compress_to(
        source, output, "ebook", overwrite=True
    )

    assert not result.success and result.status == Status.FAILED
    assert result.error == "invalid PDF"
    assert output.read_bytes() == b"previous good output"
    assert not output.with_name("result.pdf.tmp").exists()


def test_unexpected_engine_exception_is_reported(tmp_path):
    source = write_pdf(tmp_path / "a.pdf")

    result = FileCompressor(FakeEngine(error=RuntimeError("kaput"))).compress_to(
        source, tmp_path / "out.pdf", "ebook"
    )

    assert not result.success
    assert "Unexpected error" in result.error and "kaput" in result.error


def test_empty_output_is_treated_as_failure(tmp_path):
    source = write_pdf(tmp_path / "a.pdf")
    output = tmp_path / "result.pdf"

    result = FileCompressor(FakeEngine(size=0)).compress_to(source, output, "ebook")

    assert not result.success
    assert result.error == "Compression failed, output file is missing or empty."
    assert not output.exists()


def test_in_place_replaces_original_with_smaller_output(tmp_path):
    source = write_pdf(tmp_path / "source.pdf", 4096)
    engine = FakeEngine(size=2048)

    result = FileCompressor(engine).compress_in_place(source, "ebook")

    assert result.success and result.status == Status.COMPRESSED
    assert result.mode == Mode.IN_PLACE
    assert result.original_size == 4096 and result.compressed_size == 2048
    assert source.read_bytes() == b"b" * 2048
    assert not source.with_name("source.pdf.tmp").exists()
    assert engine.calls[0][0] == source and engine.calls[0][2] == "ebook"


def test_in_place_keeps_original_when_output_is_not_smaller(tmp_path):
    source = write_pdf(tmp_path / "source.pdf", 2048)

    result = FileCompressor(FakeEngine(size=2048)).compress_in_place(source, "ebook")

    assert result.success and result.status == Status.KEPT_ORIGINAL
    assert source.read_bytes() == b"a" * 2048
    assert not source.with_name("source.pdf.tmp").exists()


def test_in_place_rejects_too_small_output_and_keeps_original(tmp_path):
    source = write_pdf(tmp_path / "source.pdf", 4096)

    result = FileCompressor(FakeEngine(size=3)).compress_in_place(source, "ebook")

    assert not result.success and result.status == Status.FAILED
    assert "too small" in result.error
    assert source.read_bytes() == b"a" * 4096
    assert not source.with_name("source.pdf.tmp").exists()


def test_in_place_engine_failure_keeps_original(tmp_path):
    source = write_pdf(tmp_path / "source.pdf", 4096)

    result = FileCompressor(FailingEngine("gs crashed")).compress_in_place(
        source, "ebook"
    )

    assert not result.success and result.error == "gs crashed"
    assert source.read_bytes() == b"a" * 4096
    assert not source.with_name("source.pdf.tmp").exists()


def test_in_place_replace_failure_keeps_original_and_cleans_temp(tmp_path, monkeypatch):
    source = write_pdf(tmp_path / "source.pdf", 4096)

    def deny(*args, **kwargs):
        raise PermissionError("file is locked")

    monkeypatch.setattr(os, "replace", deny)

    result = FileCompressor(FakeEngine(size=2048)).compress_in_place(source, "ebook")

    assert not result.success
    assert "Failed to replace original file" in result.error
    assert source.read_bytes() == b"a" * 4096
    assert not source.with_name("source.pdf.tmp").exists()


def test_in_place_removes_stale_temp_before_compressing(tmp_path):
    source = write_pdf(tmp_path / "source.pdf", 4096)
    stale = source.with_name("source.pdf.tmp")
    stale.write_bytes(b"leftover from a crashed run")

    result = FileCompressor(FakeEngine(size=2048)).compress_in_place(source, "ebook")

    assert result.success
    assert not stale.exists()


def test_engine_error_is_an_exception_type():
    assert issubclass(EngineError, Exception)


@pytest.mark.parametrize("size", [1024, 1025])
def test_in_place_min_output_size_boundary(tmp_path, size):
    source = write_pdf(tmp_path / "source.pdf", 4096)

    result = FileCompressor(
        FakeEngine(size=size), min_output_size=1024
    ).compress_in_place(source, "ebook")

    assert result.success is (size > 1024)
