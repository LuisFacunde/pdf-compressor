from pathlib import Path
from typing import List, Optional
from src.models import CompressionResult
from src.ports import EngineError


class FakeEngine:
    """Motor falso: escreve ``size`` bytes no destino, ou falha conforme configurado."""

    def __init__(self, size: int = 2048, error: Optional[Exception] = None):
        self.size = size
        self.error = error
        self.calls: List[tuple] = []

    def compress(self, source: Path, destination: Path, quality: str) -> None:
        self.calls.append((source, destination, quality))
        if self.error is not None:
            # simula um motor que deixou saída parcial antes de falhar
            destination.write_bytes(b"partial")
            raise self.error
        destination.write_bytes(b"b" * self.size)


class FailingEngine(FakeEngine):
    def __init__(self, message: str = "boom"):
        super().__init__(error=EngineError(message))


class InMemoryHistory:
    def __init__(self):
        self.records: List[tuple] = []
        self.done: set = set()

    def record(self, result: CompressionResult, quality: str) -> None:
        self.records.append((result, quality))

    def is_already_compressed(self, file_path: Path, quality: str) -> bool:
        return (Path(file_path), quality) in self.done

    def query(self, folder=None, limit=100):
        return []


def write_pdf(path: Path, size: int = 4096) -> Path:
    path.write_bytes(b"a" * size)
    return path
