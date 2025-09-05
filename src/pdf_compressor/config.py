import os
import platform
from pathlib import Path

# PATHS do projeto
HERE = Path(__file__).resolve().parent.parent.parent
INPUT_DIR = HERE / "src" / "data" / "input" / "pdfs_originais"
OUTPUT_DIR = HERE / "src" / "data" / "output" / "pdfs_compactados"

def get_ghostscript_command():
    system = platform.system().lower()
    
    if system == "windows":
        candidates = [
            "gswin64c",
            "gswin32c",
            "gs",
        ]
    elif system == "darwin":  # macOS
        candidates = ["gs"]
    else:  # Linux
        candidates = ["gs"]
    
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
    
    return candidates[0]  # Se nenhum for encontrado, retorne o padrão mais provável

GHOSTSCRIPT_CMD = get_ghostscript_command()

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

MAX_INPUT_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
MIN_OUTPUT_FILE_SIZE = 1024  # 1 KB

# Configurações de Log
LOG_FILE = HERE / "logs" / "pdf_compression.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE.parent.mkdir(exist_ok=True) # Cria o diretório de logs se não existir