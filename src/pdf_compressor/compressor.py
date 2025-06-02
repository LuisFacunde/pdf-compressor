import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple
from .config import GHOSTSCRIPT_CMD
from concurrent.futures import ThreadPoolExecutor

def compress_pdf(
    input_path: Path,
    output_path: Path,
    quality: str = "prepress"
) -> Tuple[bool, str]:
    
    input_size = input_path.stat().st_size
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
        output_size = output_path.stat().st_size
        reduction_percentage = ((input_size - output_size) / input_size) * 100
        
        if output_size >= input_size or reduction_percentage < 20:
            output_path.unlink()
            new_output_path = output_path.parent / f"{input_path.stem}_original.pdf"
            shutil.copy2(input_path, new_output_path)
            msg = "Compressão não reduziu o tamanho" if output_size >= input_size else "Redução menor que 20%"
            return False, f"{msg} - arquivo original copiado"
        return True, f"Redução: {reduction_percentage:.1f}%"
    except subprocess.CalledProcessError as e:
        try:
            new_output_path = output_path.parent / f"{input_path.stem}_original.pdf"
            shutil.copy2(input_path, new_output_path)
            return False, f"Erro na compressão: {e} - arquivo original copiado"
        except Exception as copy_error:
            return False, f"Erro na compressão e na cópia: {e}, {copy_error}"

def compress_batch(
        input_files: List[Path], 
        output_dir: Path, 
        quality: str = "prepress", 
        max_workers: int = 5
    ) -> None:

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
