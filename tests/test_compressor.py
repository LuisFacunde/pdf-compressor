from pathlib import Path
import pytest

from pdf_compressor.compressor import compress_pdf
from pdf_compressor.config import INPUT_DIR

@pytest.mark.parametrize("q", ["screen","ebook","printer","prepress","default"])
def test_compress(tmp_path, q):
    src = INPUT_DIR / "retinografia.pdf"
    out = tmp_path / f"out_{q}.pdf"
    compress_pdf(src, out, quality=q)
    assert out.exists() and out.stat().st_size > 0
