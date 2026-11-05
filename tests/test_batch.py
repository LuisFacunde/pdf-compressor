from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
import pytest
from src.models import Mode, Status
from src.services import BatchCompressor, FileCompressor
from tests.helpers import FakeEngine, InMemoryHistory, write_pdf


def make_batch(engine=None, history=None, executor_factory=ThreadPoolExecutor):
    return BatchCompressor(
        FileCompressor(engine or FakeEngine(size=2048)),
        history,
        executor_factory=executor_factory,
    )


def test_batch_output_dir_compresses_and_records_history(tmp_path):
    for name in ("a.pdf", "b.pdf"):
        write_pdf(tmp_path / name)
    history = InMemoryHistory()
    output_dir = tmp_path / "output"
    seen = []

    summary = make_batch(history=history).run(
        tmp_path, output_dir, "ebook", max_workers=2, on_result=seen.append
    )

    assert (summary.successful, summary.failed) == (2, 0)
    assert summary.discovered == 2 and summary.submitted == 2 and summary.skipped == 0
    assert summary.total_original_size == 8192
    assert summary.total_compressed_size == 4096
    assert (output_dir / "a_compress.pdf").exists()
    assert (output_dir / "b_compress.pdf").exists()
    assert len(seen) == 2
    assert {r.file_name for r, _ in history.records} == {"a.pdf", "b.pdf"}
    assert all(q == "ebook" for _, q in history.records)
    assert all(r.mode == Mode.OUTPUT_DIR for r, _ in history.records)


def test_batch_counts_failures_and_records_them(tmp_path):
    write_pdf(tmp_path / "a.pdf")
    history = InMemoryHistory()
    # saída vazia => falha
    summary = make_batch(FakeEngine(size=0), history).run(
        tmp_path, tmp_path / "out", "ebook", max_workers=1
    )

    assert (summary.successful, summary.failed) == (0, 1)
    assert summary.failures[0][0] == "a.pdf"
    assert history.records[0][0].status == Status.FAILED


def test_batch_in_place_skips_already_compressed_unless_forced(tmp_path):
    done = write_pdf(tmp_path / "done.pdf")
    (tmp_path / "sub").mkdir()
    write_pdf(tmp_path / "sub" / "new.pdf")
    history = InMemoryHistory()
    history.done.add((done, "ebook"))

    summary = make_batch(history=history).run(
        tmp_path, tmp_path, "ebook", in_place=True, max_workers=1
    )
    assert summary.skipped == 1 and summary.submitted == 1
    assert summary.successful == 1  # new.pdf (recursivo)
    assert done.read_bytes() == b"a" * 4096

    history2 = InMemoryHistory()
    history2.done.add((done, "ebook"))
    forced = make_batch(history=history2).run(
        tmp_path, tmp_path, "ebook", in_place=True, force=True, max_workers=1
    )
    assert forced.skipped == 0


def test_skip_is_not_applied_outside_in_place_mode(tmp_path):
    source = write_pdf(tmp_path / "a.pdf")
    history = InMemoryHistory()
    history.done.add((source, "ebook"))

    summary = make_batch(history=history).run(
        tmp_path, tmp_path / "out", "ebook", max_workers=1
    )

    assert summary.skipped == 0 and summary.successful == 1


def test_history_failures_do_not_break_the_batch(tmp_path):
    write_pdf(tmp_path / "a.pdf")

    class BrokenHistory(InMemoryHistory):
        def record(self, result, quality):
            raise RuntimeError("db locked")

        def is_already_compressed(self, file_path, quality):
            raise RuntimeError("db locked")

    summary = make_batch(history=BrokenHistory()).run(
        tmp_path, tmp_path, "ebook", in_place=True, max_workers=1
    )

    assert (summary.successful, summary.failed) == (1, 0)


def test_unexpected_worker_exception_becomes_failed_result(tmp_path):
    write_pdf(tmp_path / "a.pdf")
    history = InMemoryHistory()

    class ExplodingExecutor(ThreadPoolExecutor):
        def submit(self, fn, *args, **kwargs):
            future = Future()
            future.set_exception(RuntimeError("worker died"))
            return future

    summary = make_batch(history=history, executor_factory=ExplodingExecutor).run(
        tmp_path, tmp_path / "out", "ebook", max_workers=1
    )

    assert (summary.successful, summary.failed) == (0, 1)
    assert "worker died" in summary.failures[0][1]
    assert history.records[0][0].status == Status.FAILED


def test_no_pdfs_found_returns_empty_summary(tmp_path):
    summary = make_batch().run(tmp_path, tmp_path / "out", "ebook", max_workers=1)
    assert summary.discovered == 0 and summary.successful == 0 and summary.failed == 0


def test_invalid_worker_count_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        make_batch().run(tmp_path, tmp_path, "ebook", max_workers=0)


def test_batch_compresses_while_discovering_pdfs(tmp_path, monkeypatch):
    first = write_pdf(tmp_path / "first.pdf")
    second = write_pdf(tmp_path / "second.pdf")
    history = InMemoryHistory()

    def lazy_pdf_paths():
        yield first
        # o primeiro arquivo já deve ter sido processado antes do segundo ser descoberto
        assert [Path(r.file_path) for r, _ in history.records] == [first]
        yield second

    def lazy_glob(path, pattern):
        assert path == tmp_path and pattern == "*.pdf"
        return lazy_pdf_paths()

    class ImmediateExecutor:
        def __init__(self, max_workers):
            assert max_workers == 1

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def submit(self, function, *args):
            future = Future()
            future.set_result(function(*args))
            return future

    monkeypatch.setattr(Path, "glob", lazy_glob)

    summary = make_batch(history=history, executor_factory=ImmediateExecutor).run(
        tmp_path, tmp_path / "output", "ebook", max_workers=1
    )

    assert (summary.successful, summary.failed) == (2, 0)
    assert [Path(r.file_path) for r, _ in history.records] == [first, second]
