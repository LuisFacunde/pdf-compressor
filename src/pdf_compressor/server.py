"""
Script para iniciar o servidor da API de compressão de PDFs
"""
import uvicorn
from .api import app

if __name__ == "__main__":
    # Configurações do servidor
    host = "0.0.0.0"  # Aceita conexões de qualquer IP
    port = 8000       # Porta padrão
    
    print(f"Iniciando servidor PDF Compressor API em http://{host}:{port}")
    print(f"Documentacao disponivel em http://{host}:{port}/docs")
    print(f"Health check em http://{host}:{port}/health")
    print("\nPressione Ctrl+C para parar o servidor\n")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

