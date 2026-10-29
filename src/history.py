import sqlite3
from pathlib import Path
from datetime import datetime
from .config import HISTORY_DB
from contextlib import contextmanager
from typing import Iterator, List, Optional

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
"""


@contextmanager
def _connect(db_path: Path = HISTORY_DB) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


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
) -> None:
    """Registra uma tentativa de compressão (sucesso, original mantido ou falha)."""
    file_path = Path(file_path).resolve()
    reduction = (
        (original_size - compressed_size) / original_size * 100
        if original_size and status != STATUS_FAILED
        else 0.0
    )
    # Referência do arquivo final no disco (usada para detectar se já foi processado)
    final_path = Path(output_path) if output_path else file_path
    try:
        mtime_ns = final_path.stat().st_mtime_ns if status != STATUS_FAILED else None
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
                file_path.name,
                str(file_path.parent),
                str(file_path),
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
    file_path: Path, quality: str, db_path: Path = HISTORY_DB
) -> bool:
    """True se o arquivo (in-place) já foi processado com a mesma qualidade
    e não foi modificado desde então (mesmo mtime e tamanho)."""
    file_path = Path(file_path).resolve()
    try:
        stat = file_path.stat()
    except OSError:
        return False

    with _connect(db_path) as conn:
        row = conn.execute(
            """SELECT * FROM compressions
               WHERE file_path = ? AND mode = 'in_place' AND quality = ?
                 AND status IN (?, ?)
               ORDER BY id DESC LIMIT 1""",
            (str(file_path), quality, STATUS_COMPRESSED, STATUS_KEPT_ORIGINAL),
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
        params.append(str(Path(folder).resolve()))
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with _connect(db_path) as conn:
        return conn.execute(query, params).fetchall()
