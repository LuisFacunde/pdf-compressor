# Compressor de PDFs Médicos

Aplicação de linha de comando que usa o Ghostscript para regravar arquivos PDF e, quando possível, reduzir seu tamanho. Foi criada para auxiliar no armazenamento de exames médicos da **Fundação Altino Ventura**. A compressão pode alterar a qualidade e o conteúdo dos PDFs; valide os resultados conforme os requisitos do seu uso antes de utilizá-los em fluxos clínicos.

## Índice

- [Sobre o Projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
- [Instalação](#instalação)
- [Como Usar](#como-usar)
- [Níveis de Qualidade](#níveis-de-qualidade)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Logs e Monitoramento](#logs-e-monitoramento)

## Sobre o Projeto

Este sistema foi desenvolvido para auxiliar na otimização do armazenamento de exames médicos digitais na Fundação Altino Ventura. A ferramenta utiliza o Ghostscript para regravar PDFs; a qualidade resultante deve ser validada para cada necessidade.

### Objetivos

- **Economia de Espaço**: Reduzir significativamente o tamanho dos arquivos PDF
- **Perfis de compressão**: Escolher entre predefinições do Ghostscript
- **Automação**: Processamento em lote para grandes volumes de arquivos
- **Histórico**: Registrar as tentativas de compressão em um banco SQLite

## Funcionalidades

### Principais Recursos

- **Compressão em Lote**: Processa múltiplos PDFs automaticamente
- **Compressão Individual**: Comprime arquivos únicos quando necessário
- **Múltiplos Níveis de Qualidade**: 5 opções diferentes conforme a necessidade
- **Estatísticas Detalhadas**: Mostra economia de espaço e taxa de compressão
- **Logs**: Registra operações e erros no console e em arquivo
- **Multiplataforma**: Funciona em Windows, Linux e macOS
- **Interface CLI Amigável**: Comandos simples e intuitivos
- **Modo in-place**: Processa PDFs recursivamente e só substitui o original quando o resultado passa pelos critérios de tamanho

### Funcionalidades Técnicas

- Detecção automática do Ghostscript
- Timeout de 5 minutos por arquivo
- Processamento paralelo de lotes
- Histórico SQLite para identificar PDFs já processados no modo in-place
- Verificação de que o arquivo de saída existe e não está vazio

## Instalação

### Pré-requisitos

1. **Python 3.9 ou superior**. O comando pode ser `python`, `python3` ou `py -3`, conforme o sistema.

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

### Obter o projeto e criar um ambiente virtual

Clone o repositório e entre na pasta do projeto:

```bash
git clone https://github.com/LuisFacunde/pdf-compressor.git
cd pdf-compressor
```

Crie e ative um ambiente virtual usando as instruções do seu sistema.

#### Windows — PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### Linux

Em distribuições Debian/Ubuntu, se o módulo `venv` não estiver instalado, instale-o com `sudo apt install python3-venv`.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Com o ambiente virtual ativado, instale as dependências e confira a ajuda:

```bash
python -m pip install -r requirements.txt
python pdf_compressor.py --help
```

Para sair do ambiente virtual quando terminar:

```bash
deactivate
```

## Como Usar

Execute os comandos a partir da raiz do repositório, com o ambiente virtual ativado. O script `pdf_compressor.py` inicia a interface de linha de comando.

### Uso Básico

```bash
# Comprimir todos os PDFs da pasta padrão
python pdf_compressor.py

# Especificar pastas de entrada e saída
python pdf_compressor.py -i ./pdfs_originais -o ./pdfs_comprimidos

# Comprimir um arquivo específico
python pdf_compressor.py --single exame.pdf exame_comprimido.pdf
```

No processamento em lote normal, são encontrados PDFs diretamente na pasta de entrada. Com `--in-place`, a busca é recursiva e os arquivos são processados no próprio local. O modo in-place mantém o original se o resultado não for menor; a opção `--force` permite reprocessar arquivos que o histórico indica como já comprimidos.

### Executar em uma pasta específica com `--in-place`

Informe a pasta a ser pesquisada com `-i` ou `--input-dir`. A busca inclui subpastas. Nesse modo os PDFs podem ser substituídos pelos resultados comprimidos; faça uma cópia de segurança antes de executar. A opção `-o` não é necessária e é ignorada nesse modo.

**Windows (PowerShell):**

```powershell
python pdf_compressor.py --input-dir "C:\Exames\Pendentes" --in-place
```

**Linux/macOS:**

```bash
python pdf_compressor.py --input-dir "/dados/exames/pendentes" --in-place
```

Para escolher outro perfil de qualidade ou quantidade de processos, acrescente `-q` e `-j`. Por exemplo:

```bash
python pdf_compressor.py -i "/dados/exames/pendentes" --in-place -q ebook -j 4
```

O perfil `prepress` é o padrão do programa. Para reprocessar PDFs que o histórico reconhece como já processados, acrescente `--force`.

### Opções Avançadas

```bash
# Compressão máxima (menor qualidade)
python pdf_compressor.py -q screen

# Modo verboso para mais detalhes
python pdf_compressor.py -v

# Sobrescrever arquivos existentes
python pdf_compressor.py --overwrite

# Combinando opções
python pdf_compressor.py -i ./exames --in-place -q ebook -j 4

# Exibir os registros mais recentes do histórico (opcionalmente filtrados por pasta)
python pdf_compressor.py --history
python pdf_compressor.py --history ./exames
```

### Ajuda Completa

```bash
python pdf_compressor.py --help
```

## Níveis de Qualidade

Os nomes abaixo são perfis `PDFSETTINGS` do Ghostscript. O resultado depende do conteúdo do arquivo; os tamanhos e a qualidade finais não são garantidos.

| Qualidade | Perfil | Uso geral |
|-----------|--------|-----------|
| `screen` | Maior compressão, menor qualidade | Visualização em tela |
| `ebook` | Compressão e qualidade intermediárias | Leitura digital |
| `printer` | Maior qualidade para impressão | Impressão |
| `prepress` | Perfil voltado à pré-impressão | Arquivos que exigem maior qualidade |
| `default` | Configuração padrão do Ghostscript | Quando não se deseja escolher outro perfil |

O programa usa `prepress` quando a opção `-q/--quality` não é informada. `default` é outro perfil disponível do Ghostscript e só será usado se solicitado explicitamente com `-q default`.

### Recomendação para Uso Médico

Não há garantia de que qualquer perfil preserve a qualidade necessária para diagnóstico. Compare os PDFs resultantes com os originais e confirme que atendem aos critérios técnicos e clínicos aplicáveis antes de adotá-los.

## Estrutura do Projeto

```
pdf-compressor/
├── pdf_compressor.py           # Ponto de entrada da CLI (python pdf_compressor.py)
├── src/
│   ├── __init__.py
│   ├── compressor.py            # Compressão de PDFs e processamento em lote
│   ├── config.py                # Configurações e caminhos padrão
│   └── history.py               # Histórico SQLite
├── tests/
│   ├── test_compressor.py
│   └── test_history.py
├── logs/                        # Criado para o arquivo de log
├── historico/                   # Criado para o banco SQLite
├── README.md
└── requirements.txt
```

Por padrão, a entrada e a saída do lote ficam em `src/data/input/pdfs_originais` e `src/data/output/pdfs_compactados`. A pasta de entrada deve existir; a pasta de saída é criada quando necessário. Também é possível informar caminhos próprios com `-i` e `-o`.

## Logs e Monitoramento

### Sistema de Logs

O sistema gera logs detalhados em duas saídas:

1. **Console**: Informações em tempo real
2. **Arquivo**: `logs/pdf_compression.log`

### Informações dos Logs

- ✅ **Sucessos**: Nome do arquivo, tamanho original/final, % de economia
- ❌ **Erros**: Motivo da falha, arquivo problemático
- 📈 **Estatísticas**: Resumo do lote com economia total
- ⏱️ **Tempo**: Timestamp de todas as operações

O histórico pode ser consultado pela opção `--history`. No modo in-place, ele também é usado para evitar o reprocessamento de arquivos que não foram modificados desde a última compressão com a mesma qualidade.
