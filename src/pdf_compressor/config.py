from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

HERE = Path(__file__).resolve().parent.parent.parent
INPUT_DIR  = HERE / "src" / "data" / "input"  / "pdfs_originais"
OUTPUT_DIR = HERE / "src" / "data" / "output" / "pdfs_compactados"
GHOSTSCRIPT_CMD = "gswin64c"

class Settings(BaseSettings):
    # Configurações da API

    # Configurações do servidor
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 1
    DEBUG: bool = False
    
    # Configurações do compressor
    DEFAULT_QUALITY: str = "prepress"
    MIN_COMPRESSION_RATIO: float = 0.2  # 20% de redução mínima
    ALLOWED_FILE_TYPES: list = [".pdf"]
    
    # Configurações de segurança
    API_KEY: Optional[str] = None
    ENABLE_CORS: bool = True
    ALLOWED_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
