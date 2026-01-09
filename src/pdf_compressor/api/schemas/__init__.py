"""Schemas Pydantic para validação de dados da API"""

from .responses import (
    CompressionResponse,
    BatchFileResult,
    BatchCompressionResponse,
    HealthResponse,
    CleanupResponse,
)

__all__ = [
    "CompressionResponse",
    "BatchFileResult",
    "BatchCompressionResponse",
    "HealthResponse",
    "CleanupResponse",
]

