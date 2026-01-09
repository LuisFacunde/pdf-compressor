# API de Compressão de PDFs - Guia de Uso

## Iniciar o Servidor

```bash
# Instalar dependências
pip install -r requirements.txt

# Iniciar o servidor
python -m pdf_compressor.server

# Ou diretamente
python src/pdf_compressor/server.py
```

O servidor estará disponível em `http://localhost:8000`

## Documentação Interativa

Acesse `http://localhost:8000/docs` para ver a documentação interativa do Swagger UI.

## Endpoints Disponíveis

### 1. Health Check
```http
GET /health
```

Verifica se o serviço está funcionando e se o Ghostscript está disponível.

**Resposta:**
```json
{
  "status": "healthy",
  "ghostscript_available": true,
  "ghostscript_command": "gswin64c"
}
```

### 2. Compressão de Arquivo Único
```http
POST /api/v1/compress
Content-Type: multipart/form-data
```

**Parâmetros:**
- `file` (arquivo): Arquivo PDF a ser comprimido
- `quality` (string, opcional): Nível de qualidade (`screen`, `ebook`, `printer`, `prepress`, `default`). Padrão: `prepress`

**Exemplo com cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/compress" \
  -F "file=@exame.pdf" \
  -F "quality=prepress"
```

**Resposta:**
```json
{
  "success": true,
  "message": "Compressão concluída com sucesso",
  "original_size": 5242880,
  "compressed_size": 2097152,
  "compression_ratio": 60.0,
  "original_size_formatted": "5.00MB",
  "compressed_size_formatted": "2.00MB",
  "file_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Download do arquivo comprimido:**
```http
GET /api/v1/download/{file_id}
```

### 3. Compressão em Lote
```http
POST /api/v1/compress/batch
Content-Type: multipart/form-data
```

**Parâmetros:**
- `files` (array de arquivos): Lista de arquivos PDF para comprimir
- `quality` (string, opcional): Nível de qualidade. Padrão: `prepress`

**Exemplo com cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/compress/batch" \
  -F "files=@exame1.pdf" \
  -F "files=@exame2.pdf" \
  -F "quality=prepress"
```

**Resposta:**
```json
{
  "success": true,
  "message": "Processados 2 arquivos: 2 sucessos, 0 falhas",
  "total_files": 2,
  "successful": 2,
  "failed": 0,
  "total_original_size": 10485760,
  "total_compressed_size": 4194304,
  "overall_compression_ratio": 60.0,
  "files": [
    {
      "file_name": "exame1.pdf",
      "success": true,
      "error": null,
      "file_id": "550e8400-e29b-41d4-a716-446655440001",
      "original_size": 5242880,
      "compressed_size": 2097152,
      "compression_ratio": 60.0,
      "original_size_formatted": "5.00MB",
      "compressed_size_formatted": "2.00MB"
    },
    {
      "file_name": "exame2.pdf",
      "success": true,
      "error": null,
      "file_id": "550e8400-e29b-41d4-a716-446655440002",
      "original_size": 5242880,
      "compressed_size": 2097152,
      "compression_ratio": 60.0,
      "original_size_formatted": "5.00MB",
      "compressed_size_formatted": "2.00MB"
    }
  ]
}
```

### 4. Obter Configurações de Qualidade
```http
GET /api/v1/quality-settings
```

Retorna todas as configurações de qualidade disponíveis.

## Exemplo de Uso com TypeScript/Node.js

### Usando Fetch API

```typescript
// Comprimir um arquivo único
async function compressPDF(file: File, quality: string = 'prepress') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('quality', quality);

  const response = await fetch('http://localhost:8000/api/v1/compress', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Erro na compressão: ${response.statusText}`);
  }

  const result = await response.json();
  
  // Baixar arquivo comprimido
  if (result.success && result.file_id) {
    const downloadUrl = `http://localhost:8000/api/v1/download/${result.file_id}`;
    window.open(downloadUrl, '_blank');
  }

  return result;
}

// Comprimir múltiplos arquivos
async function compressPDFBatch(files: File[], quality: string = 'prepress') {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });
  formData.append('quality', quality);

  const response = await fetch('http://localhost:8000/api/v1/compress/batch', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Erro na compressão: ${response.statusText}`);
  }

  return await response.json();
}
```

### Usando Axios

```typescript
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// Comprimir arquivo único
async function compressPDF(file: File, quality: string = 'prepress') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('quality', quality);

  const response = await axios.post(
    `${API_BASE_URL}/api/v1/compress`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return response.data;
}

// Comprimir em lote
async function compressPDFBatch(files: File[], quality: string = 'prepress') {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });
  formData.append('quality', quality);

  const response = await axios.post(
    `${API_BASE_URL}/api/v1/compress/batch`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return response.data;
}

// Verificar saúde do serviço
async function checkHealth() {
  const response = await axios.get(`${API_BASE_URL}/health`);
  return response.data;
}
```

### Exemplo Completo com React

```typescript
import React, { useState } from 'react';
import axios from 'axios';

const PDFCompressor: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [quality, setQuality] = useState('prepress');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleCompress = async () => {
    if (!file) return;

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('quality', quality);

      const response = await axios.post(
        'http://localhost:8000/api/v1/compress',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      setResult(response.data);
      
      // Baixar arquivo comprimido
      if (response.data.success && response.data.file_id) {
        window.open(
          `http://localhost:8000/api/v1/download/${response.data.file_id}`,
          '_blank'
        );
      }
    } catch (error) {
      console.error('Erro ao comprimir:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="file"
        accept=".pdf"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <select value={quality} onChange={(e) => setQuality(e.target.value)}>
        <option value="screen">Screen (Máxima compressão)</option>
        <option value="ebook">Ebook (Alta compressão)</option>
        <option value="printer">Printer (Média compressão)</option>
        <option value="prepress">Prepress (Baixa compressão, alta qualidade)</option>
      </select>
      <button onClick={handleCompress} disabled={!file || loading}>
        {loading ? 'Comprimindo...' : 'Comprimir PDF'}
      </button>
      {result && (
        <div>
          <p>Status: {result.success ? 'Sucesso' : 'Falha'}</p>
          {result.success && (
            <>
              <p>Tamanho original: {result.original_size_formatted}</p>
              <p>Tamanho comprimido: {result.compressed_size_formatted}</p>
              <p>Redução: {result.compression_ratio.toFixed(1)}%</p>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default PDFCompressor;
```

## Níveis de Qualidade

| Qualidade | DPI | Compressão | Uso Recomendado |
|-----------|-----|------------|-----------------|
| `screen` | 72 | Máxima | Visualização rápida |
| `ebook` | 150 | Alta | Arquivos médicos para web |
| `printer` | 300 | Média | Impressão de qualidade |
| `prepress` | 300+ | Baixa | Arquivamento profissional (recomendado para exames médicos) |
| `default` | Variável | Automática | Balanceamento automático |

## Limitações

- Tamanho máximo de arquivo: 500 MB
- Máximo de arquivos por lote: 100
- Arquivos temporários são mantidos por 24 horas (podem ser limpos manualmente via endpoint `/api/v1/cleanup/{file_id}`)

## CORS

Por padrão, a API aceita requisições de qualquer origem. Em produção, configure o CORS no arquivo `api.py` para permitir apenas domínios específicos.

