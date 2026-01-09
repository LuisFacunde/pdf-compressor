@echo off
REM Script para iniciar o servidor PDF Compressor API
REM Uso: start_server.bat

echo Iniciando PDF Compressor API...
echo.

REM Define o PYTHONPATH para incluir o diretório src
set PYTHONPATH=%~dp0src

REM Inicia o servidor uvicorn
python -m uvicorn pdf_compressor.api.app:app --host 0.0.0.0 --port 8000

echo.
echo Servidor parado.
pause
