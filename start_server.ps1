# Script para iniciar o servidor PDF Compressor API
# Uso: .\start_server.ps1

Write-Host "Iniciando PDF Compressor API..." -ForegroundColor Green
Write-Host ""

# Define o PYTHONPATH para incluir o diretório src
$env:PYTHONPATH = "$PSScriptRoot\src"

# Inicia o servidor uvicorn
python -m uvicorn pdf_compressor.api.app:app --host 0.0.0.0 --port 8000

Write-Host ""
Write-Host "Servidor parado." -ForegroundColor Yellow
