# Guia Rápido - Como Executar o PDF Compressor

## Servidor já está rodando!

O servidor está ativo em **http://localhost:8000**

---

## Acessar a Documentação

Abra seu navegador e acesse:

### 1. **Documentação Interativa (Swagger)**
```
http://localhost:8000/docs
```
Aqui você pode testar todos os endpoints diretamente!

### 2. **Health Check**
```
http://localhost:8000/health
```
Verifica se o servidor está funcionando.

### 3. **Página Inicial**
```
http://localhost:8000/
```

---

## Como Iniciar o Servidor (próximas vezes)

### **Opção 1: Usando o script (MAIS FÁCIL)**

Basta clicar duas vezes em:
```
start_server.bat
```

Ou no PowerShell:
```powershell
.\start_server.ps1
```

### **Opção 2: Comando manual**

```powershell
$env:PYTHONPATH="c:\Users\luis.silva\Desktop\pdf-compressor\src"; python -m uvicorn pdf_compressor.api.app:app --host 0.0.0.0 --port 8000
```

---

## Como Parar o Servidor

Pressione **Ctrl+C** no terminal onde o servidor está rodando.

---

## Endpoints Disponíveis

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/` | Informações da API |
| `GET` | `/health` | Status do serviço |
| `GET` | `/api/v1/quality-settings` | Configurações de qualidade |
| `POST` | `/api/v1/compress` | Comprimir um arquivo PDF |
| `POST` | `/api/v1/compress/batch` | Comprimir múltiplos PDFs |
| `GET` | `/api/v1/download/{file_id}` | Baixar arquivo comprimido |

---

## Exemplo de Uso

### Com PowerShell (Invoke-WebRequest)

```powershell
# Comprimir um arquivo
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/compress" `
    -Method POST `
    -Form @{
        file = Get-Item "C:\caminho\para\seu\arquivo.pdf"
        quality = "prepress"
    } `
    -UseBasicParsing

$response.Content
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

### Com cURL

```bash
curl -X POST "http://localhost:8000/api/v1/compress" \
  -F "file=@exame.pdf" \
  -F "quality=prepress"
```

---

## Níveis de Qualidade

| Qualidade | Uso Recomendado |
|-----------|-----------------|
| `screen` | Visualização rápida (menor tamanho) |
| `ebook` | Visualização web |
| `printer` | Impressão de qualidade |
| `prepress` | **Arquivamento profissional** (recomendado para exames médicos) |
| `default` | Padrão do Ghostscript |

---

## Problemas Comuns

### Erro: "ModuleNotFoundError"
**Solução:** Instale as dependências:
```powershell
python -m pip install -r requirements.txt
```

### Erro: "Porta 8000 já em uso"
**Solução:** Use outra porta:
```powershell
$env:PYTHONPATH="src"; python -m uvicorn pdf_compressor.api.app:app --port 8001
```

### Erro: "Ghostscript not found"
**Solução:** 
1. Baixe o Ghostscript: https://www.ghostscript.com/download/gsdnld.html
2. Instale e reinicie o terminal
3. Verifique se está no PATH do sistema

---

## Documentação Completa

- [README.md](README.md) - Documentação completa do projeto
- [API_USAGE.md](API_USAGE.md) - Guia detalhado da API
- [ARCHITECTURE.md](ARCHITECTURE.md) - Arquitetura do projeto
- [QUICK_START.md](QUICK_START.md) - Guia de início rápido

---

## Checklist de Instalação

- [x] Python 3.7+ instalado
- [x] Dependências instaladas (`pip install -r requirements.txt`)
- [x] Servidor iniciado com sucesso
- [ ] Ghostscript instalado (necessário para comprimir PDFs)
- [ ] Testado endpoint `/health`
- [ ] Acessado documentação em `/docs`

---

**Servidor rodando em:** http://localhost:8000  
**Documentação:** http://localhost:8000/docs  
**Health Check:** http://localhost:8000/health
