"""Rotas de informações da API"""
from fastapi import APIRouter
from ...core.config import QUALITY_SETTINGS

router = APIRouter(tags=["Info"])


@router.get("/")
async def root():
    """Endpoint raiz com informações da API"""
    return {
        "name": "PDF Compressor API",
        "version": "1.0.0",
        "description": "API REST para compressão de arquivos PDF",
        "endpoints": {
            "health": "/health",
            "compress_single": "/api/v1/compress",
            "compress_batch": "/api/v1/compress/batch",
            "download": "/api/v1/download/{file_id}",
            "quality_settings": "/api/v1/quality-settings"
        }
    }


@router.get("/api/v1/quality-settings")
async def get_quality_settings():
    """Retorna as configurações de qualidade disponíveis"""
    return {
        "qualities": QUALITY_SETTINGS,
        "default": "prepress",
        "recommended_for_medical": "prepress"
    }

