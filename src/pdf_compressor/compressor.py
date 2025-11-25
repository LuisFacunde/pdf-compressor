import os
import subprocess
import logging
import threading
import concurrent.futures
from tqdm import tqdm
from pathlib import Path
from typing import Optional, Tuple
from .config import GHOSTSCRIPT_CMD

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("../logs/pdf_compression.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def get_file_size(file_path: Path) -> int:
    return file_path.stat().st_size if file_path.exists() else 0


def format_file_size(
    size_bytes: int,
) -> str:
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f}{size_names[i]}"


def calculate_compression_ratio(original_size: int, compressed_size: int) -> float:
    if original_size == 0:
        return 0.0
    return ((original_size - compressed_size) / original_size) * 100


def check_ghostscript_available() -> bool:
    try:
        subprocess.run([GHOSTSCRIPT_CMD, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def compress_pdf(
    input_path: Path,
    output_path: Path,
    quality: str = "prepress",
    overwrite: bool = False,
) -> Tuple[bool, Optional[str]]:

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
        error_msg = f"Ghostscript not found. Please install Ghostscript and ensure '{GHOSTSCRIPT_CMD}' is in PATH"
        logger.error(error_msg)
        return False, error_msg

    output_path.parent.mkdir(parents=True, exist_ok=True)

    original_size = get_file_size(input_path)

    cmd = [
        GHOSTSCRIPT_CMD,
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

        if not output_path.exists() or get_file_size(output_path) == 0:
            error_msg = "Compression failed, output file is missing or empty."
            logger.error(error_msg)
            return False, error_msg

        compressed_size = get_file_size(output_path)
        compression_ratio = calculate_compression_ratio(original_size, compressed_size)

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
    pdf_file, output_dir, quality, overwrite, in_place = args

    original_size = get_file_size(pdf_file)
    success = False
    error = None
    final_output_path = None

    if in_place:
        temp_output_file = pdf_file.with_suffix(".pdf.tmp")
        success, error = compress_pdf(
            pdf_file, temp_output_file, quality, overwrite=True
        )

        if success:
            if get_file_size(temp_output_file) > 1024:
                try:
                    pdf_file.unlink()
                    temp_output_file.rename(pdf_file)
                    final_output_path = pdf_file
                except Exception as e:
                    success = False
                    error = f"Failed to replace original file: {e}"
            else:
                success = False
                error = "Compressed file is too small, likely an error occurred."

        if not success and temp_output_file.exists():
            temp_output_file.unlink()

    else:
        output_file = output_dir / f"{pdf_file.stem}_compress.pdf"
        success, error = compress_pdf(pdf_file, output_file, quality, overwrite)
        if success:
            final_output_path = output_file

    return {
        "file_name": pdf_file.name,
        "success": success,
        "error": error,
        "original_size": original_size,
        "compressed_size": (
            get_file_size(final_output_path) if success and final_output_path else 0
        ),
    }


def compress_pdf_batch(
    input_dir: Path,
    output_dir: Path,
    quality: str = "prepress",
    overwrite: bool = False,
    max_workers: int = None,
    show_progress: bool = True,
    in_place: bool = False,
) -> Tuple[int, int]:

    if in_place:
        logger.info(
            f"Modo 'in-place' ativado. Procurando PDFs recursivamente em {input_dir}"
        )
        pdf_files = list(input_dir.rglob("*.pdf"))
    else:
        pdf_files = list(input_dir.glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return 0, 0

    if max_workers is None:
        import os

        cpu_count = os.cpu_count() or 4
        max_workers = min(12, cpu_count, len(pdf_files))

    logger.info(
        f"Found {len(pdf_files)} PDF files to compress using {max_workers} parallel workers"
    )

    compression_args = []
    for pdf_file in pdf_files:
        compression_args.append((pdf_file, output_dir, quality, overwrite, in_place))

    successful = 0
    failed = 0
    total_original_size = 0
    total_compressed_size = 0
    failed_files = []

    progress_bar = None
    if show_progress:
        try:
            progress_bar = tqdm(
                total=len(pdf_files),
                desc="Comprimindo PDFs",
                unit="arquivo",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            )
        except ImportError:
            logger.warning(
                "tqdm not installed. Install with 'pip install tqdm' for progress bars."
            )
            show_progress = False

    try:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        ) as executor:
            future_to_args = {
                executor.submit(compress_single_file_wrapper, args): args
                for args in compression_args
            }

            for future in concurrent.futures.as_completed(future_to_args):
                args = future_to_args[future]
                pdf_file = args[0]

                try:
                    result = future.result()

                    total_original_size += result["original_size"]

                    if result["success"]:
                        successful += 1
                        total_compressed_size += result["compressed_size"]
                    else:
                        failed += 1
                        failed_files.append(
                            {"file": result["file_name"], "error": result["error"]}
                        )
                        logger.error(
                            f"Failed to compress {result['file_name']}: {result['error']}"
                        )

                    if show_progress and progress_bar:
                        progress_bar.update(1)

                except Exception as exc:
                    failed += 1
                    error_msg = f"Unexpected error processing {pdf_file.name}: {exc}"
                    failed_files.append({"file": pdf_file.name, "error": error_msg})
                    logger.error(error_msg)

                    if show_progress and progress_bar:
                        progress_bar.update(1)

    finally:
        if show_progress and progress_bar:
            progress_bar.close()

    logger.info(f"Parallel compression completed in batch")

    if successful > 0:
        overall_compression = calculate_compression_ratio(
            total_original_size, total_compressed_size
        )
        logger.info(f"✅ Batch results: {successful} successful, {failed} failed")
        logger.info(
            f"📊 Space savings: {format_file_size(total_original_size - total_compressed_size)} "
            f"({overall_compression:.1f}% reduction)"
        )
        logger.info(
            f"⚡ Processed {len(pdf_files)} files using {max_workers} parallel workers"
        )

    if failed_files:
        logger.warning(f"❌ {len(failed_files)} files failed to compress:")
        for failed_file in failed_files[:5]:
            logger.warning(f"   • {failed_file['file']}: {failed_file['error']}")
        if len(failed_files) > 5:
            logger.warning(f"   ... and {len(failed_files) - 5} more failures")

    return successful, failed
