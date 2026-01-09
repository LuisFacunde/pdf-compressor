"""Validadores para entrada de dados"""
from fastapi import HTTPException
from .file_utils import format_file_size
from ..core.config import QUALITY_SETTINGS, MAX_INPUT_FILE_SIZE


def validate_quality(quality: str) -> None:
    """Valida se o nível de qualidade é válido"""
    if quality not in QUALITY_SETTINGS:
        raise HTTPException(
            status_code=400,
            detail=f"Qualidade inválida. Opções: {', '.join(QUALITY_SETTINGS.keys())}"
        )


def validate_pdf_file(filename: str) -> None:
    """Valida se o arquivo é um PDF"""
    if not filename or not filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Apenas arquivos PDF são aceitos"
        )


def validate_file_size(file_size: int) -> None:
    """Valida se o tamanho do arquivo está dentro do limite"""
    if file_size > MAX_INPUT_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Arquivo muito grande. Tamanho máximo: {format_file_size(MAX_INPUT_FILE_SIZE)}"
        )

