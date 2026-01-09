"""Módulo core com configurações e logging centralizados"""

from .config import (
    GHOSTSCRIPT_CMD,
    QUALITY_SETTINGS,
    MAX_INPUT_FILE_SIZE,
    MIN_OUTPUT_FILE_SIZE,
    INPUT_DIR,
    OUTPUT_DIR,
    LOG_FILE,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
)
from .logging_config import setup_logging, get_logger

__all__ = [
    "GHOSTSCRIPT_CMD",
    "QUALITY_SETTINGS",
    "MAX_INPUT_FILE_SIZE",
    "MIN_OUTPUT_FILE_SIZE",
    "INPUT_DIR",
    "OUTPUT_DIR",
    "LOG_FILE",
    "LOG_FORMAT",
    "LOG_DATE_FORMAT",
    "setup_logging",
    "get_logger",
]

