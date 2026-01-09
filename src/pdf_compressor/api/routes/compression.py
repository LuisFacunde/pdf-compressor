"""Rotas de compressão de PDFs"""
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse

from ..schemas.responses import CompressionResponse, BatchCompressionResponse, CleanupResponse
from ...services.file_service import FileService
from ...services.compression_service import CompressionService
from ...repositories.file_repository import FileRepository
from ...utils.validators import validate_quality, validate_pdf_file
from ...core.config import QUALITY_SETTINGS

router = APIRouter(tags=["Compression"])

# Inicializar serviços (em produção, usar injeção de dependência)
_file_repository = FileRepository()
_compression_service = CompressionService()
_file_service = FileService(_file_repository, _compression_service)


@router.post("/api/v1/compress", response_model=CompressionResponse)
async def compress_single_file(
    file: UploadFile = File(..., description="Arquivo PDF para comprimir"),
    quality: str = Form("prepress", description="Nível de qualidade: screen, ebook, printer, prepress, default")
):
    """
    Comprime um único arquivo PDF
    
    - **file**: Arquivo PDF a ser comprimido
    - **quality**: Nível de compressão (screen, ebook, printer, prepress, default)
    
    Retorna informações sobre a compressão realizada
    """
    # Validar qualidade
    validate_quality(quality)
    
    # Validar tipo de arquivo
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo não fornecido")
    
    validate_pdf_file(file.filename)
    
    try:
        result = await _file_service.compress_single_file(file, quality)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Falha na compressão"))
        
        return CompressionResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.post("/api/v1/compress/batch", response_model=BatchCompressionResponse)
async def compress_batch_files(
    files: List[UploadFile] = File(..., description="Lista de arquivos PDF para comprimir"),
    quality: str = Form("prepress", description="Nível de qualidade: screen, ebook, printer, prepress, default")
):
    """
    Comprime múltiplos arquivos PDF em lote
    
    - **files**: Lista de arquivos PDF a serem comprimidos
    - **quality**: Nível de compressão (screen, ebook, printer, prepress, default)
    """
    # Validar qualidade
    validate_quality(quality)
    
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo fornecido")
    
    if len(files) > 100:  # Limite de segurança
        raise HTTPException(status_code=400, detail="Máximo de 100 arquivos por lote")
    
    try:
        result = await _file_service.compress_batch_files(files, quality)
        return BatchCompressionResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/api/v1/download/{file_id}")
async def download_compressed_file(file_id: str):
    """
    Baixa um arquivo comprimido pelo ID
    
    - **file_id**: ID do arquivo retornado pela API de compressão
    """
    output_path = _file_repository.get_output_path(file_id)
    
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado ou expirado")
    
    return FileResponse(
        path=output_path,
        filename=f"compressed_{file_id}.pdf",
        media_type="application/pdf"
    )


@router.delete("/api/v1/cleanup/{file_id}", response_model=CleanupResponse)
async def cleanup_file(file_id: str):
    """
    Remove arquivos temporários de um processamento
    
    - **file_id**: ID do arquivo a ser removido
    """
    # Verificar se existem arquivos antes de deletar
    input_exists = _file_repository.file_exists(file_id, is_output=False)
    output_exists = _file_repository.file_exists(file_id, is_output=True)
    
    if not input_exists and not output_exists:
        return CleanupResponse(
            success=False,
            message="Nenhum arquivo encontrado para remoção"
        )
    
    # Deletar arquivos
    _file_repository.delete_all_files(file_id)
    
    return CleanupResponse(
        success=True,
        message="Arquivos removidos com sucesso"
    )

