"""Serviço de compressão de PDFs"""
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from ..core.config import GHOSTSCRIPT_CMD
from ..core.logging_config import get_logger
from ..utils.file_utils import get_file_size, format_file_size, calculate_compression_ratio

logger = get_logger(__name__)


def check_ghostscript_available() -> bool:
    """Verifica se o Ghostscript está disponível"""
    try:
        subprocess.run([GHOSTSCRIPT_CMD, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


class CompressionService:
    """Serviço para compressão de arquivos PDF"""
    
    def __init__(self):
        """Inicializa o serviço de compressão"""
        self.ghostscript_cmd = GHOSTSCRIPT_CMD
    
    def compress_pdf(
        self,
        input_path: Path,
        output_path: Path,
        quality: str = "prepress",
        overwrite: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Comprime um arquivo PDF
        
        Args:
            input_path: Caminho do arquivo de entrada
            output_path: Caminho do arquivo de saída
            quality: Nível de qualidade (screen, ebook, printer, prepress, default)
            overwrite: Se True, sobrescreve arquivo de saída existente
        
        Returns:
            Tupla (sucesso, mensagem_de_erro)
        """
        # Validações
        if not input_path.exists():
            error_msg = f"Input file does not exist: {input_path}"
            logger.error(error_msg)
            return False, error_msg
        
        if not input_path.suffix.lower() == ".pdf":
            error_msg = f"Input file is not a PDF: {input_path}"
            logger.error(error_msg)
            return False, error_msg
        
        if output_path.exists() and not overwrite:
            error_msg = f"Output file already exists and overwrite is False: {output_path}"
            logger.warning(error_msg)
            return False, error_msg
        
        if not check_ghostscript_available():
            error_msg = f"Ghostscript not found. Please install Ghostscript and ensure '{self.ghostscript_cmd}' is in PATH"
            logger.error(error_msg)
            return False, error_msg
        
        # Criar diretório de saída se necessário
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        original_size = get_file_size(input_path)
        
        # Comando Ghostscript
        cmd = [
            self.ghostscript_cmd,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{quality}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dSAFER",
            f"-sOutputFile={output_path}",
            str(input_path),
        ]
        
        try:
            logger.info(f"Compressing {input_path.name} with quality '{quality}'...")
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=300
            )
            
            # Verificar se o arquivo foi criado e não está vazio
            if not output_path.exists() or get_file_size(output_path) == 0:
                error_msg = "Compression failed, output file is missing or empty."
                logger.error(error_msg)
                return False, error_msg
            
            compressed_size = get_file_size(output_path)
            compression_ratio = calculate_compression_ratio(original_size, compressed_size)
            
            logger.info(
                f"Success: {input_path.name} → {output_path.name} "
                f"({format_file_size(original_size)} → {format_file_size(compressed_size)}, "
                f"{compression_ratio:.1f}% reduction)"
            )
            
            return True, None
        
        except subprocess.TimeoutExpired:
            error_msg = f"Compression timeout for {input_path.name}"
            logger.error(error_msg)
            return False, error_msg
        
        except subprocess.CalledProcessError as e:
            error_msg = f"Ghostscript error for {input_path.name}: {e.stderr}"
            logger.error(error_msg)
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error compressing {input_path.name}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

