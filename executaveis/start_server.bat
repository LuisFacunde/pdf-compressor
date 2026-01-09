@echo off

echo Iniciando PDF Compressor API...
echo.

set PYTHONPATH=%~dp0src

python -m uvicorn pdf_compressor.api.app:app --host 0.0.0.0 --port 8000

echo.
echo Servidor parado.
pause
