# PDF Compressor API

API RESTful para compressão de arquivos PDF de exames médicos.

## Funcionalidades

- Compressão de arquivos PDF individuais
- Compressão em lote de múltiplos arquivos
- Diferentes níveis de qualidade de compressão
- Compressão inteligente (mantém arquivo original se a redução for menor que 20%)
- Monitoramento de status da API
- Suporte a CORS
- Autenticação via API Key (opcional)

## Requisitos

- Python 3.8+
- FastAPI
- uvicorn
- python-multipart
- typing-extensions
- GhostScript (necessário para a compressão de PDFs)

## Instalação

1. Clone o repositório:
```bash
git clone [seu-repositorio]
cd pdf-compressor
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente (opcional):
Crie um arquivo `.env` na raiz do projeto com as seguintes configurações:

```env
# Configurações do servidor
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1
DEBUG=False

# Configurações do compressor
DEFAULT_QUALITY=prepress
MIN_COMPRESSION_RATIO=0.2  # 20% de redução mínima
ALLOWED_FILE_TYPES=[".pdf"]

# Configurações de segurança
API_KEY=  # Deixe em branco para desabilitar a autenticação
ENABLE_CORS=True
ALLOWED_ORIGINS=["*"]
```

## Como Executar a API

1. Abra o terminal na pasta do projeto

2. Inicie o servidor com um dos comandos abaixo:

   **Windows (PowerShell):**
   ```powershell
   python -m src.pdf_compressor.api
   ```
   
   **Linux/Mac:**
   ```bash
   python3 -m src.pdf_compressor.api
   ```

3. A API estará disponível em: http://localhost:8000

## Acessando a Documentação (Swagger)

1. Com a API em execução, abra seu navegador e acesse:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc (alternativa): http://localhost:8000/redoc

2. No Swagger UI você pode:
   - Ver todos os endpoints disponíveis
   - Testar a API diretamente pelo navegador
   - Ver os modelos de dados e parâmetros
   - Fazer upload de arquivos para teste
   - Ver as respostas e códigos de status

## Endpoints Disponíveis

### GET /status
Verifica o status da API e retorna informações básicas do sistema.

### POST /compress/
Comprime um único arquivo PDF.

**Parâmetros:**
- `file`: Arquivo PDF a ser comprimido
- `quality`: Nível de qualidade (screen, ebook, printer, prepress)
- `X-API-Key`: Chave de API (se configurada)

**Resposta:**
- Arquivo PDF comprimido (se a redução for >= 20%)
- Arquivo original (se a redução for < 20%)
- Header `X-Compression-Ratio` com a taxa de compressão alcançada

### POST /compress-batch/
Comprime múltiplos arquivos PDF em lote.

**Parâmetros:**
- `files`: Lista de arquivos PDF
- `quality`: Nível de qualidade (screen, ebook, printer, prepress)
- `X-API-Key`: Chave de API (se configurada)

**Resposta:**
- Lista com resultados da compressão de cada arquivo
- Taxa de compressão para cada arquivo
- Mensagens de sucesso/erro individuais

## Exemplos de Uso

### Python
```python
import requests

# Comprimir um único arquivo
files = {'file': open('exemplo.pdf', 'rb')}
response = requests.post('http://localhost:8000/compress/', files=files)

# Ver a taxa de compressão
compression_ratio = response.headers.get('X-Compression-Ratio')
print(f'Taxa de compressão: {compression_ratio}')

# Comprimir múltiplos arquivos
files = [
    ('files', open('exemplo1.pdf', 'rb')),
    ('files', open('exemplo2.pdf', 'rb'))
]
response = requests.post('http://localhost:8000/compress-batch/', files=files)
results = response.json()
```

### cURL
```bash
# Comprimir um único arquivo
curl -X POST "http://localhost:8000/compress/" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@exemplo.pdf"

# Comprimir múltiplos arquivos
curl -X POST "http://localhost:8000/compress-batch/" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@exemplo1.pdf" \
  -F "files=@exemplo2.pdf"
```

## Segurança

- Use HTTPS em produção
- Configure uma API Key forte se necessário
- Ajuste as configurações CORS conforme necessário
- Monitore o uso da API

## Solução de Problemas

1. Se a API não iniciar, verifique:
   - Se todas as dependências estão instaladas
   - Se a porta 8000 não está em uso
   - Se o Python está no PATH do sistema

2. Se a compressão falhar, verifique:
   - Se o GhostScript está instalado
   - Se o arquivo PDF é válido
   - Se há espaço em disco suficiente