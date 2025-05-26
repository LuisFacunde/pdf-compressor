from pathlib import Path

HERE = Path(__file__).resolve().parent.parent.parent
INPUT_DIR  = HERE / "src" / "data" / "input"  / "pdfs_originais"
OUTPUT_DIR = HERE / "src" / "data" / "output" / "pdfs_compactados"
GHOSTSCRIPT_CMD = "gswin64c"
