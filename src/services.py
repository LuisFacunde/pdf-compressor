"""Casos de uso: compressão de um arquivo e processamento em lote.

Dependem apenas das interfaces em ``ports`` (motor e histórico injetados).
"""

import concurrent.futures
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple
from .models import CompressionResult, Mode, Status
from .ports import CompressionEngine, EngineError, HistoryRepository
from .utils import calculate_compression_ratio, format_file_size, get_file_size

logger = logging.getLogger(__name__)


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError as e:
        logger.warning(f"Could not remove temporary file {path}: {e}")


def default_workers() -> int:
    return min(12, os.cpu_count() or 4)


class FileCompressor:
    """Comprime um único PDF."""

    def __init__(self, engine: CompressionEngine, min_output_size: int = 1024):
        self.engine = engine
        self.min_output_size = min_output_size

    def compress_to(
        self,
        source: Path,
        destination: Path,
        quality: str,
        overwrite: bool = False,
        mode: Mode = Mode.OUTPUT_DIR,
    ) -> CompressionResult:
        """Comprime ``source`` para ``destination`` sem alterar o original."""
        original_size = get_file_size(source)

        error = self._validate_source(source)
        if error is None and destination.exists() and not overwrite:
            error = f"Output file already exists and overwrite is False: {destination}"
            logger.warning(error)
        if error:
            return self._failed(source, mode, original_size, error)

        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(destination.name + ".tmp")
        _safe_unlink(temp)
        try:
            error = self._run_engine(source, temp, quality)
            if error is None:
                try:
                    os.replace(temp, destination)
                except OSError as e:
                    error = f"Failed to write output file: {e}"
        finally:
            _safe_unlink(temp)

        if error:
            return self._failed(source, mode, original_size, error)

        compressed_size = get_file_size(destination)
        logger.info(
            f"✅ {source.name} → {destination.name} "
            f"({format_file_size(original_size)} → {format_file_size(compressed_size)}, "
            f"{calculate_compression_ratio(original_size, compressed_size):.1f}% reduction)"
        )
        return CompressionResult(
            file_name=source.name,
            file_path=str(source),
            status=Status.COMPRESSED,
            mode=mode,
            success=True,
            original_size=original_size,
            compressed_size=compressed_size,
            output_path=str(destination),
        )

    def compress_in_place(self, source: Path, quality: str) -> CompressionResult:
        """Substitui o original pelo comprimido, somente se válido e menor."""
        original_size = get_file_size(source)
        error = self._validate_source(source)
        if error:
            return self._failed(source, Mode.IN_PLACE, original_size, error)

        temp = source.with_name(source.name + ".tmp")
        _safe_unlink(temp)  # remove .tmp órfão de execuções interrompidas
        status = Status.FAILED
        try:
            error = self._run_engine(source, temp, quality)
            if error is None:
                compressed_size = get_file_size(temp)
                if compressed_size <= self.min_output_size:
                    error = "Compressed file is too small, likely an error occurred."
                elif compressed_size >= original_size:
                    status = Status.KEPT_ORIGINAL
                    logger.info(
                        f"⏭️ {source.name}: compressed file is not smaller, original kept."
                    )
                else:
                    try:
                        # Substituição atômica: o original nunca fica sem existir
                        os.replace(temp, source)
                        status = Status.COMPRESSED
                    except OSError as e:
                        error = f"Failed to replace original file: {e}"
        finally:
            _safe_unlink(temp)

        if error:
            return self._failed(source, Mode.IN_PLACE, original_size, error)

        return CompressionResult(
            file_name=source.name,
            file_path=str(source),
            status=status,
            mode=Mode.IN_PLACE,
            success=True,
            original_size=original_size,
            compressed_size=get_file_size(source),
        )

    def _validate_source(self, source: Path) -> Optional[str]:
        if not source.exists():
            error = f"Input file does not exist: {source}"
        elif source.suffix.lower() != ".pdf":
            error = f"Input file is not a PDF: {source}"
        else:
            return None
        logger.error(error)
        return error

    def _run_engine(self, source: Path, temp: Path, quality: str) -> Optional[str]:
        logger.info(f"Compressing {source.name} with quality '{quality}'...")
        try:
            self.engine.compress(source, temp, quality)
        except EngineError as e:
            logger.error(str(e))
            return str(e)
        except Exception as e:
            error = f"Unexpected error compressing {source.name}: {e}"
            logger.error(error)
            return error

        if get_file_size(temp) == 0:
            error = "Compression failed, output file is missing or empty."
            logger.error(error)
            return error
        return None

    @staticmethod
    def _failed(
        source: Path, mode: Mode, original_size: int, error: str
    ) -> CompressionResult:
        return CompressionResult(
            file_name=source.name,
            file_path=str(source),
            status=Status.FAILED,
            mode=mode,
            success=False,
            original_size=original_size,
            error=error,
        )


def _process_file(
    file_compressor: FileCompressor,
    source: Path,
    output_dir: Path,
    quality: str,
    overwrite: bool,
    in_place: bool,
) -> CompressionResult:
    """Função de topo (picklable) executada nos workers do lote."""
    if in_place:
        return file_compressor.compress_in_place(source, quality)
    return file_compressor.compress_to(
        source,
        output_dir / f"{source.stem}_compress.pdf",
        quality,
        overwrite,
        Mode.OUTPUT_DIR,
    )


@dataclass
class BatchSummary:
    discovered: int = 0
    submitted: int = 0
    skipped: int = 0
    successful: int = 0
    failed: int = 0
    total_original_size: int = 0
    total_compressed_size: int = 0
    failures: List[Tuple[str, Optional[str]]] = field(default_factory=list)


class BatchCompressor:
    """Processa uma pasta de PDFs em paralelo, descobrindo arquivos de forma incremental."""

    def __init__(
        self,
        file_compressor: FileCompressor,
        history: Optional[HistoryRepository] = None,
        executor_factory: Callable[..., concurrent.futures.Executor] = (
            concurrent.futures.ProcessPoolExecutor
        ),
    ):
        self.file_compressor = file_compressor
        self.history = history
        self.executor_factory = executor_factory

    def run(
        self,
        input_dir: Path,
        output_dir: Path,
        quality: str,
        *,
        overwrite: bool = False,
        in_place: bool = False,
        force: bool = False,
        max_workers: Optional[int] = None,
        on_result: Optional[Callable[[CompressionResult], None]] = None,
    ) -> BatchSummary:
        workers = max_workers if max_workers is not None else default_workers()
        if workers < 1:
            raise ValueError("max_workers must be greater than zero")

        if in_place:
            logger.info(
                f"Modo 'in-place' ativado. Procurando PDFs recursivamente em {input_dir}"
            )
            pdf_files = iter(input_dir.rglob("*.pdf"))
        else:
            pdf_files = iter(input_dir.glob("*.pdf"))

        logger.info(
            f"Scanning for PDFs and compressing with up to {workers} parallel workers"
        )

        summary = BatchSummary()
        with self.executor_factory(max_workers=workers) as executor:
            pending = {}
            exhausted = False

            while pending or not exhausted:
                while len(pending) < workers and not exhausted:
                    try:
                        pdf_file = next(pdf_files)
                    except StopIteration:
                        exhausted = True
                        break

                    summary.discovered += 1
                    if in_place and not force and self._already_done(pdf_file, quality):
                        summary.skipped += 1
                        logger.info(
                            f"⏭️ {pdf_file.name}: já comprimido (histórico), pulando."
                        )
                        continue

                    future = executor.submit(
                        _process_file,
                        self.file_compressor,
                        pdf_file,
                        output_dir,
                        quality,
                        overwrite,
                        in_place,
                    )
                    pending[future] = pdf_file
                    summary.submitted += 1

                if not pending:
                    continue

                done, _ = concurrent.futures.wait(
                    pending, return_when=concurrent.futures.FIRST_COMPLETED
                )
                for future in done:
                    pdf_file = pending.pop(future)
                    result = self._collect(future, pdf_file, in_place)
                    self._handle_result(result, quality, summary, on_result)

        self._log_summary(summary, input_dir, workers)
        return summary

    def _already_done(self, pdf_file: Path, quality: str) -> bool:
        if self.history is None:
            return False
        try:
            return self.history.is_already_compressed(pdf_file, quality)
        except Exception as e:
            logger.warning(f"Falha ao consultar histórico de {pdf_file.name}: {e}")
            return False

    @staticmethod
    def _collect(future, pdf_file: Path, in_place: bool) -> CompressionResult:
        try:
            return future.result()
        except Exception as exc:
            error = f"Unexpected error processing {pdf_file.name}: {exc}"
            return CompressionResult(
                file_name=pdf_file.name,
                file_path=str(pdf_file),
                status=Status.FAILED,
                mode=Mode.IN_PLACE if in_place else Mode.OUTPUT_DIR,
                success=False,
                original_size=get_file_size(pdf_file),
                error=error,
            )

    def _handle_result(self, result, quality, summary, on_result) -> None:
        if self.history is not None:
            try:
                self.history.record(result, quality)
            except Exception as e:
                logger.warning(f"Falha ao gravar histórico: {e}")

        summary.total_original_size += result.original_size
        if result.success:
            summary.successful += 1
            summary.total_compressed_size += result.compressed_size
        else:
            summary.failed += 1
            summary.failures.append((result.file_name, result.error))
            logger.error(f"Failed to compress {result.file_name}: {result.error}")

        if on_result is not None:
            on_result(result)

    @staticmethod
    def _log_summary(summary: BatchSummary, input_dir: Path, workers: int) -> None:
        if summary.discovered == 0:
            logger.warning(f"No PDF files found in {input_dir}")
            return

        if summary.submitted == 0 and summary.skipped:
            logger.info(
                "No pending PDFs to compress; all discovered files were skipped."
            )

        logger.info(
            f"Parallel compression completed: {summary.submitted} files submitted, "
            f"{summary.skipped} skipped from history"
        )

        if summary.successful > 0:
            saved = summary.total_original_size - summary.total_compressed_size
            ratio = calculate_compression_ratio(
                summary.total_original_size, summary.total_compressed_size
            )
            logger.info(
                f"✅ Batch results: {summary.successful} successful, {summary.failed} failed"
            )
            logger.info(
                f"📊 Space savings: {format_file_size(saved)} ({ratio:.1f}% reduction)"
            )
            logger.info(
                f"⚡ Processed {summary.submitted} files using {workers} parallel workers"
            )

        if summary.failures:
            logger.warning(f"❌ {len(summary.failures)} files failed to compress:")
            for name, error in summary.failures[:5]:
                logger.warning(f"   • {name}: {error}")
            if len(summary.failures) > 5:
                logger.warning(f"   ... and {len(summary.failures) - 5} more failures")
