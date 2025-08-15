# src/pdf_compressor/config.py
import os
import platform
from pathlib import Path

# Project paths
HERE = Path(__file__).resolve().parent.parent.parent
INPUT_DIR = HERE / "src" / "data" / "input" / "pdfs_originais"
OUTPUT_DIR = HERE / "src" / "data" / "output" / "pdfs_compactados"

# Ghostscript configuration based on platform
def get_ghostscript_command():
    """Get the appropriate Ghostscript command for the current platform."""
    system = platform.system().lower()
    
    if system == "windows":
        # Try common Windows installations
        candidates = [
            "gswin64c",  # 64-bit command line
            "gswin32c",  # 32-bit command line
            "gs",        # Generic
        ]
    elif system == "darwin":  # macOS
        candidates = ["gs"]
    else:  # Linux and other Unix-like systems
        candidates = ["gs"]
    
    # Check if any candidate is available in PATH
    for cmd in candidates:
        try:
            import subprocess
            subprocess.run(
                [cmd, "--version"], 
                capture_output=True, 
                check=True
            )
            return cmd
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    # If none found, return the most likely default
    return candidates[0]

GHOSTSCRIPT_CMD = get_ghostscript_command()

# Compression quality settings with descriptions
QUALITY_SETTINGS = {
    "screen": {
        "description": "Máxima compressão, menor qualidade (72 DPI)",
        "dpi": 72,
        "use_case": "Visualização em tela, rascunhos"
    },
    "ebook": {
        "description": "Alta compressão, qualidade média (150 DPI)",
        "dpi": 150,
        "use_case": "Arquivos médicos para armazenamento"
    },
    "printer": {
        "description": "Compressão média, qualidade alta (300 DPI)",
        "dpi": 300,
        "use_case": "Impressão de qualidade"
    },
    "prepress": {
        "description": "Baixa compressão, qualidade máxima (300+ DPI)",
        "dpi": 300,
        "use_case": "Arquivamento profissional"
    },
    "default": {
        "description": "Configuração padrão do Ghostscript",
        "dpi": "Variable",
        "use_case": "Balanceamento automático"
    }
}

# File size limits (in bytes)
MAX_INPUT_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
MIN_OUTPUT_FILE_SIZE = 1024  # 1 KB

# Logging configuration
LOG_FILE = HERE / "logs" / "pdf_compression.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Create logs directory if it doesn't exist
LOG_FILE.parent.mkdir(exist_ok=True)