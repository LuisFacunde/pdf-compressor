import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from .settings import get_settings

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"


def setup_logging(verbose: bool = False, log_file: Optional[Path] = None) -> None:
    """Configura o logging da aplicação.

    Deve ser chamada explicitamente pelo ponto de entrada (CLI); importar os
    módulos da biblioteca não cria arquivos nem altera o logging global.
    O arquivo de log tem rotação (5 MB x 5 backups) para não crescer sem limite.
    """
    root = logging.getLogger()
    level = logging.DEBUG if verbose else logging.INFO
    if any(getattr(h, "_pdf_compressor", False) for h in root.handlers):
        root.setLevel(level)
        return

    log_file = Path(log_file) if log_file else get_settings().log_file
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    stream_handler = logging.StreamHandler()
    for handler in (file_handler, stream_handler):
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handler._pdf_compressor = True
        root.addHandler(handler)
    root.setLevel(level)
