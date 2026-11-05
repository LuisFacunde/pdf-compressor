import os
import logging
import threading
import subprocess
from tqdm import tqdm
from pathlib import Path
import concurrent.futures
from typing import Optional, Tuple
from .config import GHOSTSCRIPT_CMD, LOG_FILE
from .history import (
    STATUS_COMPRESSED,
    STATUS_FAILED,
    STATUS_KEPT_ORIGINAL,
    is_already_compressed,
    record_compression,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def _get_file_stat(file_path: Path) -> Optional[os.stat_result]:
    try:
        return file_path.stat()
    except OSError:
        return None


def get_file_size(file_path: Path) -> int:
    stat = _get_file_stat(file_path)
    return stat.st_size if stat is not None else 0


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

    input_stat = _get_file_stat(input_path)
    if input_stat is None:
        error_msg = f"Input file does not exist: {input_path}"
        logger.error(error_msg)
        return False, error_msg

    if not input_path.suffix.lower() == ".pdf":
        error_msg = f"Input file is not a PDF: {input_path}"
        logger.error(error_msg)
        return False, error_msg

    if not overwrite and output_path.exists():
        error_msg = f"Output file already exists and overwrite is False: {output_path}"
        logger.warning(error_msg)
        return False, error_msg

    if not check_ghostscript_available():
        error_msg = f"Ghostscript not found. Please install Ghostscript and ensure '{GHOSTSCRIPT_CMD}' is in PATH"
        logger.error(error_msg)
        return False, error_msg

    output_path.parent.mkdir(parents=True, exist_ok=True)

    original_size = input_stat.st_size

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

        compressed_size = get_file_size(output_path)
        if compressed_size == 0:
            error_msg = "Compression failed, output file is missing or empty."
            logger.error(error_msg)
            return False, error_msg

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


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError as e:
        logger.warning(f"Could not remove temporary file {path}: {e}")


def compress_single_file_wrapper(args):
    pdf_file, output_dir, quality, overwrite, in_place = args[:5]
    original_size = (
        args[5] if len(args) > 5 and args[5] is not None else get_file_size(pdf_file)
    )

    success = False
    error = None
    final_output_path = None
    status = STATUS_FAILED
    final_compressed_size = 0
    file_mtime_ns = None

    if in_place:
        temp_output_file = pdf_file.with_name(pdf_file.name + ".tmp")
        # Remove .tmp órfão de execuções interrompidas
        _safe_unlink(temp_output_file)
        success, error = compress_pdf(
            pdf_file, temp_output_file, quality, overwrite=True
        )

        if success:
            compressed_size = get_file_size(temp_output_file)
            if compressed_size > 1024 and compressed_size >= original_size:
                # Resultado não é menor: mantém o original intacto
                status = STATUS_KEPT_ORIGINAL
                logger.info(
                    f"⏭️ {pdf_file.name}: compressed file is not smaller, original kept."
                )
                final_output_path = pdf_file
                final_compressed_size = original_size
            elif compressed_size > 1024:
                try:
                    # Substituição atômica: o original nunca fica sem existir
                    os.replace(temp_output_file, pdf_file)
                    status = STATUS_COMPRESSED
                    final_output_path = pdf_file
                    final_compressed_size = compressed_size
                except Exception as e:
                    success = False
                    error = f"Failed to replace original file: {e}"
            else:
                success = False
                error = "Compressed file is too small, likely an error occurred."

        if status != STATUS_COMPRESSED:
            _safe_unlink(temp_output_file)

    else:
        output_file = output_dir / f"{pdf_file.stem}_compress.pdf"
        success, error = compress_pdf(pdf_file, output_file, quality, overwrite)
        if success:
            final_output_path = output_file
            status = STATUS_COMPRESSED

    if success and final_output_path is not None:
        final_stat = _get_file_stat(final_output_path)
        if final_stat is not None:
            final_compressed_size = final_stat.st_size
            file_mtime_ns = final_stat.st_mtime_ns

    return {
        "file_name": pdf_file.name,
        "file_path": str(pdf_file),
        "status": status if success else STATUS_FAILED,
        "mode": "in_place" if in_place else "output_dir",
        "output_path": (
            str(final_output_path) if final_output_path and not in_place else None
        ),
        "success": success,
        "error": error,
        "original_size": original_size,
        "compressed_size": final_compressed_size if success else 0,
        "file_mtime_ns": file_mtime_ns,
    }


def compress_pdf_batch(
    input_dir: Path,
    output_dir: Path,
    quality: str = "prepress",
    overwrite: bool = False,
    max_workers: int = None,
    show_progress: bool = True,
    in_place: bool = False,
    force: bool = False,
) -> Tuple[int, int]:
    if in_place:
        logger.info(
            f"Modo 'in-place' ativado. Procurando PDFs recursivamente em {input_dir}"
        )
        pdf_files = iter(input_dir.rglob("*.pdf"))
    else:
        pdf_files = iter(input_dir.glob("*.pdf"))

    if max_workers is None:
        cpu_count = os.cpu_count() or 4
        max_workers = min(12, cpu_count)
    if max_workers < 1:
        raise ValueError("max_workers must be greater than zero")

    logger.info(
        f"Scanning for PDFs and compressing with up to {max_workers} parallel workers"
    )

    successful = 0
    failed = 0
    total_original_size = 0
    total_compressed_size = 0
    failed_files = []
    discovered_count = 0
    skipped_count = 0
    submitted_count = 0

    progress_bar = None
    if show_progress:
        try:
            progress_bar = tqdm(
                desc="Comprimindo PDFs",
                unit="arquivo",
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
            future_to_file = {}
            source_exhausted = False

            while future_to_file or not source_exhausted:
                while len(future_to_file) < max_workers and not source_exhausted:
                    try:
                        pdf_file = next(pdf_files)
                    except StopIteration:
                        source_exhausted = True
                        break

                    discovered_count += 1
                    if in_place and not force:
                        try:
                            file_stat = _get_file_stat(pdf_file)
                            if is_already_compressed(
                                pdf_file, quality, stat_result=file_stat
                            ):
                                skipped_count += 1
                                logger.info(
                                    f"⏭️ {pdf_file.name}: já comprimido "
                                    "(histórico), pulando."
                                )
                                continue
                        except Exception as e:
                            logger.warning(
                                f"Falha ao consultar histórico de {pdf_file.name}: {e}"
                            )

                    args = (
                        pdf_file,
                        output_dir,
                        quality,
                        overwrite,
                        in_place,
                    )
                    future = executor.submit(compress_single_file_wrapper, args)
                    future_to_file[future] = pdf_file
                    submitted_count += 1

                if not future_to_file:
                    continue

                completed, _ = concurrent.futures.wait(
                    future_to_file,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                for future in completed:
                    pdf_file = future_to_file.pop(future)
                    try:
                        result = future.result()

                        try:
                            extra_history_kwargs = (
                                {"file_mtime_ns": result["file_mtime_ns"]}
                                if result.get("file_mtime_ns") is not None
                                else {}
                            )
                            record_compression(
                                Path(result["file_path"]),
                                status=result["status"],
                                mode=result["mode"],
                                quality=quality,
                                original_size=result["original_size"],
                                compressed_size=result["compressed_size"],
                                output_path=(
                                    Path(result["output_path"])
                                    if result["output_path"]
                                    else None
                                ),
                                error=result["error"],
                                **extra_history_kwargs,
                            )
                        except Exception as hist_exc:
                            logger.warning(f"Falha ao gravar histórico: {hist_exc}")

                        total_original_size += result["original_size"]

                        if result["success"]:
                            successful += 1
                            total_compressed_size += result["compressed_size"]
                        else:
                            failed += 1
                            failed_files.append(
                                {
                                    "file": result["file_name"],
                                    "error": result["error"],
                                }
                            )
                            logger.error(
                                f"Failed to compress {result['file_name']}: "
                                f"{result['error']}"
                            )

                    except Exception as exc:
                        failed += 1
                        error_msg = (
                            f"Unexpected error processing {pdf_file.name}: {exc}"
                        )
                        failed_files.append({"file": pdf_file.name, "error": error_msg})
                        logger.error(error_msg)

                    if show_progress and progress_bar is not None:
                        progress_bar.update(1)

    finally:
        if show_progress and progress_bar is not None:
            progress_bar.close()

    if discovered_count == 0:
        logger.warning(f"No PDF files found in {input_dir}")
        return 0, 0

    if submitted_count == 0 and skipped_count:
        logger.info("No pending PDFs to compress; all discovered files were skipped.")

    logger.info(
        f"Parallel compression completed: {submitted_count} files submitted, "
        f"{skipped_count} skipped from history"
    )

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
            f"⚡ Processed {submitted_count} files using {max_workers} parallel workers"
        )

    if failed_files:
        logger.warning(f"❌ {len(failed_files)} files failed to compress:")
        for failed_file in failed_files[:5]:
            logger.warning(f"   • {failed_file['file']}: {failed_file['error']}")
        if len(failed_files) > 5:
            logger.warning(f"   ... and {len(failed_files) - 5} more failures")

    return successful, failed
