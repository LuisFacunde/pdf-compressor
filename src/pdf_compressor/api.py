from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import tempfile
from typing import List, Optional
from .compressor import compress_pdf
from .config import settings
import uvicorn
import time

app = FastAPI(
    title="PDF Compressor API",
    description="""
    API para compressão de arquivos PDF de exames médicos.
    
    Funcionalidades:
    - Compressão de arquivos PDF individuais
    - Compressão em lote de múltiplos arquivos
    - Diferentes níveis de qualidade de compressão
    - Monitoramento de status da API
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuração do CORS
if settings.ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Diretório temporário para armazenar arquivos durante o processo de compressão
TEMP_DIR = Path(tempfile.gettempdir()) / "pdf_compressor"
TEMP_DIR.mkdir(exist_ok=True)

# Função para verificar a API key
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if settings.API_KEY and x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="API key inválida ou não fornecida"
        )
    return x_api_key

# Middleware para logging
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/status", summary="Verificar status da API")
async def check_status():
    # Retorna o status atual da API e informações do sistema
    return {
        "status": "online",
        "version": app.version,
        "max_file_size": settings.MAX_FILE_SIZE,
        "allowed_file_types": settings.ALLOWED_FILE_TYPES
    }

@app.post("/compress/", summary="Comprimir um único arquivo PDF")
async def compress_single_pdf(
    file: UploadFile = File(...),
    quality: str = settings.DEFAULT_QUALITY,
    api_key: str = Depends(verify_api_key)
):
    # Comprime um único arquivo PDF.
    # - *file*: Arquivo PDF a ser comprimido
    # - *quality*: Nível de qualidade da compressão (screen, ebook, printer, prepress)
    # Retorna o arquivo PDF comprimido.

    # Validação do arquivo (verificar se é um PDF)
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser um PDF")
    
    # Processamento do arquivo (chama a função de compressão)
    temp_input = TEMP_DIR / f"input_{file.filename}"
    temp_output = TEMP_DIR / f"output_{file.filename}"
    
    try:
        # Salva o arquivo original
        with temp_input.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Obtém o tamanho original do arquivo
        original_size = temp_input.stat().st_size
        
        # Tenta comprimir o PDF
        success, message = compress_pdf(temp_input, temp_output, quality)
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        # Verifica a taxa de compressão
        compressed_size = temp_output.stat().st_size
        compression_ratio = 1 - (compressed_size / original_size)
        
        # Se a compressão não atingiu o mínimo esperado, usa o arquivo original
        if compression_ratio < settings.MIN_COMPRESSION_RATIO:
            return FileResponse(
                path=temp_input,
                filename=f"original_{file.filename}",
                media_type="application/pdf",
                headers={"X-Compression-Ratio": f"{compression_ratio:.2%}"}
            )
        
        return FileResponse(
            path=temp_output,
            filename=f"compressed_{file.filename}",
            media_type="application/pdf",
            headers={"X-Compression-Ratio": f"{compression_ratio:.2%}"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if temp_input.exists():
            temp_input.unlink()
        if temp_output.exists():
            temp_output.unlink()

@app.post("/compress-batch/", summary="Comprimir múltiplos arquivos PDF")
async def compress_multiple_pdfs(
    files: List[UploadFile] = File(...),
    quality: str = settings.DEFAULT_QUALITY,
    api_key: str = Depends(verify_api_key)
):
    # Comprime múltiplos arquivos PDF em lote.
    # - *files*: Lista de arquivos PDF a serem comprimidos
    # - *quality*: Nível de qualidade da compressão (screen, ebook, printer, prepress)
    # Retorna uma lista com os resultados da compressão de cada arquivo.

    results = []
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            results.append({
                "filename": file.filename,
                "success": False,
                "message": "Não é um arquivo PDF",
                "compression_ratio": 0
            })
            continue
            
        temp_input = TEMP_DIR / f"input_{file.filename}"
        temp_output = TEMP_DIR / f"output_{file.filename}"
        
        try:
            # Salva o arquivo original
            with temp_input.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Obtém o tamanho original do arquivo
            original_size = temp_input.stat().st_size
            
            # Tenta comprimir o PDF
            success, message = compress_pdf(temp_input, temp_output, quality)
            
            if success:
                # Verifica a taxa de compressão
                compressed_size = temp_output.stat().st_size
                compression_ratio = 1 - (compressed_size / original_size)
                
                # Se a compressão não atingiu o mínimo esperado, usa o arquivo original
                if compression_ratio < settings.MIN_COMPRESSION_RATIO:
                    compressed_bytes = temp_input.read_bytes()
                    results.append({
                        "filename": file.filename,
                        "success": True,
                        "message": "Arquivo original mantido (compressão insuficiente)",
                        "compression_ratio": f"{compression_ratio:.2%}",
                        "compressed_file": compressed_bytes
                    })
                else:
                    compressed_bytes = temp_output.read_bytes()
                    results.append({
                        "filename": file.filename,
                        "success": True,
                        "message": "Arquivo comprimido com sucesso",
                        "compression_ratio": f"{compression_ratio:.2%}",
                        "compressed_file": compressed_bytes
                    })
            else:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "message": message,
                    "compression_ratio": "0%"
                })
                
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "message": str(e),
                "compression_ratio": "0%"
            })
            
        finally:
            if temp_input.exists():
                temp_input.unlink()
            if temp_output.exists():
                temp_output.unlink()
    
    return results

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "path": str(request.url)
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "pdf_compressor.api:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        workers=settings.API_WORKERS,
        reload=settings.DEBUG
    ) 