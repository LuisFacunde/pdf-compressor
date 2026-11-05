import platform
import subprocess
from pathlib import Path
from typing import Optional
from ..ports import EngineError


def detect_ghostscript_command() -> str:
    """Retorna o primeiro executável do Ghostscript que responde a ``--version``."""
    if platform.system().lower() == "windows":
        candidates = ["gswin64c", "gswin32c", "gs"]
    else:
        candidates = ["gs"]

    for cmd in candidates:
        try:
            subprocess.run([cmd, "--version"], capture_output=True, check=True)
            return cmd
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return candidates[0]


class GhostscriptEngine:
    """Implementação de ``CompressionEngine`` usando o Ghostscript (pdfwrite)."""

    def __init__(self, command: Optional[str] = None, timeout: int = 300):
        self._command = command
        self.timeout = timeout
        self._available: Optional[bool] = None

    @property
    def command(self) -> str:
        if self._command is None:
            self._command = detect_ghostscript_command()
        return self._command

    def is_available(self) -> bool:
        if self._available is None:
            try:
                subprocess.run(
                    [self.command, "--version"], capture_output=True, check=True
                )
                self._available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                self._available = False
        return self._available

    def compress(self, source: Path, destination: Path, quality: str) -> None:
        if not self.is_available():
            raise EngineError(
                "Ghostscript not found. Please install Ghostscript and "
                f"ensure '{self.command}' is in PATH"
            )

        cmd = [
            self.command,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{quality}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dSAFER",
            f"-sOutputFile={destination}",
            str(source),
        ]

        try:
            subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=self.timeout
            )
        except subprocess.TimeoutExpired:
            raise EngineError(f"Compression timeout for {source.name}") from None
        except subprocess.CalledProcessError as e:
            raise EngineError(f"Ghostscript error for {source.name}: {e.stderr}") from e
