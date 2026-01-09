"""Rotas de health check"""
from fastapi import APIRouter
from ..schemas.responses import HealthResponse
from ...services.compression_service import check_ghostscript_available
from ...core.config import GHOSTSCRIPT_CMD

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica o status do serviço e disponibilidade do Ghostscript"""
    gs_available = check_ghostscript_available()
    
    return HealthResponse(
        status="healthy" if gs_available else "unhealthy",
        ghostscript_available=gs_available,
        ghostscript_command=GHOSTSCRIPT_CMD
    )

