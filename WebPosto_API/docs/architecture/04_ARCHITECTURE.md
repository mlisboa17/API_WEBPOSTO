# Architecture
## Arquitetura do Sistema - LOGOS SPACE

**Versão:** 1.0  
**Data:** 2026-06-28  
**Status:** Ativo  
**Pattern:** Snapshot First Architecture

---

## 🎯 Visão Geral

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENTE (Navegador)                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/JSON
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND LAYER                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Vanilla JavaScript SPA (frontend/)                      │    │
│  │  • index.html (entrypoint)                               │    │
│  │  • app.js (aplicação principal)                          │    │
│  │  • pages/ (50+ páginas)                                  │    │
│  │  • components/ (15+ componentes)                          │    │
│  │  • services/ (API clients)                               │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Fetch API
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                     API LAYER (FastAPI)                          │
│  Porta: 8040                                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Rotas (src/interfaces/http/routes/)                      │    │
│  │  • /v1/* (Enterprise endpoints)                           │    │
│  │  • /api/v1/* (Analytics endpoints)                        │    │
│  │  • /app/* (Frontend static)                              │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                     SERVICE LAYER                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Business Services (src/services/)                        │    │
│  │  • corporate_finance_center_service.py                    │    │
│  │  • corporate_cash_flow_service.py                         │    │
│  │  • financial_intelligence_service.py                      │    │
│  │  • network_financial_overview_service.py                   │    │
│  │  • supplier_intelligence_service.py                        │    │
│  │  • fuel_executive_service.py                              │    │
│  │  • sales_service.py                                       │    │
│  │  • [50+ serviços]                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓ (opcional)
┌─────────────────────────────────────────────────────────────────┐
│                     SNAPSHOT LAYER (Cache)                       │
│  TTL: 300 segundos (5 minutos)                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Snapshot Services                                        │    │
│  │  • finance_center_snapshot_service.py                     │    │
│  │  • finance_intelligence_snapshot_service.py               │    │
│  │  • cash_flow_snapshot_service.py                          │    │
│  │  Performance: 13.5ms (HIT) vs 2-5s (MISS)                 │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                     GATEWAY LAYER                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  WebPosto Integration                                     │    │
│  │  • webposto_client.py                                      │    │
│  │  • Circuit Breaker (failure_threshold=3, block_seconds=3600)│   │
│  │  • DateRangeResolver (auto-datas)                       │    │
│  │  • Endpoint Contracts (49 endpoints)                      │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS/JSON
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                     EXTERNAL APIs                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │  WebPosto API   │  │   Supabase      │  │   Outras        │   │
│  │  (Quality Auth) │  │   (PostgreSQL)  │  │   APIs          │   │
│  │  49 endpoints   │  │   logos_dw      │  │                 │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Componentes Principais

### 1. Frontend Layer

**Tecnologia:** Vanilla JavaScript ES6+  
**Framework:** Nenhum (SPA puro)  
**Pasta:** `frontend/`

**Estrutura:**
```
frontend/
├── index.html              # Entrypoint HTML
├── app.js                  # Aplicação principal
├── styles.css              # Estilos globais
├── pages/                  # 50+ páginas
│   ├── executiveDashboard.js
│   ├── fuelExecutiveDashboard.js
│   ├── sales.js
│   ├── dashboard.js
│   ├── security.html       # Sprint 25A
│   └── governance.html     # Sprint 25A
├── components/             # 15+ componentes
│   ├── navigationShell.js
│   ├── filters.js
│   └── table.js
└── services/               # API clients
    └── api.js
```

**Princípios:**
- ✅ Zero frameworks (React/Vue/Angular proibidos)
- ✅ Fetch API nativo
- ✅ NUNCA acessa Supabase diretamente
- ✅ Sempre via FastAPI endpoints

---

### 2. API Layer (FastAPI)

**Tecnologia:** FastAPI (Python 3.9+)  
**Porta:** 8040  
**Pasta:** `src/interfaces/http/`

**Estrutura:**
```
src/interfaces/http/
├── app.py                  # FastAPI app factory
├── routes/                 # 50+ rotas
│   ├── health.py
│   ├── fechamento_enterprise.py
│   ├── business_analyst.py    # Sprint IA-05
│   ├── governance.py          # Sprint 25A
│   └── [47+ rotas]
└── middleware/
    └── auth.py
```

**Convenções:**
- `/v1/*` - Endpoints Enterprise
- `/api/v1/*` - Endpoints Analytics
- `/app/*` - Static files (Frontend)

---

### 3. Service Layer

**Pasta:** `src/services/`

**Serviços Principais:**

| Serviço | Arquivo | Propósito |
|---------|---------|-----------|
| Finance Center | `corporate_finance_center_service.py` | Gestão financeira |
| Cash Flow | `corporate_cash_flow_service.py` | Fluxo de caixa |
| Intelligence | `financial_intelligence_service.py` | Inteligência financeira |
| Overview | `network_financial_overview_service.py` | Visão rede |
| Supplier | `supplier_intelligence_service.py` | Inteligência fornecedores |
| Fuel | `fuel_executive_service.py` | Combustíveis |
| Sales | `sales_service.py` | Vendas |
| Stock | `stock_service.py` | Estoque |
| Governance | `governance/` | Governança (Sprint 25A) |

**Total:** 50+ serviços

---

### 4. Snapshot Layer (Cache)

**Pattern:** Snapshot First Architecture  
**TTL:** 300 segundos (5 minutos)  
**Performance:**
- Cache HIT: **13.5 ms**
- Cache MISS: **2-5 segundos**

**Implementação:**
```python
# finance_center_snapshot_service.py
class SnapshotStore:
    TTL = 300  # segundos
    
    async def get(self, key):
        if self.cache.has(key) and not self.cache.expired(key):
            return self.cache.get(key)  # 13.5ms
        else:
            data = await self.fetch_from_webposto()  # 2-5s
            self.cache.set(key, data, ttl=self.TTL)
            return data
```

**Serviços:**
- `finance_center_snapshot_service.py`
- `finance_intelligence_snapshot_service.py`
- `cash_flow_snapshot_service.py`

---

### 5. Gateway Layer

**Pasta:** `src/gateway/`

#### WebPosto Client
**Arquivo:** `webposto_client.py`

**Responsabilidades:**
- ✅ Autenticação com API WebPosto
- ✅ Circuit Breaker (3 falhas = abre, 1h = fecha)
- ✅ Retry com backoff exponencial
- ✅ Timeout management (30s padrão, 60s lentos)
- ✅ DateRangeResolver (auto-injeção de datas)
- ✅ Endpoint Contracts (49 endpoints mapeados)

#### Circuit Breaker
```python
class SimpleCircuitBreaker:
    failure_threshold = 3      # Abre após 3 falhas
    block_seconds = 3600      # Fecha após 1 hora
```

**Estados:**
- `CLOSED` - Normal
- `OPEN` - Bloqueado (rejeita requisições)
- `HALF_OPEN` - Testando (1 requisição)

#### DateRangeResolver
```python
# Garantir datas em todos os endpoints
params = DateRangeResolver.ensure_date_params(
    params,
    default_preset="last_7_days"
)
# Resultado: {"dataInicial": "2026-06-21", "dataFinal": "2026-06-28"}
```

---

### 6. Data Layer

#### WebPosto API
- **URL:** https://api.webposto.com.br
- **Auth:** Quality Automação (Token)
- **Endpoints:** 49 mapeados

#### Supabase
- **Schema:** `logos_dw`
- **Tabelas:** 6 (dim + fact)
- **RLS:** Ativo (Row Level Security)
- **Multi-tenant:** Por `tenant_id`

**Tabelas:**
```sql
logos_dw.dim_cliente
logos_dw.dim_empresa
logos_dw.dim_produto
logos_dw.fact_receber
logos_dw.fact_venda
logos_dw.fact_venda_item
```

#### Governance Schema (Novo - Sprint 25A)
```sql
governance.audit_log
governance.approval_requests
governance.security_events
governance.copilot_audit
governance.user_roles
```

---

## 🔄 Fluxo de Dados

### 1. Requisição Normal (Cache HIT)
```
Cliente → Frontend → FastAPI → Snapshot → Resposta (13.5ms)
```

### 2. Requisição com Cache MISS
```
Cliente → Frontend → FastAPI → Snapshot (miss)
                                    ↓
                              Service → WebPosto Client
                                            ↓
                                    WebPosto API (Quality Auth)
                                            ↓
                              Service → Snapshot (store)
                                    ↓
                              Resposta (2-5s)
```

### 3. Requisição com Circuit Breaker Aberto
```
Cliente → Frontend → FastAPI → Service → Circuit Breaker (OPEN)
                                                ↓
                                    Retorna erro imediato
```

---

## 🛡️ Segurança

### Multi-Tenancy
- **Implementação:** RLS (Row Level Security)
- **Campo:** `tenant_id`
- **Isolamento:** 100% garantido

### Autenticação
- **WebPosto:** Token Quality Automação
- **API:** JWT (quando aplicável)
- **Service Role:** Para backend

### Autorização
- **RBAC:** Roles (OWNER, ADMIN, MANAGER, FINANCE, OPERATIONS, VIEWER)
- **Governança:** Sprint 25A

---

## 📊 Métricas de Performance

| Componente | Tempo | Status |
|------------|-------|--------|
| Cache HIT | 13.5 ms | ✅ Excelente |
| Cache MISS | 2-5 s | ⚠️ Aceitável |
| API Latency | < 50 ms | ✅ Bom |
| WebPosto Latency | 1-3 s | ⚠️ Externo |
| Frontend Render | < 1 s | ✅ Bom |

---

## 🎯 Princípios Arquiteturais

1. **Snapshot First** - Cache agressivo para performance
2. **Circuit Breaker** - Resiliência contra falhas
3. **Date Ranges** - Sempre garantir datas nos endpoints
4. **Multi-Tenant** - Isolamento total por tenant
5. **Vanilla JS** - Frontend sem frameworks
6. **Service Layer** - Lógica de negócio isolada
7. **Gateway Pattern** - Integração externa encapsulada
8. **RLS** - Segurança no banco

---

## 🚫 Anti-Padrões Proibidos

❌ Acessar Supabase direto do frontend  
❌ Usar React/Vue/Angular no frontend  
❌ Hardcodes de `empresaCodigo`  
❌ Mocks sem autorização  
❌ Chamar WebPosto sem datas obrigatórias  
❌ Bypass do Circuit Breaker  
❌ SQL na UI  

---

**[ARCHITECTURE — APROVADO]**

*Snapshot First Architecture em produção*
