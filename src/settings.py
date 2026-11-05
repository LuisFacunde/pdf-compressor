"""Configuração da aplicação, sem efeitos colaterais no import."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = ROOT_DIR / "src" / "data" / "input" / "pdfs_originais"
DEFAULT_OUTPUT_DIR = Path(r"\\192.168.4.52\c$\exames")
DEFAULT_HISTORY_DB = ROOT_DIR / "historico" / "historico.db"
DEFAULT_LOG_FILE = ROOT_DIR / "logs" / "pdf_compression.log"
ENV_PREFIX = "PDF_COMPRESSOR_"

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


@dataclass(frozen=True)
class Settings:
    input_dir: Path = DEFAULT_INPUT_DIR
    output_dir: Path = DEFAULT_OUTPUT_DIR
    history_db: Path = DEFAULT_HISTORY_DB
    log_file: Path = DEFAULT_LOG_FILE
    ghostscript_cmd: Optional[str] = None  # None = detectar automaticamente
    timeout: int = 300
    min_output_size: int = 1024

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Settings":
        """Cria as configurações a partir de variáveis de ambiente.

        Variáveis: PDF_COMPRESSOR_INPUT_DIR, _OUTPUT_DIR, _HISTORY_DB, _LOG_FILE,
        _GS_CMD, _TIMEOUT, _MIN_OUTPUT_SIZE.
        """
        env = os.environ if env is None else env

        def get(name: str) -> Optional[str]:
            value = env.get(ENV_PREFIX + name)
            return value if value else None

        defaults = cls()
        return cls(
            input_dir=Path(get("INPUT_DIR") or defaults.input_dir),
            output_dir=Path(get("OUTPUT_DIR") or defaults.output_dir),
            history_db=Path(get("HISTORY_DB") or defaults.history_db),
            log_file=Path(get("LOG_FILE") or defaults.log_file),
            ghostscript_cmd=get("GS_CMD"),
            timeout=int(get("TIMEOUT") or defaults.timeout),
            min_output_size=int(get("MIN_OUTPUT_SIZE") or defaults.min_output_size),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
