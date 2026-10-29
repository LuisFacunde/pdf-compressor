import os

from src.history import (
    STATUS_COMPRESSED,
    STATUS_FAILED,
    STATUS_KEPT_ORIGINAL,
    get_history,
    is_already_compressed,
    record_compression,
)


def test_in_place_history_detects_unchanged_file_with_same_quality(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"x" * 2048)
    database = tmp_path / "history.db"

    record_compression(
        source,
        status=STATUS_COMPRESSED,
        mode="in_place",
        quality="ebook",
        original_size=4096,
        compressed_size=source.stat().st_size,
        db_path=database,
    )

    assert is_already_compressed(source, "ebook", db_path=database)
    assert not is_already_compressed(source, "screen", db_path=database)


def test_in_place_history_stops_matching_after_file_changes(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"x" * 2048)
    database = tmp_path / "history.db"

    record_compression(
        source,
        status=STATUS_COMPRESSED,
        mode="in_place",
        quality="ebook",
        original_size=4096,
        compressed_size=source.stat().st_size,
        db_path=database,
    )

    stat = source.stat()
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
    assert not is_already_compressed(source, "ebook", db_path=database)

    source.write_bytes(b"changed")
    assert not is_already_compressed(source, "ebook", db_path=database)


def test_kept_original_is_skipped_but_failed_attempt_is_not(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"x" * 2048)
    database = tmp_path / "history.db"

    record_compression(
        source,
        status=STATUS_KEPT_ORIGINAL,
        mode="in_place",
        quality="ebook",
        original_size=source.stat().st_size,
        compressed_size=source.stat().st_size,
        db_path=database,
    )
    assert is_already_compressed(source, "ebook", db_path=database)

    record_compression(
        source,
        status=STATUS_FAILED,
        mode="in_place",
        quality="screen",
        original_size=source.stat().st_size,
        error="compression error",
        db_path=database,
    )
    assert not is_already_compressed(source, "screen", db_path=database)


def test_history_folder_filter_and_limit_return_latest_rows(tmp_path):
    first_folder = tmp_path / "first"
    second_folder = tmp_path / "second"
    first_folder.mkdir()
    second_folder.mkdir()
    first_file = first_folder / "first.pdf"
    second_file = second_folder / "second.pdf"
    first_file.write_bytes(b"first")
    second_file.write_bytes(b"second")
    database = tmp_path / "history.db"

    record_compression(
        first_file,
        status=STATUS_COMPRESSED,
        mode="output_dir",
        quality="screen",
        db_path=database,
    )
    record_compression(
        second_file,
        status=STATUS_COMPRESSED,
        mode="output_dir",
        quality="ebook",
        db_path=database,
    )
    record_compression(
        first_file,
        status=STATUS_FAILED,
        mode="output_dir",
        quality="printer",
        error="retry failed",
        db_path=database,
    )

    latest = get_history(limit=1, db_path=database)
    filtered = get_history(folder=str(first_folder), db_path=database)

    assert len(latest) == 1
    assert latest[0]["quality"] == "printer"
    assert [row["quality"] for row in filtered] == ["printer", "screen"]
    assert all(row["folder"] == str(first_folder.resolve()) for row in filtered)
