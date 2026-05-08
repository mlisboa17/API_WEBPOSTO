# webposto-service — Arquitetura Técnica

## 🏛️ Padrão de Arquitetura

**Hexagonal Architecture (Ports & Adapters)** + **Event-Driven**

Separa a lógica de negócio (Domain) das implementações técnicas (Infrastructure), permitindo:

- ✅ Fácil teste (mocks dos adapters)
- ✅ Baixo acoplamento (interfaces/ports)
- ✅ Escalabilidade (novos adapters sem afetar domínio)
- ✅ Reutilização (múltiplos consumidores de eventos)

## 📦 Camadas

### 1. **Domain Layer** (`src/domain/`)

**Responsabilidade:** Lógica de negócio pura

**Componentes:**

- **Entities** (`entities/`): Objetos com identidade e lógica de negócio
  - `Cliente`, `Abastecimento`, `Financeiro`, `Caixa`
  - Validações de domínio (CNPJ válido, valor > 0, etc)
  - Gerenciamento de eventos

- **Events** (`events/`): Domain events imutáveis
  - `ClienteAdicionado`, `ClienteAtualizado`, `AbastecimentoRegistrado`, etc
  - Publicados quando regras de negócio são satisfeitas

- **Repositories (Interfaces/Ports)** (`repositories/`): Contratos de persistência
  - `ClienteRepository`, `AbastecimentoRepository`, etc
  - Apenas assinaturas, sem implementação

**Exemplo:**

```python
# Entidade com regra de negócio
cliente = Cliente(id="123", nome="Acme Corp", cnpj="12345678901234")

# Validação de domínio acontece aqui
if len(cliente.cnpj) < 10:
    raise ValueError("CNPJ inválido")

# Evento disparado
evento = ClienteAdicionado(nome=cliente.nome, cnpj=cliente.cnpj)
cliente.adicionar_evento(evento)
```

### 2. **Application Layer** (`src/application/`)

**Responsabilidade:** Orquestração de casos de uso

**Componentes:**

- **DTOs** (`dto/`): Data Transfer Objects para API
  - `ClienteCreateDTO`, `ClienteUpdateDTO`, `ClienteResponseDTO`
  - Validações de entrada (Pydantic v2)

- **Services** (`services/`): Use cases da aplicação
  - `ClienteService`: CRUD de clientes + publicação de eventos
  - `SyncService`: Sincronização com webPosto API

**Exemplo:**

```python
# Use case: Criar cliente
class ClienteService:
    async def criar_cliente(self, dto: ClienteCreateDTO):
        # 1. Valida DTO (Pydantic)
        # 2. Cria entidade de domínio
        # 3. Salva no repositório
        # 4. Publica evento no event bus
        # 5. Retorna DTO de resposta
```

### 3. **Infrastructure Layer** (`src/infrastructure/`)

**Responsabilidade:** Implementação técnica de interfaces de domínio

**Componentes:**

- **Config** (`config/`): Configuração centralizada
  - `settings.py`: Pydantic BaseSettings (variáveis de ambiente)
  - `database.py`: SQLAlchemy async engine

- **WebPosto Client** (`webposto/`): Adapter para API REST do webPosto
  - `client.py`: Cliente HTTPX com retry automático
  - Métodos GET/POST/PUT para os 8 módulos

- **Repositories** (`repositories/`): Implementação de persistência
  - `models.py`: ORM models SQLAlchemy
  - `cliente_repository.py`: Implementação de `ClienteRepository`
  - Conversão Entity ↔ ORM Model

- **Event Bus** (`event_bus/`): Adapter para Redis Pub/Sub
  - `redis_event_bus.py`: Publicação e consumo de eventos
  - Serialização/desserialização JSON

**Exemplo:**

```python
# Infrastructure: Implementação concreta de repositório
class SQLAlchemyClienteRepository(ClienteRepository):
    async def save(self, entity: Cliente) -> Cliente:
        # Converte entity para model ORM
        model = ClienteModel(id=entity.id, nome=entity.nome, ...)
        # Salva no banco
        await self.session.flush()
        return entity
```

### 4. **Interfaces Layer** (`src/interfaces/`)

**Responsabilidade:** Apresentação (HTTP)

**Componentes:**

- **HTTP Routes** (`http/routes/`): Endpoints FastAPI
  - `clientes.py`: CRUD de clientes
  - `sync.py`: Endpoints de sincronização
  - `health.py`: Health checks

- **Dependencies** (`http/dependencies.py`): Injeção de dependência FastAPI
  - Cria instâncias de services, repositórios, clients
  - Gerencia ciclo de vida

- **App Factory** (`http/app.py`): Factory FastAPI
  - Cria aplicação com middleware, rotas, eventos startup/shutdown

**Exemplo:**

```python
# HTTP: Rota que orquestra service
@router.post("/clientes", response_model=ClienteResponseDTO)
async def criar_cliente(
    dto: ClienteCreateDTO,
    service: ClienteService = Depends(get_cliente_service)
):
    return await service.criar_cliente(dto)
```

### 5. **Shared Layer** (`src/shared/`)

**Responsabilidade:** Código comum reutilizável

- `domain_event.py`: Base class para eventos
- `repository.py`: Interface genérica para repositórios
- `logger.py`: Setup logging estruturado

---

## 🔄 Fluxo de Dados

### Criação de Cliente

```
1. HTTP POST /clientes
   ↓
2. FastAPI valida DTO com Pydantic
   ↓
3. Route chama ClienteService.criar_cliente()
   ↓
4. Service cria entity Cliente (validação de domínio)
   ↓
5. Service chama Repository.save()
   ↓
6. Repository converte Entity → ORM Model → PostgreSQL
   ↓
7. Service publica evento ClienteAdicionado no Redis
   ↓
8. Outros serviços recebem evento via subscription
   ↓
9. Response: ClienteResponseDTO (JSON)
```

### Sincronização com webPosto

```
1. HTTP POST /sync/clientes
   ↓
2. Route chama SyncService.sync_clientes()
   ↓
3. Service chama WebPostoClient.get_clientes()
   ↓
4. Client faz GET para webPosto API com retry automático
   ↓
5. Service: para cada cliente recebido:
   - Verifica se já existe (by CNPJ)
   - Se existe: atualiza via Repository
   - Se novo: cria via ClienteService (gera eventos)
   ↓
6. Retorna estatísticas (criados, atualizados, erros)
```

---

## 🗄️ Banco de Dados

**Type:** PostgreSQL 15
**ORM:** SQLAlchemy 2.0 (async)
**Migrations:** Alembic

### Tabelas

```sql
-- Clientes sincronizados da API webPosto
CREATE TABLE clientes (
    id VARCHAR(36) PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    cnpj VARCHAR(20) NOT NULL UNIQUE,
    ativo BOOLEAN DEFAULT TRUE,
    webposto_id VARCHAR(255) UNIQUE,
    created_at DATETIME,
    updated_at DATETIME
);

-- Abastecimentos registrados
CREATE TABLE abastecimentos (
    id VARCHAR(36) PRIMARY KEY,
    cliente_id VARCHAR(36) NOT NULL,
    data DATETIME NOT NULL,
    valor FLOAT NOT NULL,
    litros FLOAT NOT NULL,
    produto_id VARCHAR(36),
    webposto_id VARCHAR(255) UNIQUE,
    created_at DATETIME,
    updated_at DATETIME
);

-- Lançamentos financeiros
CREATE TABLE financeiro (
    id VARCHAR(36) PRIMARY KEY,
    tipo VARCHAR(20) NOT NULL,  -- RECEBER, PAGAR, TRANSFERENCIA
    valor FLOAT NOT NULL,
    data_vencimento DATETIME NOT NULL,
    descricao VARCHAR(255) NOT NULL,
    pago BOOLEAN DEFAULT FALSE,
    data_pagamento DATETIME,
    webposto_id VARCHAR(255) UNIQUE,
    created_at DATETIME,
    updated_at DATETIME
);

-- Movimentos de caixa
CREATE TABLE caixa (
    id VARCHAR(36) PRIMARY KEY,
    descricao VARCHAR(255) NOT NULL,
    saldo FLOAT DEFAULT 0,
    data_movimento DATETIME NOT NULL,
    referencia VARCHAR(255) UNIQUE,
    webposto_id VARCHAR(255) UNIQUE,
    created_at DATETIME,
    updated_at DATETIME
);
```

---

## 🔔 Event-Driven Architecture

### Fluxo de Eventos

```
Domain Entity dispara evento
    ↓
Service publica no Event Bus
    ↓
Redis Pub/Sub: channel "events:{NomeEvento}"
    ↓
Outros serviços se inscrevem via RedisEventBus.subscribe()
    ↓
Handler executado quando evento chega
```

### Exemplo: Consumidor Externo

```python
# Serviço externo se inscreve a eventos
async def handle_cliente_adicionado(data):
    print(f"Novo cliente: {data['nome']}")
    # Atualizar cache, notificar, etc

event_bus = RedisEventBus()
await event_bus.subscribe("ClienteAdicionado", handle_cliente_adicionado)
await event_bus.listen()  # Loop infinito ouvindo eventos
```

### Eventos Disponíveis

```
Domain Entities → Events

Cliente → ClienteAdicionado
       → ClienteAtualizado
       → ClienteAtivado
       → ClienteDesativado
       → ClienteDeletado

Abastecimento → AbastecimentoRegistrado
             → AbastecimentoAtualizado
             → AbastecimentoDeletado

Financeiro → LancamentoFinanceiroRegistrado
          → LancamentoFinanceiroPago
          → LancamentoFinanceiroAtualizado
```

---

## 🧪 Testes

### Estrutura

```
tests/
├── unit/              # Testes de classes isoladas
│   ├── domain/        # Testes de entities/events
│   ├── application/   # Testes de services
│   └── infrastructure/# Testes de clients/repositories
├── integration/       # Testes de múltiplas camadas
├── e2e/              # Testes de API completa
└── mocks/            # Fixtures e mocks
```

### Cobertura

- **Target:** 100% de cobertura
- **Unitários:** Entities, value objects, lógica de domínio
- **Integração:** Services com repositórios mockados
- **E2E:** API endpoints com fixtures de banco

### Exemplo: Teste Unitário

```python
# test_cliente.py
def test_criar_cliente_valido():
    cliente = Cliente(id="1", nome="Acme", cnpj="12345678901234")
    assert cliente.ativo is True
    assert cliente.nome == "Acme"

def test_cliente_nome_vazio_falha():
    with pytest.raises(ValueError):
        Cliente(id="1", nome="   ", cnpj="12345678901234")
```

### Exemplo: Teste de Service

```python
# test_cliente_service.py
@pytest.mark.asyncio
async def test_criar_cliente(mocked_repository, mocked_event_bus):
    service = ClienteService(mocked_repository, mocked_event_bus)
    dto = ClienteCreateDTO(nome="Teste", cnpj="12345678901234")

    result = await service.criar_cliente(dto)

    assert result.nome == "Teste"
    assert mocked_repository.save.called
    assert mocked_event_bus.publish.called
```

---

## 🚀 Dependências Principais

### Production

| Biblioteca | Versão | Uso |
|-----------|--------|-----|
| FastAPI | ^0.104.0 | Web framework async |
| SQLAlchemy | ^2.0.23 | ORM async |
| Pydantic | ^2.4.0 | Validação de dados |
| HTTPX | ^0.25.0 | Cliente HTTP async |
| Redis | ^5.0.0 | Pub/Sub e cache |
| Tenacity | ^8.2.3 | Retry logic |
| Structlog | ^23.2.0 | Logging estruturado |

### Development

| Biblioteca | Uso |
|-----------|-----|
| pytest | Testes |
| pytest-asyncio | Testes async |
| pytest-cov | Cobertura |
| black | Formatação |
| isort | Ordem de imports |
| flake8 | Linting |
| mypy | Type checking |
| bandit | Security scanning |

---

## 🔐 Segurança

- ✅ **Validação**: Pydantic v2 em todas DTOs
- ✅ **Retry**: HTTPX com tenacity (exponential backoff)
- ✅ **Timeout**: 30s padrão em todas requisições HTTP
- ✅ **Rate Limiting**: Configurável via env (100 req/min)
- ✅ **CORS**: Habilitado (customizável)
- ✅ **Logging**: Nenhum secret (API key) é loggado

---

## 🔄 CI/CD Workflows

### GitHub Actions

- **test.yml**: Testa em Python 3.11, integrando PostgreSQL e Redis
- **lint.yml**: Black, isort, flake8, mypy, bandit

---

## 📊 Métricas & Observabilidade

### Logging Estruturado (JSON)

```json
{
  "timestamp": "2024-04-08T10:30:45Z",
  "level": "INFO",
  "logger": "src.application.services.cliente_service",
  "message": "Cliente criado",
  "cliente_id": "550e8400-e29b-41d4-a716-446655440000",
  "event": "ClienteAdicionado"
}
```

### Health Endpoints

```
GET /health  → {"status": "healthy"}
GET /ready   → {"ready": true}
```

---

## 🚢 Deployment

### Local (Desenvolvimento)

```bash
docker-compose up
# Acesso: http://localhost:8000
```

### Production (Roadmap)

- [ ] Kubernetes manifests
- [ ] Helm charts
- [ ] CI/CD automático para DockerHub/ECR
- [ ] Prometheus metrics
- [ ] Jaeger tracing
- [ ] ArgoCD integration

---

## 📚 Decisões de Design

### Por que Hexagonal Architecture?

✅ Lógica de negócio isolada de implementação técnica
✅ Fácil mock para testes
✅ Múltiplos adapters (DB, cache, APIs) sem afetar domínio
✅ Escalável (novos eventos, novos consumers)

### Por que Event-Driven?

✅ Desacoplamento: serviços não precisam se conhecer
✅ Escalabilidade: novos consumidores sem afetar publisher
✅ Rastreabilidade: audit log natural dos eventos
✅ Resiliência: se consumer falhar, evento fica na fila Redis

### Por que PostgreSQL?

✅ ACID guarantees
✅ Full-text search, JSON columns, arrays
✅ Async support via asyncpg
✅ Production-ready

### Por que Redis?

✅ Pub/Sub para eventos
✅ Cache para dados frequentes
✅ TTL automático
✅ Throughput alto

---

## 🎯 Próximos Passos

1. **Fase 1 (MVP):** GET endpoints + sincronização leitura
2. **Fase 2:** POST/PUT endpoints (escrita)
3. **Fase 3:** Múltiplos consumers de eventos
4. **Fase 4:** Observabilidade (Prometheus, Jaeger)
5. **Fase 5:** Kubernetes + scaling automático

---

**Versão:** 0.1.0
**Última Atualização:** 2024-04-08
**Mantido por:** Grupo Lisboa
