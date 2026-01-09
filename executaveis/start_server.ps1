Write-Host "Iniciando PDF Compressor API..." -ForegroundColor Green
Write-Host ""

$env:PYTHONPATH = "$PSScriptRoot\src"

python -m uvicorn pdf_compressor.api.app:app --host 0.0.0.0 --port 8000

Write-Host ""
Write-Host "Servidor parado." -ForegroundColor Yellow
