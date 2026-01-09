"""Rotas da API organizadas por funcionalidade"""

from .compression import router as compression_router
from .health import router as health_router
from .info import router as info_router

__all__ = ["compression_router", "health_router", "info_router"]
