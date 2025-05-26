import argparse
from pathlib import Path
from .config import INPUT_DIR, OUTPUT_DIR
from .compressor import compress_pdf

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
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for pdf in args.input_dir.glob("*.pdf"):
        out = args.output_dir / f"{pdf.stem}_{args.quality}.pdf"
        compress_pdf(pdf, out, quality=args.quality)

if __name__ == "__main__":
    main()
