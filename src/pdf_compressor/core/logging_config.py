"""Configuração centralizada de logging"""
import logging
from pathlib import Path
from .config import LOG_FILE, LOG_FORMAT, LOG_DATE_FORMAT


def setup_logging(level: int = logging.INFO) -> None:
    """Configura o sistema de logging"""
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(),
        ],
    )


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger configurado"""
    return logging.getLogger(name)

