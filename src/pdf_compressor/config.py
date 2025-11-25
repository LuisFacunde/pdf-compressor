import os
import platform
import sys
from pathlib import Path


def _get_base_dir() -> Path:
    """
    Resolve o diretório-base em tempo de execução.
    Se estiver empacotado (PyInstaller), utiliza a pasta do executável.
    Caso contrário, considera a raiz do repositório.
    """
    if getattr(sys, "frozen", False):  # Executável PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


BASE_DIR = _get_base_dir()


def _resolve_data_dir() -> Path:
    """
    Procura primeiro por src/data (layout de desenvolvimento) e,
    caso não exista, usa um diretório data/ ao lado do executável.
    """
    dev_data = BASE_DIR / "src" / "data"
    if dev_data.exists():
        return dev_data
    return BASE_DIR / "data"


DATA_DIR = _resolve_data_dir()
INPUT_DIR = DATA_DIR / "input" / "pdfs_originais"
OUTPUT_DIR = DATA_DIR / "output" / "pdfs_compactados"

LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "pdf_compression.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)


def get_ghostscript_command():
    system = platform.system().lower()

    if system == "windows":
        candidates = [
            "gswin64c",
            "gswin32c",
            "gs",
        ]
    elif system == "darwin":
        candidates = ["gs"]
    else:
        candidates = ["gs"]

    for cmd in candidates:
        try:
            import subprocess

            subprocess.run([cmd, "--version"], capture_output=True, check=True)
            return cmd
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    return candidates[0]


GHOSTSCRIPT_CMD = get_ghostscript_command()

QUALITY_SETTINGS = {
    "screen": {
        "description": "Máxima compressão, menor qualidade (72 DPI)",
        "dpi": 72,
        "use_case": "Visualização em tela, rascunhos",
    },
    "ebook": {
        "description": "Alta compressão, qualidade média (150 DPI)",
        "dpi": 150,
        "use_case": "Arquivos médicos para armazenamento",
    },
    "printer": {
        "description": "Compressão média, qualidade alta (300 DPI)",
        "dpi": 300,
        "use_case": "Impressão de qualidade",
    },
    "prepress": {
        "description": "Baixa compressão, qualidade máxima (300+ DPI)",
        "dpi": 300,
        "use_case": "Arquivamento profissional",
    },
    "default": {
        "description": "Configuração padrão do Ghostscript",
        "dpi": "Variable",
        "use_case": "Balanceamento automático",
    },
}

MAX_INPUT_FILE_SIZE = 500 * 1024 * 1024
MIN_OUTPUT_FILE_SIZE = 1024

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
