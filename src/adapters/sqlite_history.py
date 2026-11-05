from pathlib import Path
from typing import List, Optional
from ..history import get_history, is_already_compressed, record_compression
from ..models import CompressionResult
from ..settings import get_settings


class SqliteHistory:
    """Implementação de ``HistoryRepository`` sobre o módulo ``history`` (SQLite)."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else get_settings().history_db

    def record(self, result: CompressionResult, quality: str) -> None:
        record_compression(
            Path(result.file_path),
            status=result.status.value,
            mode=result.mode.value,
            quality=quality,
            original_size=result.original_size,
            compressed_size=result.compressed_size,
            output_path=Path(result.output_path) if result.output_path else None,
            error=result.error,
            db_path=self.db_path,
        )

    def is_already_compressed(self, file_path: Path, quality: str) -> bool:
        return is_already_compressed(file_path, quality, db_path=self.db_path)

    def query(self, folder: Optional[str] = None, limit: int = 100) -> List[dict]:
        return [dict(row) for row in get_history(folder, limit, db_path=self.db_path)]
