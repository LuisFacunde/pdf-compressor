import argparse
from pathlib import Path
from .config import INPUT_DIR, OUTPUT_DIR
from .compressor import compress_pdf, compress_batch

def main():
    parser = argparse.ArgumentParser(
        description="Compressão em lote de PDFs com Ghostscript"
    )
    parser.add_argument(
        "-i", "--input-dir",
        type=Path, default=INPUT_DIR,
        help="pasta dos PDFs originais"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path, default=OUTPUT_DIR,
        help="pasta de saída para PDFs comprimidos"
    )
    parser.add_argument(
        "-q", "--quality",
        choices=["screen","ebook","printer","prepress","default"],
        default="prepress",
        help="nível de compressão"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="número de workers para processamento paralelo"
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pdfs = list(args.input_dir.glob("*.pdf"))
    compress_batch(pdfs, args.output_dir, quality=args.quality, max_workers=args.workers)

if __name__ == "__main__":
    main()
