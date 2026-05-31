# Logos WebPosto Gateway API (Porta 8050)
## API Gateway Unificada para Integração com WebPosto

**Status**: 🚀 Pronto para Desenvolvimento Paralelo

---

## 📋 Visão Geral

Esta é a arquitetura modular DDD (Domain-Driven Design) para o **Logos Gateway API**, que funciona como um **API Gateway centralizado** na porta 8050 para integrar o sistema Logos com o WebPosto.

### 🎯 Objetivo Principal
- **Centralizar** todas as chamadas ao WebPosto em um único ponto (porta 8050)
- **Cachear** respostas para evitar overload na API legada
- **Rotear dinamicamente** requisições baseado em `X-Posto-ID`
- **Validar e parsear** dados de forma limpa e segura

---

## 📂 Estrutura do Projeto

```
logos-webposto-gateway/
├── src/
│   ├── main.py                      ✅ Core FastAPI (porta 8050)
│   ├── domain/
│   │   ├── entities.py              🔄 CLAUDE: Entidades (CashExpense, PostoCredentials)
│   │   └── exceptions.py            🔄 CLAUDE: Exceções customizadas
│   ├── application/
│   │   └── fetch_expenses.py        🔄 CLAUDE: UseCase (orquestração)
│   ├── infrastructure/
│   │   ├── database.py              ✅ SQLite assíncrono (aiosqlite)
│   │   ├── repository.py            🔄 CLAUDE: Busca credenciais no DB
│   │   ├── webposto_client.py       🔄 GROK: Cliente HTTPX assíncrono
│   │   └── cache.py                 🔄 GROK: Cache local com TTL
│   └── presentation/
│       └── routes.py                ✅ Endpoints (/ready, /health, /v1/expenses)
├── tests/                           🔄 GROK: Suite de testes
├── Dockerfile                       ✅ Multi-stage Python 3.12-slim
├── docker-compose.yml               ✅ Valkey + Gateway (porta 8050)
├── requirements.txt                 ✅ Dependências (FastAPI, SQLModel, HTTPX)
├── .env.example                     ✅ Variáveis de ambiente
└── README.md                        📖 Este arquivo
```

---

## 🔌 Kit de Consumo para Outros Sistemas

O projeto inclui um pacote pronto para integradores consumirem a API sem depender de implementação interna do gateway.

- Guia de integração: `docs/API_CONSUMO.md`
- Guia de CRUD catalogo/financeiro: `docs/CRUD_CATALOGO_FINANCEIRO.md`
- Cliente Python pronto: `consumer-kit/python/gateway_client.py`
- Exemplo executável: `consumer-kit/python/example_consumer.py`
- Requisições HTTP prontas: `consumer-kit/http/gateway_requests.http`
- Contrato de resposta (JSON Schema): `consumer-kit/contracts/expenses.response.schema.json`

---

## 🔄 Divisão de Tarefas (3 IAs em Paralelo)

### 🟢 GEMINI 2.0 TASK (Infraestrutura & DevOps)
**Status**: ✅ COMPLETO  
**Arquivos**: `src/main.py` | `src/infrastructure/database.py` | `src/presentation/routes.py`

**Entregáveis**:
- [x] FastAPI configurado na porta 8050
- [x] SQLite assíncrono (aiosqlite) inicializado
- [x] Endpoints `/ready` (HTTP 200 direto) e `/health` (SELECT 1 no DB)
- [x] Dockerfile Multi-stage otimizado
- [x] docker-compose.yml com Valkey e healthchecks

---

### 🟡 CLAUDE 3.7 TASK (Domínio & Lógica de Negócio)
**Status**: 🔄 EM ANDAMENTO  
**Arquivos**: `src/domain/entities.py` | `src/domain/exceptions.py` | `src/application/fetch_expenses.py`

**Responsabilidades**:
1. **Entidades do Domínio** (`entities.py`):
   - Implementar `CashExpense` com Pydantic v2 (id, posto_id, valor, descricao, timestamp)
   - Implementar `PostoCredentials` (id, posto_id, api_key, api_secret, status)
   - Garantir imutabilidade (`frozen=True`)

2. **Exceções Customizadas** (`exceptions.py`):
   - `PostoNaoConfiguradoException`: Quando ID do posto não está no banco local
   - `WebPostoIntegracaoException`: Erros de integração HTTP
   - `DadosInvalidosException`: Falhas de validação

3. **Use Case** (`fetch_expenses.py`):
   - Classe `FetchExpensesUseCase` com método `execute()`
   - Buscar credenciais do repositório
   - Disparar exceções apropriadas
   - Retornar lista de `CashExpense`

**Checklist CLAUDE**:
- [ ] Entidades imutáveis com `frozen=True`
- [ ] Exceções mapeadas para HTTP status corretos
- [ ] UseCase com injeção de dependência via FastAPI `Depends`
- [ ] Testes unitários para o domínio

---

### 🔵 GROK 4 TASK (Infraestrutura & Performance)
**Status**: 🔄 EM ANDAMENTO  
**Arquivos**: `src/infrastructure/webposto_client.py` | `src/infrastructure/cache.py` | `tests/`

**Responsabilidades**:
1. **Cliente HTTP** (`webposto_client.py`):
   - Classe `WebPostoClient` com `httpx.AsyncClient`
   - Injetar credenciais dinamicamente nos headers
   - Timeout rígido de 10 segundos máximo
   - Parsing robusto de resposta JSON → `CashExpense`
   - Circuit breaker simples (retry com backoff)

2. **Cache Local** (`cache.py`):
   - Classe `CacheManager` com TTL de 5 minutos
   - Índex por `posto_id` + `data_consulta`
   - Método `get()`, `set()`, `cleanup_expired()`
   - Uso mínimo de memória

3. **Suite de Testes** (`tests/`):
   - Testes assíncronos com `pytest-asyncio`
   - Mock do cliente WebPosto
   - Validação de cache

**Checklist GROK**:
- [ ] HTTPX com timeouts configurados
- [ ] Parser robusto para JSON do WebPosto
- [ ] Cache com expiração automática
- [ ] Circuit breaker evitando cascata de falhas
- [ ] Tests cobrindo 80%+ do código

---

## 🚀 Como Começar (Setup Local)

### 1️⃣ Clonar e Entrar no Diretório
```bash
cd logos-webposto-gateway
```

### 2️⃣ Criar Ambiente Virtual
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

### 3️⃣ Instalar Dependências
```bash
pip install -r requirements.txt
```

### 4️⃣ Copiar .env
```bash
cp .env.example .env
```

### 5️⃣ Iniciar com Docker Compose (Recomendado)
```bash
docker compose up -d
```

Validar:
```bash
curl http://localhost:8050/ready   # HTTP 200
curl http://localhost:8050/health  # HTTP 200 + DB status
curl http://localhost:8050/v1/     # Info da API
```

---

## ✅ Checklist de Validação

```
FASE 1: Infraestrutura (GEMINI) ✅
[ ] FastAPI rodando na porta 8050
[ ] Database inicializa sem erros
[ ] Endpoints /ready e /health respondendo
[ ] Docker build funciona sem erros

FASE 2: Domínio (CLAUDE) 🔄
[ ] Entidades têm frozen=True
[ ] Exceções mapeadas corretamente
[ ] UseCase orquestra corretamente
[ ] Testes unitários passam

FASE 3: Performance (GROK) 🔄
[ ] Cliente HTTP com timeout configurado
[ ] Cache funciona com TTL
[ ] Tests cobrem componentes críticos
[ ] Circuit breaker dispara em erro

FASE 4: Integração 🔄
[ ] E2E tests passam
[ ] Docker compose com healthchecks verdes
[ ] Logs estruturados e legíveis
[ ] Pronto para staging
```

---

## 📊 Fluxo de Requisição

```
Cliente (Logos Módulo)
    │
    ├─ X-Posto-ID: "23"
    └─> GET /v1/expenses
            │
            ▼
    [Router FastAPI na porta 8050]
            │
    ┌───────┴───────┐
    │ Cache Hit?    │
    └───────┬───────┘
           NO
            │
            ▼
    [Repository busca credenciais]
            │
    ┌───────┴───────────────┐
    │ Credenciais ativas?   │
    └───────┬───────────────┘
           SIM
            │
            ▼
    [WebPostoClient]
    └─> HTTPX GET (timeout 10s)
            │
            ▼
    [Parser JSON → CashExpense]
            │
            ▼
    [Cache.set() com TTL 5min]
            │
            ▼
    [Retornar 200 + JSON]
```

---

## 🔐 Variáveis de Ambiente

Ver [.env.example](.env.example) para configurações completas.

**Essenciais**:
- `DATABASE_URL`: SQLite local (padrão: `sqlite+aiosqlite:///./logos_gateway.db`)
- `API_PORT`: Porta de escuta (padrão: `8050`)
- `WEBPOSTO_API_TIMEOUT`: Timeout HTTP (padrão: `10s`)
- `CACHE_TTL_MINUTES`: TTL do cache (padrão: `5`)

---

## 📚 Referências

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [HTTPX Async Client](https://www.python-httpx.org/)
- [Pydantic v2](https://docs.pydantic.dev/latest/)

---

## 🎯 Próximos Passos (Após Desenvolvimento Paralelo)

1. ✅ **Fase 1**: Validar todos os endpoints localmente
2. ✅ **Fase 2**: Testes E2E com dados reais do WebPosto
3. ✅ **Fase 3**: Deploy em staging com Kubernetes
4. ✅ **Fase 4**: Monitoramento e observabilidade (Prometheus/Grafana)
5. ✅ **Fase 5**: Produção com load balancer

---

**Autor**: Logos Engineering Team  
**Data**: 2026-05-17  
**Versão**: 1.0.0-alpha

