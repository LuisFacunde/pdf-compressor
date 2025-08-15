import subprocess
import logging
import os
from pathlib import Path
from typing import Optional, Tuple
from .config import GHOSTSCRIPT_CMD

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_compression.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_file_size(file_path: Path) -> int:
    # Paga o tamanho do arquivo em Bytes
    return file_path.stat().st_size if file_path.exists() else 0

def format_file_size(size_bytes: int) -> str:
    # Converte bytes para um formato mais legível;
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f}{size_names[i]}"

def calculate_compression_ratio(original_size: int, compressed_size: int) -> float:
    # Calcular a porcentagem de compressão.
    if original_size == 0:
        return 0.0
    return ((original_size - compressed_size) / original_size) * 100

def check_ghostscript_available() -> bool:
    # Checa se o Ghostspirit está instalado no sistema.
    try:
        subprocess.run(
            [GHOSTSCRIPT_CMD, "--version"], 
            capture_output=True, 
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def compress_pdf(
    input_path: Path,
    output_path: Path,
    quality: str = "prepress",
    overwrite: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Compress a PDF file using Ghostscript.
    
    Args:
        input_path: Path to input PDF
        output_path: Path for compressed PDF
        quality: Compression quality level
        overwrite: Whether to overwrite existing output files
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    # Validation checks
    if not input_path.exists():
        error_msg = f"Input file does not exist: {input_path}"
        logger.error(error_msg)
        return False, error_msg
    
    if not input_path.suffix.lower() == '.pdf':
        error_msg = f"Input file is not a PDF: {input_path}"
        logger.error(error_msg)
        return False, error_msg
    
    if output_path.exists() and not overwrite:
        error_msg = f"Output file already exists: {output_path}"
        logger.warning(error_msg)
        return False, error_msg
    
    if not check_ghostscript_available():
        error_msg = f"Ghostscript not found. Please install Ghostscript and ensure '{GHOSTSCRIPT_CMD}' is in PATH"
        logger.error(error_msg)
        return False, error_msg
    
    # Criar diretório de saída
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Pega o tamanho original do arquivo
    original_size = get_file_size(input_path)
    
    # Perapra comando Ghostscript
    cmd = [
        GHOSTSCRIPT_CMD,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS=/{quality}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        "-dSAFER",  # Security enhancement
        f"-sOutputFile={output_path}",
        str(input_path),
    ]
    
    try:
        logger.info(f"Compressing {input_path.name} with quality '{quality}'...")
        
        # Roda a compressão
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True,
            timeout=300  # 5 minutos de timeout
        )
        
        # Verifica se o arquivo de saída foi criado
        if not output_path.exists():
            error_msg = "Compression completed but output file was not created"
            logger.error(error_msg)
            return False, error_msg
        
        # Calcula estatisticas de compressão
        compressed_size = get_file_size(output_path)
        compression_ratio = calculate_compression_ratio(original_size, compressed_size)
        
        # Log de sucesso com estatisticas
        logger.info(
            f"✅ {input_path.name} → {output_path.name} "
            f"({format_file_size(original_size)} → {format_file_size(compressed_size)}, "
            f"{compression_ratio:.1f}% reduction)"
        )
        
        return True, None
        
    except subprocess.TimeoutExpired:
        error_msg = f"❌ Compression timeout for {input_path.name}"
        logger.error(error_msg)
        return False, error_msg
        
    except subprocess.CalledProcessError as e:
        error_msg = f"❌ Ghostscript error for {input_path.name}: {e.stderr}"
        logger.error(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"❌ Unexpected error compressing {input_path.name}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

import concurrent.futures
import threading
from tqdm import tqdm

# Contador de Threads para processos em paralelo
class ThreadSafeCounter:
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self, value=1):
        with self._lock:
            self._value += value
    
    @property
    def value(self):
        with self._lock:
            return self._value

def compress_single_file_wrapper(args):
    """
    Wrapper function for parallel processing.
    
    Args:
        args: Tuple of (pdf_file, output_file, quality, overwrite)
    
    Returns:
        dict with compression results
    """
    pdf_file, output_file, quality, overwrite = args
    
    original_size = get_file_size(pdf_file)
    success, error = compress_pdf(pdf_file, output_file, quality, overwrite)
    
    result = {
        'file_name': pdf_file.name,
        'success': success,
        'error': error,
        'original_size': original_size,
        'compressed_size': get_file_size(output_file) if success else 0
    }
    
    return result

def compress_pdf_batch(
    input_dir: Path,
    output_dir: Path,
    quality: str = "prepress",
    overwrite: bool = False,
    max_workers: int = None,
    show_progress: bool = True
) -> Tuple[int, int]:
    """
    Compress all PDF files in a directory using parallel processing.
    
    Args:
        input_dir: Directory containing input PDF files
        output_dir: Directory for compressed PDF files
        quality: Compression quality level
        overwrite: Whether to overwrite existing output files
        max_workers: Maximum number of parallel workers (None = auto-detect)
        show_progress: Whether to show progress bar
    
    Returns:
        Tuple of (successful_compressions, failed_compressions)
    """
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return 0, 0
    
    # Auto-detect optimal number of workers based on CPU cores and file count
    if max_workers is None:
        import os
        cpu_count = os.cpu_count() or 2
        # Use at most 4 workers to avoid overwhelming the system
        max_workers = min(4, cpu_count, len(pdf_files))
    
    logger.info(f"Found {len(pdf_files)} PDF files to compress using {max_workers} parallel workers")
    
    # Prepare arguments for parallel processing
    compression_args = []
    for pdf_file in pdf_files:
        output_file = output_dir / f"{pdf_file.stem}_compress.pdf"
        compression_args.append((pdf_file, output_file, quality, overwrite))
    
    successful = 0
    failed = 0
    total_original_size = 0
    total_compressed_size = 0
    failed_files = []
    
    # Progress bar setup
    progress_bar = None
    if show_progress:
        try:
            progress_bar = tqdm(
                total=len(pdf_files),
                desc="Comprimindo PDFs",
                unit="arquivo",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
            )
        except ImportError:
            logger.warning("tqdm not installed. Install with 'pip install tqdm' for progress bars.")
            show_progress = False
    
    # Execute compression in parallel
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all compression tasks
            future_to_args = {
                executor.submit(compress_single_file_wrapper, args): args 
                for args in compression_args
            }
            
            # Process completed tasks
            for future in concurrent.futures.as_completed(future_to_args):
                args = future_to_args[future]
                pdf_file = args[0]
                
                try:
                    result = future.result()
                    
                    # Update counters
                    total_original_size += result['original_size']
                    
                    if result['success']:
                        successful += 1
                        total_compressed_size += result['compressed_size']
                    else:
                        failed += 1
                        failed_files.append({
                            'file': result['file_name'],
                            'error': result['error']
                        })
                        logger.error(f"Failed to compress {result['file_name']}: {result['error']}")
                    
                    # Update progress bar
                    if show_progress and progress_bar:
                        progress_bar.update(1)
                        
                except Exception as exc:
                    failed += 1
                    error_msg = f"Unexpected error processing {pdf_file.name}: {exc}"
                    failed_files.append({
                        'file': pdf_file.name,
                        'error': error_msg
                    })
                    logger.error(error_msg)
                    
                    if show_progress and progress_bar:
                        progress_bar.update(1)
    
    finally:
        if show_progress and progress_bar:
            progress_bar.close()
    
    # Log batch summary
    logger.info(f"Parallel compression completed in batch")
    
    if successful > 0:
        overall_compression = calculate_compression_ratio(
            total_original_size, total_compressed_size
        )
        logger.info(
            f"✅ Batch results: {successful} successful, {failed} failed"
        )
        logger.info(
            f"📊 Space savings: {format_file_size(total_original_size - total_compressed_size)} "
            f"({overall_compression:.1f}% reduction)"
        )
        logger.info(
            f"⚡ Processed {len(pdf_files)} files using {max_workers} parallel workers"
        )
    
    # Log failed files details if any
    if failed_files:
        logger.warning(f"❌ {len(failed_files)} files failed to compress:")
        for failed_file in failed_files[:5]:  # Show first 5 failures
            logger.warning(f"   • {failed_file['file']}: {failed_file['error']}")
        if len(failed_files) > 5:
            logger.warning(f"   ... and {len(failed_files) - 5} more failures")
    
    return successful, failed