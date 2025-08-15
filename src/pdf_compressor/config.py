# src/pdf_compressor/config.py
import os
import platform
from pathlib import Path

# PATHS do projeto
HERE = Path(__file__).resolve().parent.parent.parent
INPUT_DIR = HERE / "src" / "data" / "input" / "pdfs_originais"
OUTPUT_DIR = HERE / "src" / "data" / "output" / "pdfs_compactados"

# Configuração do GhostScript com base na plataforma
def get_ghostscript_command():
    """Get the appropriate Ghostscript command for the current platform."""
    system = platform.system().lower()
    
    if system == "windows":
        # Try common Windows installations
        candidates = [
            "gswin64c",  # linha de comando para 64-bit
            "gswin32c",  # linha de comando para 32-bit
            "gs",        # Generico
        ]
    elif system == "darwin":  # macOS
        candidates = ["gs"]
    else:  # Linux ou Sistemas baseados em Unix
        candidates = ["gs"]
    
    # Verifique se algum candidato está disponível no PATH
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
    
    # Se nenhum for encontrado, retorne o padrão mais provável
    return candidates[0]

GHOSTSCRIPT_CMD = get_ghostscript_command()

# Configuração de qualidade de compressão com descrição
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

# Tamanho máximo de arquivos (em bytes)
MAX_INPUT_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
MIN_OUTPUT_FILE_SIZE = 1024  # 1 KB

# Configuração de Logging
LOG_FILE = HERE / "logs" / "pdf_compression.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Cria o diretório de logs se não existir
LOG_FILE.parent.mkdir(exist_ok=True)