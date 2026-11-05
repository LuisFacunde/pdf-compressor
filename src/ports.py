"""Interfaces (ports) que o núcleo da aplicação espera das implementações externas."""

from pathlib import Path
from typing import List, Optional, Protocol
from .models import CompressionResult


class EngineError(Exception):
    """Falha do motor de compressão (indisponível, timeout, erro do processo...)."""


class CompressionEngine(Protocol):
    def compress(self, source: Path, destination: Path, quality: str) -> None:
        """Gera ``destination`` a partir de ``source``. Levanta EngineError em falha."""
        ...


class HistoryRepository(Protocol):
    def record(self, result: CompressionResult, quality: str) -> None: ...

    def is_already_compressed(self, file_path: Path, quality: str) -> bool: ...

    def query(self, folder: Optional[str] = None, limit: int = 100) -> List[dict]: ...
