"""Utilitários para manipulação de arquivos"""
from pathlib import Path


def get_file_size(file_path: Path) -> int:
    """Retorna o tamanho do arquivo em bytes"""
    return file_path.stat().st_size if file_path.exists() else 0


def format_file_size(size_bytes: int) -> str:
    """Formata o tamanho do arquivo em formato legível"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.2f}{size_names[i]}"


def calculate_compression_ratio(original_size: int, compressed_size: int) -> float:
    """Calcula a porcentagem de redução do arquivo"""
    if original_size == 0:
        return 0.0
    return ((original_size - compressed_size) / original_size) * 100

