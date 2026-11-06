import concurrent.futures
import os
import signal
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .compressor import (
    _get_file_stat,
    compress_single_file_wrapper,
    logger,
)
from .history import is_already_compressed, record_compression


def _init_worker_process() -> None:
    """Faz processos filhos ignorarem SIGINT direto do console (evita tracebacks no Ctrl+C)."""
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except (ValueError, OSError):
        pass


def _normalize_path(path: Path) -> str:
    return os.path.abspath(os.fspath(path))


def _is_valid_pdf_candidate(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".pdf") and not name.endswith(".tmp")


def _can_open_for_reading(path: Path) -> bool:
    try:
        with open(path, "rb"):
            return True
    except OSError:
        return False


def _start_watchdog_observer(
    input_dir: Path,
    pending_paths: Set[Path],
    lock: threading.Lock,
    wake_event: threading.Event,
):
    """Inicia um Observer do watchdog se a biblioteca estiver instalada."""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        return None

    class _PdfEventHandler(FileSystemEventHandler):
        def _enqueue(self, raw_path: str) -> None:
            path = Path(raw_path)
            if _is_valid_pdf_candidate(path):
                with lock:
                    pending_paths.add(path)
                wake_event.set()

        def on_created(self, event):
            if not event.is_directory:
                self._enqueue(event.src_path)

        def on_modified(self, event):
            if not event.is_directory:
                self._enqueue(event.src_path)

        def on_moved(self, event):
            if not event.is_directory:
                self._enqueue(event.dest_path)

    try:
        observer = Observer()
        observer.schedule(_PdfEventHandler(), str(input_dir), recursive=True)
        observer.daemon = True
        observer.start()
        return observer
    except Exception as exc:
        logger.warning(f"Não foi possível iniciar o watchdog observer: {exc}")
        return None


def _create_executor(executor_factory, max_workers: int):
    if executor_factory is concurrent.futures.ProcessPoolExecutor:
        return executor_factory(
            max_workers=max_workers, initializer=_init_worker_process
        )
    return executor_factory(max_workers=max_workers)


class DirectoryWatcher:
    """Monitora uma pasta recursivamente e comprime novos PDFs na própria pasta do documento."""

    def __init__(
        self,
        input_dir: Path,
        quality: str = "prepress",
        max_workers: Optional[int] = None,
        settle_time: float = 3.0,
        poll_interval: float = 5.0,
        force: bool = False,
    ):
        if max_workers is None:
            cpu_count = os.cpu_count() or 4
            max_workers = min(12, cpu_count)
        if max_workers < 1:
            raise ValueError("max_workers must be greater than zero")

        self.input_dir = input_dir
        self.quality = quality
        self.max_workers = max_workers
        self.settle_time = max(0.0, float(settle_time))
        self.poll_interval = max(0.05, float(poll_interval))
        self.force = force

        # {normalized_path: (st_size, st_mtime_ns, first_seen_timestamp)}
        self._observed: Dict[str, Tuple[int, int, float]] = {}
        # Cache em memória de assinaturas (st_size, st_mtime_ns) já puladas ou recém-comprimidas
        self._skipped_signatures: Dict[str, Tuple[int, int]] = {}
        # Evita tentar recomprimir infinitamente na mesma sessão um arquivo corrompido que não mudou
        self._failed_signatures: Dict[str, Tuple[int, int]] = {}
        self._event_paths: Set[Path] = set()
        self._lock = threading.Lock()
        self._wake_event = threading.Event()

    def notify_file(self, path: Path) -> None:
        """Registra manualmente ou via evento de SO um arquivo candidato."""
        if _is_valid_pdf_candidate(path):
            with self._lock:
                self._event_paths.add(path)
            self._wake_event.set()

    def _collect_candidates(self, full_scan: bool) -> List[Path]:
        with self._lock:
            candidates = list(self._event_paths)
            self._event_paths.clear()

        seen = {_normalize_path(p) for p in candidates}
        for tracked_key in list(self._observed.keys()):
            if tracked_key not in seen:
                candidates.append(Path(tracked_key))
                seen.add(tracked_key)

        if full_scan:
            try:
                for pdf_file in self.input_dir.rglob("*.pdf"):
                    if not _is_valid_pdf_candidate(pdf_file):
                        continue
                    key = _normalize_path(pdf_file)
                    if key not in seen:
                        candidates.append(pdf_file)
                        seen.add(key)
            except OSError as exc:
                logger.warning(f"Erro ao varrer diretório {self.input_dir}: {exc}")

        return candidates

    def _filter_ready_files(
        self, candidates: List[Path], now: Optional[float] = None
    ) -> List[Tuple[Path, int]]:
        if now is None:
            now = time.monotonic()

        ready: List[Tuple[Path, int]] = []
        for pdf_file in candidates:
            key = _normalize_path(pdf_file)
            file_stat = _get_file_stat(pdf_file)
            if file_stat is None or file_stat.st_size == 0:
                self._observed.pop(key, None)
                continue

            signature = (file_stat.st_size, file_stat.st_mtime_ns)
            if self._failed_signatures.get(key) == signature:
                continue

            if not self.force:
                if self._skipped_signatures.get(key) == signature:
                    self._observed.pop(key, None)
                    continue
                try:
                    if is_already_compressed(
                        pdf_file, self.quality, stat_result=file_stat
                    ):
                        self._skipped_signatures[key] = signature
                        self._observed.pop(key, None)
                        logger.info(
                            f"⏭️ {pdf_file.name}: já comprimido (histórico), pulando."
                        )
                        continue
                except Exception as exc:
                    logger.warning(
                        f"Falha ao consultar histórico de {pdf_file.name}: {exc}"
                    )

            if self.settle_time > 0:
                previous = self._observed.get(key)
                if previous is None or (previous[0], previous[1]) != signature:
                    self._observed[key] = (
                        file_stat.st_size,
                        file_stat.st_mtime_ns,
                        now,
                    )
                    continue
                if (now - previous[2]) < self.settle_time:
                    continue

            if not _can_open_for_reading(pdf_file):
                continue

            self._observed.pop(key, None)
            ready.append((pdf_file, file_stat.st_size))

        return ready

    def _process_ready_files(
        self,
        ready_files: List[Tuple[Path, int]],
        executor: concurrent.futures.Executor,
    ) -> Tuple[int, int]:
        if not ready_files:
            return 0, 0

        successful = 0
        failed = 0
        future_to_file = {}

        for pdf_file, known_size in ready_files:
            logger.info(f"📥 Novo documento detectado para compressão: {pdf_file}")
            args = (
                pdf_file,
                pdf_file.parent,
                self.quality,
                True,
                True,
                known_size,
            )
            future = executor.submit(compress_single_file_wrapper, args)
            future_to_file[future] = pdf_file

        for future in concurrent.futures.as_completed(future_to_file):
            pdf_file = future_to_file[future]
            key = _normalize_path(pdf_file)
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
                        quality=self.quality,
                        original_size=result["original_size"],
                        compressed_size=result["compressed_size"],
                        output_path=None,
                        error=result["error"],
                        **extra_history_kwargs,
                    )
                except Exception as hist_exc:
                    logger.warning(f"Falha ao gravar histórico: {hist_exc}")

                if result["success"]:
                    successful += 1
                    self._failed_signatures.pop(key, None)
                    if result.get("file_mtime_ns") is not None:
                        self._skipped_signatures[key] = (
                            result["compressed_size"],
                            result["file_mtime_ns"],
                        )
                else:
                    failed += 1
                    stat_after = _get_file_stat(pdf_file)
                    if stat_after is not None:
                        self._failed_signatures[key] = (
                            stat_after.st_size,
                            stat_after.st_mtime_ns,
                        )
                    logger.error(
                        f"Failed to compress {result['file_name']}: {result['error']}"
                    )
            except Exception as exc:
                failed += 1
                logger.error(f"Unexpected error processing {pdf_file.name}: {exc}")

        return successful, failed

    def run_once(
        self,
        executor: Optional[concurrent.futures.Executor] = None,
        full_scan: bool = True,
        now: Optional[float] = None,
        executor_factory=concurrent.futures.ProcessPoolExecutor,
    ) -> Tuple[int, int]:
        candidates = self._collect_candidates(full_scan=full_scan)
        ready = self._filter_ready_files(candidates, now=now)
        if not ready:
            return 0, 0

        if executor is not None:
            return self._process_ready_files(ready, executor)

        workers = min(self.max_workers, len(ready))
        pool = _create_executor(executor_factory, workers)
        try:
            return self._process_ready_files(ready, pool)
        except KeyboardInterrupt:
            pool.shutdown(wait=False, cancel_futures=True)
            raise
        else:
            pool.shutdown(wait=True)

    def _wait_interruptible(
        self, timeout: float, stop_event: Optional[threading.Event]
    ) -> None:
        """Aguarda em fatias curtas para que Ctrl+C seja processado imediatamente no Windows."""
        deadline = time.monotonic() + timeout
        while True:
            if stop_event is not None and stop_event.is_set():
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            if self._wake_event.wait(timeout=min(0.2, remaining)):
                self._wake_event.clear()
                return

    def run(
        self,
        stop_event: Optional[threading.Event] = None,
        max_cycles: Optional[int] = None,
        executor_factory=concurrent.futures.ProcessPoolExecutor,
    ) -> Tuple[int, int]:
        logger.info(
            f"👀 Monitorando continuamente {self.input_dir} "
            f"(qualidade='{self.quality}', settle_time={self.settle_time}s, "
            f"poll_interval={self.poll_interval}s)"
        )
        observer = _start_watchdog_observer(
            self.input_dir, self._event_paths, self._lock, self._wake_event
        )
        total_successful = 0
        total_failed = 0
        cycles = 0
        last_full_scan = 0.0

        try:
            while True:
                if stop_event is not None and stop_event.is_set():
                    break

                now_mono = time.monotonic()
                do_full_scan = (
                    cycles == 0
                    or (now_mono - last_full_scan) >= self.poll_interval
                    or observer is None
                )
                if do_full_scan:
                    last_full_scan = now_mono

                ok, fail = self.run_once(
                    executor=None,
                    full_scan=do_full_scan,
                    now=now_mono,
                    executor_factory=executor_factory,
                )
                total_successful += ok
                total_failed += fail
                cycles += 1

                if max_cycles is not None and cycles >= max_cycles:
                    break

                wait_timeout = (
                    min(self.poll_interval, max(0.1, self.settle_time / 2.0))
                    if self._observed
                    else self.poll_interval
                )
                self._wait_interruptible(wait_timeout, stop_event)
        except KeyboardInterrupt:
            logger.info("🛑 Monitoramento interrompido pelo usuário.")
        finally:
            if observer is not None:
                observer.stop()
                observer.join(timeout=5)

        return total_successful, total_failed


def watch_directory(
    input_dir: Path,
    quality: str = "prepress",
    max_workers: Optional[int] = None,
    settle_time: float = 3.0,
    poll_interval: float = 5.0,
    force: bool = False,
    stop_event: Optional[threading.Event] = None,
    max_cycles: Optional[int] = None,
) -> Tuple[int, int]:
    watcher = DirectoryWatcher(
        input_dir=input_dir,
        quality=quality,
        max_workers=max_workers,
        settle_time=settle_time,
        poll_interval=poll_interval,
        force=force,
    )
    return watcher.run(stop_event=stop_event, max_cycles=max_cycles)
