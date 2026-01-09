"""Aplicação FastAPI principal"""
from fastapi import FastAPI

from .middleware import setup_cors
from .routes import compression_router, health_router, info_router
from ..core.logging_config import setup_logging

setup_logging()

app = FastAPI(
    title="PDF Compressor API",
    description="API REST para compressão de arquivos PDF de exames médicos",
    version="1.0.0",
)

setup_cors(app)

app.include_router(info_router)
app.include_router(health_router)
app.include_router(compression_router)

