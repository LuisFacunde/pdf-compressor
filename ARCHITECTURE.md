# Arquitetura do Projeto - PDF Compressor

## Estrutura Organizada

O projeto foi reorganizado seguindo princípios de **Clean Architecture** e **Separation of Concerns**:

```
src/pdf_compressor/
├── api/                          # Camada de API REST
│   ├── __init__.py
│   ├── app.py                   # Aplicação FastAPI principal
│   ├── middleware.py             # Configuração de CORS e middlewares
│   ├── routes/                   # Rotas organizadas por funcionalidade
│   │   ├── __init__.py
│   │   ├── compression.py        # Rotas de compressão
│   │   ├── health.py             # Rotas de health check
│   │   └── info.py               # Rotas de informações
│   └── schemas/                  # Modelos Pydantic
│       ├── __init__.py
│       └── responses.py           # Schemas de resposta da API
│
├── core/                         # Configurações e utilitários centrais
│   ├── __init__.py
│   ├── config.py                 # Configurações da aplicação
│   └── logging_config.py         # Configuração de logging
│
├── services/                     # Lógica de negócio
│   ├── __init__.py
│   ├── compression_service.py    # Serviço de compressão de PDFs
│   └── file_service.py           # Serviço de processamento de arquivos
│
├── repositories/                  # Camada de acesso a dados
│   ├── __init__.py
│   └── file_repository.py        # Gerenciamento de arquivos temporários
│
├── utils/                        # Utilitários gerais
│   ├── __init__.py
│   ├── file_utils.py              # Utilitários de arquivo
│   └── validators.py              # Validadores de entrada
│
├── __init__.py
├── __main__.py                   # Interface CLI (compatibilidade)
├── compressor.py                 # Módulo de compatibilidade CLI
├── config.py                     # Config de compatibilidade (deprecated)
└── server.py                     # Script para iniciar servidor
```

## Princípios Aplicados

### 1. **Separation of Concerns**
- **API Layer**: Apenas recebe requisições e retorna respostas
- **Service Layer**: Contém a lógica de negócio
- **Repository Layer**: Gerencia acesso a dados/arquivos
- **Utils**: Funções auxiliares reutilizáveis

### 2. **Single Responsibility**
- Cada módulo tem uma responsabilidade única e bem definida
- Serviços são focados em uma funcionalidade específica
- Rotas são organizadas por domínio

### 3. **Dependency Inversion**
- Serviços dependem de abstrações (repositórios)
- Fácil de testar e mockar dependências

### 4. **DRY (Don't Repeat Yourself)**
- Funções utilitárias centralizadas
- Validações reutilizáveis
- Configurações centralizadas

## Fluxo de Dados

### Compressão via API:
```
Request → Route → Validator → FileService → CompressionService → Repository → Response
```

### Compressão via CLI:
```
CLI → compressor.py → CompressionService → Response
```

## Módulos Principais

### `api/`
- **Responsabilidade**: Receber requisições HTTP e retornar respostas
- **Não deve conter**: Lógica de negócio
- **Depende de**: Services, Schemas, Validators

### `services/`
- **Responsabilidade**: Lógica de negócio da aplicação
- **Não deve conter**: Detalhes de HTTP, acesso a arquivos
- **Depende de**: Repositories, Utils

### `repositories/`
- **Responsabilidade**: Gerenciar acesso a dados/arquivos
- **Não deve conter**: Lógica de negócio
- **Depende de**: Core (config)

### `utils/`
- **Responsabilidade**: Funções auxiliares reutilizáveis
- **Não deve conter**: Lógica de negócio específica
- **Depende de**: Core (config)

### `core/`
- **Responsabilidade**: Configurações e setup centralizados
- **Não deve conter**: Lógica de negócio
- **Usado por**: Todos os outros módulos

## Benefícios da Nova Estrutura

1. **Manutenibilidade**: Código organizado e fácil de encontrar
2. **Testabilidade**: Módulos isolados são mais fáceis de testar
3. **Escalabilidade**: Fácil adicionar novas funcionalidades
4. **Legibilidade**: Código mais limpo e fácil de entender
5. **Reutilização**: Utilitários e serviços podem ser reutilizados

## Compatibilidade

O projeto mantém compatibilidade com código antigo:
- `compressor.py` ainda funciona para CLI
- `config.py` está deprecated mas ainda funciona
- Todas as funções públicas mantêm a mesma interface

## Próximos Passos Sugeridos

1. Adicionar injeção de dependência (FastAPI Depends)
2. Implementar testes unitários para cada camada
3. Adicionar documentação de código (docstrings)
4. Implementar cache para arquivos processados
5. Adicionar rate limiting na API

