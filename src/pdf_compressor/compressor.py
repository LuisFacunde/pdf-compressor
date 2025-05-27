import subprocess
from pathlib import Path
from .config import GHOSTSCRIPT_CMD
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple
import os

def compress_pdf(
    input_path: Path,
    output_path: Path,
    quality: str = "prepress"
) -> Tuple[bool, str]:
    # Verifica se vale a pena comprimir
    input_size = input_path.stat().st_size
    if input_size < 1024 * 1024:  # Arquivos menores que 1MB
        return False, "Arquivo muito pequeno para compressão"

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
        # Verifica se houve redução real no tamanho
        output_size = output_path.stat().st_size
        if output_size >= input_size:
            output_path.unlink()  # Remove arquivo de saída
            return False, "Compressão não reduziu o tamanho"
        return True, f"Redução: {((input_size - output_size) / input_size) * 100:.1f}%"
    except subprocess.CalledProcessError as e:
        return False, str(e)

def compress_batch(input_files: List[Path], output_dir: Path, quality: str = "prepress", max_workers: int = 4) -> None:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for pdf in input_files:
            out = output_dir / f"{pdf.stem}_compress.pdf"
            futures.append(executor.submit(compress_pdf, pdf, out, quality))
        
        total = len(futures)
        for i, future in enumerate(futures, 1):
            success, msg = future.result()
            status = "✔" if success else "✘"
            print(f"[{i}/{total}] [{status}] {msg}")
