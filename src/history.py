import os
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
from .config import HISTORY_DB
from contextlib import contextmanager
from typing import Dict, Iterator, List, Optional, Set

STATUS_COMPRESSED = "compressed"
STATUS_KEPT_ORIGINAL = "kept_original"
STATUS_FAILED = "failed"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS compressions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    folder TEXT NOT NULL,
    file_path TEXT NOT NULL,
    output_path TEXT,
    mode TEXT NOT NULL,
    quality TEXT NOT NULL,
    status TEXT NOT NULL,
    original_size INTEGER,
    compressed_size INTEGER,
    reduction_percent REAL,
    error TEXT,
    file_mtime_ns INTEGER,
    compressed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_compressions_path ON compressions(file_path);
CREATE INDEX IF NOT EXISTS idx_compressions_folder ON compressions(folder);
CREATE INDEX IF NOT EXISTS idx_compressions_lookup
    ON compressions(file_path, mode, quality);
"""

_local = threading.local()


def _normalize_path(path: Path) -> str:
    return os.path.abspath(os.fspath(path))


def _get_connection(db_path: Path) -> sqlite3.Connection:
    conns: Dict[str, sqlite3.Connection] = getattr(_local, "conns", None)
    if conns is None:
        conns = {}
        _local.conns = conns

    initialized: Set[str] = getattr(_local, "initialized", None)
    if initialized is None:
        initialized = set()
        _local.initialized = initialized

    key = _normalize_path(db_path)
    conn = conns.get(key)
    if conn is not None and not db_path.exists():
        try:
            conn.close()
        except sqlite3.Error:
            pass
        conns.pop(key, None)
        initialized.discard(key)
        conn = None

    if conn is None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conns[key] = conn

    if key not in initialized:
        conn.executescript(_SCHEMA)
        initialized.add(key)

    return conn


@contextmanager
def _connect(db_path: Path = HISTORY_DB) -> Iterator[sqlite3.Connection]:
    conn = _get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db(db_path: Path = HISTORY_DB) -> None:
    with _connect(db_path):
        pass


def record_compression(
    file_path: Path,
    status: str,
    mode: str,
    quality: str,
    original_size: int = 0,
    compressed_size: int = 0,
    output_path: Optional[Path] = None,
    error: Optional[str] = None,
    db_path: Path = HISTORY_DB,
    file_mtime_ns: Optional[int] = None,
) -> None:
    """Registra uma tentativa de compressão (sucesso, original mantido ou falha)."""
    resolved_file_path = _normalize_path(file_path)
    folder_path = os.path.dirname(resolved_file_path)
    file_name = os.path.basename(resolved_file_path)
    reduction = (
        (original_size - compressed_size) / original_size * 100
        if original_size and status != STATUS_FAILED
        else 0.0
    )
    # Referência do arquivo final no disco (usada para detectar se já foi processado)
    if status == STATUS_FAILED:
        mtime_ns = None
    elif file_mtime_ns is not None:
        mtime_ns = file_mtime_ns
    else:
        final_path = Path(output_path) if output_path else Path(resolved_file_path)
        try:
            mtime_ns = final_path.stat().st_mtime_ns
        except OSError:
            mtime_ns = None

    with _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO compressions
               (file_name, folder, file_path, output_path, mode, quality, status,
                original_size, compressed_size, reduction_percent, error,
                file_mtime_ns, compressed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                file_name,
                folder_path,
                resolved_file_path,
                str(output_path) if output_path else None,
                mode,
                quality,
                status,
                original_size,
                compressed_size,
                reduction,
                error,
                mtime_ns,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )


def is_already_compressed(
    file_path: Path,
    quality: str,
    db_path: Path = HISTORY_DB,
    stat_result: Optional[os.stat_result] = None,
) -> bool:
    """True se o arquivo (in-place) já foi processado com a mesma qualidade
    e não foi modificado desde então (mesmo mtime e tamanho)."""
    resolved_file_path = _normalize_path(file_path)
    try:
        stat = (
            stat_result if stat_result is not None else Path(resolved_file_path).stat()
        )
    except OSError:
        return False

    with _connect(db_path) as conn:
        row = conn.execute(
            """SELECT file_mtime_ns, compressed_size FROM compressions
               WHERE file_path = ? AND mode = 'in_place' AND quality = ?
                 AND status IN (?, ?)
               ORDER BY id DESC LIMIT 1""",
            (resolved_file_path, quality, STATUS_COMPRESSED, STATUS_KEPT_ORIGINAL),
        ).fetchone()

    return bool(
        row
        and row["file_mtime_ns"] == stat.st_mtime_ns
        and row["compressed_size"] == stat.st_size
    )


def get_history(
    folder: Optional[str] = None, limit: int = 100, db_path: Path = HISTORY_DB
) -> List[sqlite3.Row]:
    """Retorna os registros mais recentes, opcionalmente filtrados por pasta."""
    query = "SELECT * FROM compressions"
    params: list = []
    if folder:
        query += " WHERE folder = ?"
        params.append(_normalize_path(Path(folder)))
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with _connect(db_path) as conn:
        return conn.execute(query, params).fetchall()
