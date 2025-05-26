import subprocess
from pathlib import Path
from .config import GHOSTSCRIPT_CMD

def compress_pdf(
    input_path: Path,
    output_path: Path,
    quality: str = "prepress"
) -> None:
    """
    Comprime um PDF usando Ghostscript.
    quality: 'screen', 'ebook', 'printer', 'prepress' ou 'default'
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        GHOSTSCRIPT_CMD,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS=/{quality}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        str(input_path),
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"[✔] {input_path.name} → {output_path.name}")
    except subprocess.CalledProcessError as e:
        print(f"[✘] falha ao comprimir {input_path.name}:", e)
