from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import shutil
import tempfile
from typing import List
from .compressor import compress_pdf
import uvicorn

app = FastAPI(
    title="PDF Compressor API",
    description="API para compressão de arquivos PDF de exames médicos",
    version="1.0.0"
)

# Diretório temporário para armazenar arquivos durante o processamento
TEMP_DIR = Path(tempfile.gettempdir()) / "pdf_compressor"
TEMP_DIR.mkdir(exist_ok=True)

@app.post("/compress/", summary="Comprimir um único arquivo PDF")
async def compress_single_pdf(
    file: UploadFile = File(...),
    quality: str = "prepress"
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser um PDF")
    
    # Salva o arquivo temporariamente
    temp_input = TEMP_DIR / f"input_{file.filename}"
    temp_output = TEMP_DIR / f"output_{file.filename}"
    
    try:
        # Salva o arquivo recebido
        with temp_input.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Comprime o PDF
        success, message = compress_pdf(temp_input, temp_output, quality)
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        # Retorna o arquivo comprimido
        return FileResponse(
            path=temp_output,
            filename=f"compressed_{file.filename}",
            media_type="application/pdf"
        )
    
    finally:
        # Limpa os arquivos temporários
        if temp_input.exists():
            temp_input.unlink()
        if temp_output.exists():
            temp_output.unlink()

@app.post("/compress-batch/", summary="Comprimir múltiplos arquivos PDF")
async def compress_multiple_pdfs(
    files: List[UploadFile] = File(...),
    quality: str = "prepress"
):
    results = []
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            results.append({"filename": file.filename, "success": False, "message": "Não é um arquivo PDF"})
            continue
            
        temp_input = TEMP_DIR / f"input_{file.filename}"
        temp_output = TEMP_DIR / f"output_{file.filename}"
        
        try:
            with temp_input.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            success, message = compress_pdf(temp_input, temp_output, quality)
            
            if success:
                # Lê o arquivo comprimido em bytes para retornar
                compressed_bytes = temp_output.read_bytes()
                results.append({
                    "filename": file.filename,
                    "success": True,
                    "message": message,
                    "compressed_file": compressed_bytes
                })
            else:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "message": message
                })
                
        finally:
            if temp_input.exists():
                temp_input.unlink()
            if temp_output.exists():
                temp_output.unlink()
    
    return results

if __name__ == "__main__":
    uvicorn.run("pdf_compressor.api:app", host="0.0.0.0", port=8000, reload=True) 