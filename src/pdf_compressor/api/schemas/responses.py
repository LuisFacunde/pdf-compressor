"""Modelos de resposta da API"""
from typing import List, Optional
from pydantic import BaseModel


class CompressionResponse(BaseModel):
    """Resposta de compressão de arquivo único"""
    success: bool
    message: str
    original_size: Optional[int] = None
    compressed_size: Optional[int] = None
    compression_ratio: Optional[float] = None
    original_size_formatted: Optional[str] = None
    compressed_size_formatted: Optional[str] = None
    file_id: Optional[str] = None


class BatchFileResult(BaseModel):
    """Resultado de um arquivo em processamento em lote"""
    file_name: str
    success: bool
    error: Optional[str] = None
    file_id: Optional[str] = None
    original_size: Optional[int] = None
    compressed_size: Optional[int] = None
    compression_ratio: Optional[float] = None
    original_size_formatted: Optional[str] = None
    compressed_size_formatted: Optional[str] = None


class BatchCompressionResponse(BaseModel):
    """Resposta de compressão em lote"""
    success: bool
    message: str
    total_files: int
    successful: int
    failed: int
    total_original_size: int
    total_compressed_size: int
    overall_compression_ratio: float
    files: List[BatchFileResult]


class HealthResponse(BaseModel):
    """Resposta de health check"""
    status: str
    ghostscript_available: bool
    ghostscript_command: str


class CleanupResponse(BaseModel):
    """Resposta de limpeza de arquivos"""
    success: bool
    message: str

