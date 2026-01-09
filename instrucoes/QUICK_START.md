# Guia Rápido de Execução - PDF Compressor API

## Pré-requisitos

1. **Python 3.7+** instalado
   ```bash
   python --version
   ```

2. **Ghostscript** instalado e no PATH
   - Windows: Baixe em https://www.ghostscript.com/download/gsdnld.html
   - Linux: `sudo apt-get install ghostscript` (Ubuntu/Debian)
   - macOS: `brew install ghostscript`

## Instalação

### 1. Clone o repositório (se ainda não tiver)
```bash
git clone <url-do-repositorio>
cd pdf-compressor
```

### 2. Crie um ambiente virtual (recomendado)
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python -m venv .venv
source .venv/bin/activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

## Execução

### Opção 1: Usando scripts (Recomendado)
```bash
# Windows - Clique duas vezes ou execute:
.\executaveis\start_server.bat

# PowerShell
.\executaveis\start_server.ps1
```

### Opção 2: Com uvicorn (manual)
```bash
# Windows PowerShell
$env:PYTHONPATH="src"; python -m uvicorn pdf_compressor.api.app:app --host 0.0.0.0 --port 8000

# Linux/macOS
PYTHONPATH=src python -m uvicorn pdf_compressor.api.app:app --host 0.0.0.0 --port 8000
```

## Verificação

Após iniciar o servidor, você verá:
```
Iniciando servidor PDF Compressor API em http://0.0.0.0:8000
Documentacao disponivel em http://0.0.0.0:8000/docs
Health check em http://0.0.0.0:8000/health

Pressione Ctrl+C para parar o servidor
```

### Testar se está funcionando

1. **Health Check:**
   ```bash
   curl http://localhost:8000/health
   ```
   Ou acesse no navegador: http://localhost:8000/health

2. **Documentação Interativa:**
   Acesse: http://localhost:8000/docs

3. **Endpoint raiz:**
   Acesse: http://localhost:8000/

## Endpoints Disponíveis

- `GET /` - Informações da API
- `GET /health` - Status do serviço
- `GET /api/v1/quality-settings` - Configurações de qualidade
- `POST /api/v1/compress` - Comprimir arquivo único
- `POST /api/v1/compress/batch` - Comprimir múltiplos arquivos
- `GET /api/v1/download/{file_id}` - Baixar arquivo comprimido
- `DELETE /api/v1/cleanup/{file_id}` - Limpar arquivos temporários

## Exemplo de Uso

### Com cURL (comprimir arquivo único)
```bash
curl -X POST "http://localhost:8000/api/v1/compress" \
  -F "file=@exame.pdf" \
  -F "quality=prepress"
```

### Com Python
```python
import requests

url = "http://localhost:8000/api/v1/compress"
files = {"file": open("exame.pdf", "rb")}
data = {"quality": "prepress"}

response = requests.post(url, files=files, data=data)
print(response.json())
```

## Parar o Servidor

Pressione `Ctrl+C` no terminal onde o servidor está rodando.

## Troubleshooting

### Erro: "Ghostscript not found"
- Verifique se o Ghostscript está instalado
- Verifique se está no PATH do sistema
- Reinicie o terminal após instalar

### Erro: "ModuleNotFoundError"
- Certifique-se de que o ambiente virtual está ativado
- Execute: `pip install -r requirements.txt`

### Porta 8000 já em uso
- Altere a porta no arquivo `server.py` ou use:
  ```bash
  uvicorn pdf_compressor.api.app:app --port 8001
  ```

