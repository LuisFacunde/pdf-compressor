"""Configuração de middleware da API"""
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI


def setup_cors(app: FastAPI, allow_origins: list = None) -> None:
    """
    Configura CORS para a aplicação
    
    Args:
        app: Instância do FastAPI
        allow_origins: Lista de origens permitidas. Se None, permite todas (apenas desenvolvimento)
    """
    if allow_origins is None:
        allow_origins = ["*"]  # Em produção, especifique os domínios permitidos
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

