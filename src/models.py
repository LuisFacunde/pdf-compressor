from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class Quality(str, Enum):
    SCREEN = "screen"
    EBOOK = "ebook"
    PRINTER = "printer"
    PREPRESS = "prepress"
    DEFAULT = "default"


class Status(str, Enum):
    COMPRESSED = "compressed"
    KEPT_ORIGINAL = "kept_original"
    FAILED = "failed"


class Mode(str, Enum):
    IN_PLACE = "in_place"
    OUTPUT_DIR = "output_dir"
    SINGLE = "single"


@dataclass(frozen=True)
class CompressionResult:
    """Resultado tipado do processamento de um arquivo."""

    file_name: str
    file_path: str
    status: Status
    mode: Mode
    success: bool
    original_size: int
    compressed_size: int = 0
    output_path: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        # Valores simples (str) para serem serializáveis entre processos
        return {
            "file_name": self.file_name,
            "file_path": self.file_path,
            "status": self.status.value,
            "mode": self.mode.value,
            "output_path": self.output_path,
            "success": self.success,
            "error": self.error,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
        }
