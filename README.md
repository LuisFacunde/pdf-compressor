# Compressor de PDFs Médicos

Aplicação desenvolvida para comprimir arquivos PDF de exames médicos visando poupar espaço de armazenamento nos servidores da **Fundação Altino Ventura**.

## 🏥 Sobre o Projeto

Este sistema foi desenvolvido especificamente para otimizar o armazenamento de exames médicos digitais na Fundação Altino Ventura. A ferramenta utiliza o Ghostscript para comprimir PDFs mantendo a qualidade necessária para diagnósticos médicos.

### 🎯 Objetivos

- **Economia de Espaço**: Reduzir significativamente o tamanho dos arquivos PDF
- **Preservação da Qualidade**: Manter a qualidade diagnóstica dos exames
- **Automação**: Processamento em lote para grandes volumes de arquivos
- **Confiabilidade**: Sistema robusto com logs detalhados e tratamento de erros

## ⚡ Funcionalidades

### ✨ Principais Recursos

- **Compressão em Lote**: Processa múltiplos PDFs automaticamente
- **Compressão Individual**: Comprime arquivos únicos quando necessário
- **Múltiplos Níveis de Qualidade**: 5 opções diferentes conforme a necessidade
- **Estatísticas Detalhadas**: Mostra economia de espaço e taxa de compressão
- **Logs Abrangentes**: Registro completo de todas as operações
- **Multiplataforma**: Funciona em Windows, Linux e macOS
- **Interface CLI Amigável**: Comandos simples e intuitivos
- **Validação Robusta**: Verifica integridade dos arquivos antes e após compressão

### 🔧 Funcionalidades Técnicas

- Detecção automática do Ghostscript
- Timeout para compressões longas
- Verificação de espaço em disco
- Preservação de metadados dos PDFs
- Tratamento de erros abrangente

## 🚀 Instalação

### Pré-requisitos

1. **Python 3.7+**
   ```bash
   python --version  # Verificar versão
   ```

2. **Ghostscript**
   
   **Windows:**
   - Baixe em: https://www.ghostscript.com/download/gsdnld.html
   - Instale a versão 64-bit se possível
   
   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt-get update
   sudo apt-get install ghostscript
   ```
   
   **Linux (CentOS/RHEL):**
   ```bash
   sudo yum install ghostscript
   ```
   
   **macOS:**
   ```bash
   brew install ghostscript
   ```

### Instalação do Projeto

1. **Clone o repositório:**
   ```bash
   git clone <url-do-repositório>
   cd compressor-pdfs
   ```

2. **Crie um ambiente virtual (recomendado):**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/macOS
   source .venv/bin/activate
   ```

3. **Instale as dependências (se houver):**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verifique a instalação:**
   ```bash
   python -m pdf_compressor --help
   ```

## 📖 Como Usar

### Uso Básico

```bash
# Comprimir todos os PDFs da pasta padrão
python -m pdf_compressor

# Especificar pastas de entrada e saída
python -m pdf_compressor -i ./pdfs_originais -o ./pdfs_comprimidos

# Comprimir um arquivo específico
python -m pdf_compressor --single exame.pdf exame_comprimido.pdf
```

### Opções Avançadas

```bash
# Compressão máxima (menor qualidade)
python -m pdf_compressor -q screen

# Modo verboso para mais detalhes
python -m pdf_compressor -v

# Sobrescrever arquivos existentes
python -m pdf_compressor --overwrite

# Combinando opções
python -m pdf_compressor -i ./exames -o ./comprimidos -q ebook -v --overwrite
```

### Ajuda Completa

```bash
python -m pdf_compressor --help
```

## 🎛️ Níveis de Qualidade

| Qualidade | DPI | Compressão | Tamanho Final | Uso Recomendado |
|-----------|-----|------------|---------------|-----------------|
| `screen` | 72 | **Máxima** | **Menor** | Visualização rápida, rascunhos |
| `ebook` | 150 | **Alta** | **Pequeno** | ⭐ **Recomendado para exames médicos** |
| `printer` | 300 | Média | Médio | Impressão de qualidade |
| `prepress` | 300+ | **Baixa** | **Maior** | Arquivamento profissional |
| `default` | Variável | Automática | Variável | Configuração padrão do Ghostscript |

### 💡 Recomendação para Uso Médico

Para exames médicos, recomendamos o nível **`ebook`** que oferece:
- ✅ Boa compressão (economia significativa de espaço)
- ✅ Qualidade suficiente para diagnóstico
- ✅ Carregamento rápido nos sistemas hospitalares
- ✅ Compatibilidade com impressoras médicas

## 📁 Estrutura do Projeto

```
compressor-pdfs/
├── src/
│   ├── pdf_compressor/
│   │   ├── __init__.py
│   │   ├── __main__.py          # Interface CLI principal
│   │   ├── compressor.py        # Lógica de compressão
│   │   └── config.py           # Configurações do sistema
│   └── data/
│       ├── input/
│       │   └── pdfs_originais/  # 📥 Coloque seus PDFs aqui
│       └── output/
│           └── pdfs_compactados/ # 📤 PDFs comprimidos ficam aqui
├── tests/
│   └── test_compressor.py       # Testes automatizados
├── logs/                        # 📋 Arquivos de log
├── scripts/                     # Scripts de exemplo/desenvolvimento
├── .gitignore
├── README.md
└── requirements.txt
```

## 📊 Logs e Monitoramento

### Sistema de Logs

O sistema gera logs detalhados em duas saídas:

1. **Console**: Informações em tempo real
2. **Arquivo**: `logs/pdf_compression.log`

### Informações dos Logs

- ✅ **Sucessos**: Nome do arquivo, tamanho original/final, % de economia
- ❌ **Erros**: Motivo da falha, arquivo problemático
- 📈 **Estatísticas**: Resumo do lote com economia total
- ⏱️ **Tempo**: Timestamp de todas as operações

### Exemplo de Log

```
2024-01-15 14:30:15 - INFO - Compressing retinografia.pdf with quality 'ebook'...
2024-01-15 14:30:18 - INFO - [✔] retinografia.pdf → retinografia_compress.pdf (2.5MB → 890KB, 64.4% reduction)
2024-01-15 14:30:20 - INFO - Batch compression complete: 5 successful, 0 failed. Overall space savings: 8.2MB (58.3% reduction)
```

## 💡 Exemplos
