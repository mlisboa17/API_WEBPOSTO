# Prompt para Cursor - webposto-service

Copie e cole tudo isso no Cursor:

---

Você é um **Arquiteto de Software Sênior**. Você vai criar um sistema profissional, production-ready, seguindo as melhores práticas de engenharia de software.

## Requisitos Técnicos

### 1. Arquitetura
- **Padrão:** Hexagonal Architecture (Ports & Adapters) + Event-Driven
- **Objetivo:** Integração com webPosto REST API alimentando múltiplos serviços internos
- **Linguagem:** Python 3.11+
- **Framework:** FastAPI (async)

### 2. Stack Tecnológico
- **API Rest:** FastAPI
- **Validação:** Pydantic v2
- **HTTP Client:** HTTPX com retry automático
- **Banco de Dados:** PostgreSQL + SQLAlchemy ORM
- **Migrations:** Alembic
- **Cache:** Redis
- **Event Bus:** Redis Pub/Sub
- **Testes:** pytest + testcontainers + responses
- **Container:** Docker + docker-compose
- **CI/CD:** GitHub Actions
- **Documentação:** Swagger automático (FastAPI) + README

### 3. Boas Práticas Obrigatórias
- SOLID Principles (SRP, OCP, DIP, ISP, LSP)
- Clean Code
- Domain-Driven Design (DDD)
- Testes: unitários, integração, E2E (100% coverage mínimo)
- Logging estruturado (JSON)
- Error handling com exceções tipadas
- Versionamento semântico
- Commit messages: Conventional Commits
- Segurança: OWASP Top 10
- Rate limiting, retry logic, circuit breaker

### 4. Estrutura do Projeto

```
webposto-service/
├── src/
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   ├── cliente.py        # Entity: Cliente
│   │   │   ├── abastecimento.py  # Entity: Abastecimento
│   │   │   ├── financeiro.py     # Entity: Financeiro
│   │   │   ├── caixa.py          # Entity: Caixa
│   │   │   └── produto.py        # Entity: Produto
│   │   │
│   │   ├── events/
│   │   │   ├── __init__.py
│   │   │   ├── base_event.py     # BaseEvent class
│   │   │   ├── cliente_events.py # ClienteAdicionado, ClienteAtualizado, etc
│   │   │   ├── abastecimento_events.py
│   │   │   ├── financeiro_events.py
│   │   │   └── caixa_events.py
│   │   │
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── cliente_repository.py        # Interface (port)
│   │   │   ├── abastecimento_repository.py
│   │   │   ├── financeiro_repository.py
│   │   │   └── caixa_repository.py
│   │   │
│   │   ├── value_objects/
│   │   │   ├── __init__.py
│   │   │   └── comum.py          # CPF, CNPJ, Moeda, etc
│   │   │
│   │   ├── exceptions.py         # Domain exceptions
│   │   └── specifications.py     # Query specifications
│   │
│   ├── application/
│   │   ├── __init__.py
│   │   ├── dto/
│   │   │   ├── __init__.py
│   │   │   ├── cliente_dto.py
│   │   │   ├── abastecimento_dto.py
│   │   │   └── comum_dto.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── cliente_service.py
│   │   │   ├── abastecimento_service.py
│   │   │   └── sync_service.py   # Sincronização com webPosto
│   │   │
│   │   ├── event_handlers/
│   │   │   ├── __init__.py
│   │   │   ├── cliente_event_handler.py
│   │   │   └── event_dispatcher.py
│   │   │
│   │   └── exceptions.py         # Application exceptions
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── webposto/
│   │   │   ├── __init__.py
│   │   │   ├── client.py         # Cliente HTTP webPosto (adapter)
│   │   │   ├── schemas.py        # Request/response schemas
│   │   │   └── mappers.py        # Domain ↔ webPosto mapping
│   │   │
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── sqlalchemy_base.py
│   │   │   ├── cliente_repository.py    # Implementação (adapter)
│   │   │   ├── abastecimento_repository.py
│   │   │   └── models.py         # SQLAlchemy models
│   │   │
│   │   ├── event_bus/
│   │   │   ├── __init__.py
│   │   │   ├── redis_event_bus.py   # Redis Pub/Sub (adapter)
│   │   │   └── event_serializer.py
│   │   │
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   ├── settings.py       # Pydantic settings (env vars)
│   │   │   ├── database.py       # Database config
│   │   │   └── logging.py        # Logging config (JSON)
│   │   │
│   │   ├── migrations/           # Alembic
│   │   │   └── versions/
│   │   │
│   │   └── exceptions.py         # Infrastructure exceptions
│   │
│   ├── interfaces/
│   │   ├── __init__.py
│   │   ├── http/
│   │   │   ├── __init__.py
│   │   │   ├── app.py            # FastAPI app factory
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── clientes.py
│   │   │   │   ├── abastecimentos.py
│   │   │   │   ├── financeiro.py
│   │   │   │   ├── caixa.py
│   │   │   │   └── health.py     # Health check
│   │   │   ├── middleware/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── error_handler.py
│   │   │   │   └── logging.py
│   │   │   └── dependencies.py   # FastAPI dependencies
│   │   │
│   │   ├── cli/
│   │   │   ├── __init__.py
│   │   │   └── commands.py       # Click commands
│   │   │
│   │   └── exceptions.py         # Interface exceptions
│   │
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── domain_event.py       # Domain event base
│   │   ├── repository.py         # Repository base interface
│   │   ├── logger.py             # Logger estruturado
│   │   └── utils.py              # Utilities
│   │
│   └── main.py                   # Entry point
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Fixtures globais
│   ├── factories.py              # Factory Boy factories
│   │
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── test_cliente.py
│   │   │   └── test_abastecimento.py
│   │   ├── application/
│   │   │   ├── __init__.py
│   │   │   ├── test_cliente_service.py
│   │   │   └── test_sync_service.py
│   │   └── infrastructure/
│   │       ├── __init__.py
│   │       └── test_webposto_client.py
│   │
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_cliente_flow.py
│   │   ├── test_webposto_integration.py
│   │   └── test_event_bus.py
│   │
│   ├── e2e/
│   │   ├── __init__.py
│   │   ├── test_api_clientes.py
│   │   ├── test_api_abastecimentos.py
│   │   └── test_sync_workflow.py
│   │
│   └── mocks/
│       ├── __init__.py
│       └── webposto_responses.py
│
├── docker-compose.yml
├── Dockerfile
├── .dockerignore
├── .env.example
├── .gitignore
├── pyproject.toml               # Poetry ou pip
├── poetry.lock / requirements.txt
├── Makefile
├── pytest.ini
├── .github/
│   └── workflows/
│       ├── test.yml
│       └── lint.yml
├── README.md
└── ARCHITECTURE.md

```

### 5. Arquivos Críticos a Criar

#### src/domain/entities/cliente.py
- Entity Cliente com validações
- Methods: adicionar, atualizar, ativar, desativar
- Events: ClienteAdicionado, ClienteAtualizado

#### src/domain/repositories/cliente_repository.py
- Interface (port): métodos que o repositório deve ter
- Sem implementação PostgreSQL aqui (apenas assinatura)

#### src/infrastructure/webposto/client.py
- Cliente HTTP autenticado (HTTPX)
- Métodos: get_clientes(), get_abastecimentos(), etc
- Retry automático, timeout, error handling

#### src/infrastructure/repositories/cliente_repository.py
- Implementação (adapter) com SQLAlchemy
- CRUD: create, read, update, delete

#### src/application/services/cliente_service.py
- Use cases: sync_clientes(), obter_cliente(), etc
- Orquestra domain + event bus

#### src/infrastructure/event_bus/redis_event_bus.py
- Pub/Sub em Redis
- Publica domain events para outros serviços

#### src/interfaces/http/app.py
- FastAPI app factory
- Routes, middleware, error handlers, CORS

#### tests/
- 100% coverage mínimo
- Unit tests (domain, services)
- Integration tests (repositories, webposto client)
- E2E tests (API endpoints)
- Mocks com responses library

### 6. Configuração de Variáveis de Ambiente

```
# .env.example
# Ambiente
ENVIRONMENT=development
DEBUG=true

# webPosto API
WEBPOSTO_BASE_URL=http://web.qualityautomacao.com.br
WEBPOSTO_API_KEY=<será preenchido quando tiverem a chave>
WEBPOSTO_SYNC_INTERVAL_SECONDS=3600

# Banco de Dados
DATABASE_URL=postgresql://user:password@localhost:5432/webposto
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60

# Circuit Breaker
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60
```

### 7. Docker & docker-compose.yml

- PostgreSQL + Redis
- Volume para dados persistentes
- Network compartilhada
- Health checks

### 8. GitHub Actions CI/CD

- Lint (black, isort, flake8)
- Tests (pytest com coverage)
- Type checking (mypy)
- Security scan (bandit)
- Build Docker image

### 9. Documentação

- README com: instalação, setup, como rodar, como testar
- ARCHITECTURE.md explicando decisões e fluxos
- Docstrings em todas as classes/métodos
- Swagger automático no /docs

### 10. Entregáveis Finais

1. ✅ Projeto Python estruturado, pronto pra producção
2. ✅ Todos os 8 módulos (Clientes, Produtos, Abastecimentos, Financeiro, Caixa, Cartões, Relatórios, Movimentos)
3. ✅ Sincronização com webPosto (quando tiverem a chave REST)
4. ✅ Event system para outros serviços consumirem
5. ✅ API interna (FastAPI) expondo dados
6. ✅ Testes com 100% coverage
7. ✅ Docker pronto pra deploy
8. ✅ Documentação completa

### 11. Priorização

**Fase 1 (MVP):** Clientes + Abastecimentos (mais simples)
**Fase 2:** Financeiro + Caixa (mais complexo)
**Fase 3:** Produtos + Relatórios + Cartões

Comece tudo agora, mas foque na estrutura que permite escalar depois.

---

**Você tem alguma dúvida? Pode pedir esclarecimentos antes de começar.**

