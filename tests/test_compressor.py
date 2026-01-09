from pathlib import Path
import pytest

from pdf_compressor.services.compression_service import CompressionService
from pdf_compressor.core.config import INPUT_DIR

@pytest.mark.parametrize("q", ["screen","ebook","printer","prepress","default"])
def test_compress(tmp_path, q):
    """Testa a compressão usando o serviço diretamente"""
    service = CompressionService()
    src = INPUT_DIR / "retinografia.pdf"
    out = tmp_path / f"out_{q}.pdf"
    
    if not src.exists():
        pytest.skip(f"Arquivo de teste não encontrado: {src}")
    
    success, error = service.compress_pdf(src, out, quality=q)
    assert success, f"Compressão falhou: {error}"
    assert out.exists() and out.stat().st_size > 0
