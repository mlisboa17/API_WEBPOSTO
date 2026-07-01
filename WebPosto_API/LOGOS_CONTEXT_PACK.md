# LOGOS CONTEXT PACK
## Fonte Única da Verdade — LOGOS SPACE / WebPosto

**Versão:** 1.0  
**Data:** 2026-06-28  
**Status:** PRODUÇÃO ATIVA  
**Última Atualização:** Sprint 25A — Advanced Governance

---

> ⚠️ **LEIA ANTES DE QUALQUER ALTERAÇÃO**
> 
> Este documento previne erros comuns:
> - Trabalhar no projeto errado (`dashboard-v2`)
> - Usar stack errada (React/Vite em vez de Vanilla JS)
> - Acessar Supabase direto do frontend
> - Usar mocks sem autorização
> - Endpoint ou schema incorreto

---

## 📋 ÍNDICE

1. [Sistema Oficial](#seção-1--sistema-oficial)
2. [O Que NÃO Usar](#seção-2--o-que-não-usar)
3. [Fluxo de Dados](#seção-3--fluxo-de-dados-oficial)
4. [Mapeamento de Filiais](#seção-4--mapeamento-oficial-de-filiais)
5. [Endpoints FastAPI](#seção-5--endpoints-fastapi-oficiais)
6. [Regras de Datas](#seção-6--regra-de-datas-obrigatórias)
7. [Circuit Breaker](#seção-7--circuit-breaker)
8. [Telas Oficiais](#seção-8--telas-oficiais)
9. [Regras para Sprints](#seção-9--regras-para-novas-sprints)
10. [Checklist de Validação](#seção-10--checklist-de-validação)

---

## SEÇÃO 1 — SISTEMA OFICIAL

### Backend Oficial

| Item | Valor |
|------|-------|
| **Arquivo Entrypoint** | `src/main.py` |
| **Framework** | FastAPI |
| **Porta Local** | `8040` |
| **URL Base** | `http://127.0.0.1:8040` |
| **Comando Oficial** | `python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 --reload` |

**Pasta:** `WebPosto_API/src/`

### Frontend Oficial

| Item | Valor |
|------|-------|
| **Pasta** | `frontend/` |
| **Stack** | Vanilla JavaScript SPA |
| **Entrypoint** | `frontend/index.html` |
| **Servido por** | FastAPI StaticFiles |
| **URL Principal** | `http://127.0.0.1:8040/app/financial` |

**NÃO é React. NÃO é Vite. É JavaScript vanilla ES6+.**

### Arquitetura de Dados

```
┌─────────────────┐
│   WebPosto API  │ ← Quality Automação (API externa)
│  (Quality Auth) │
└────────┬────────┘
         │
         ↓
┌─────────────────────────┐
│  webposto_client.py     │ ← Circuit Breaker + Retry
│  (src/gateway/)         │
└────────┬────────────────┘
         │
         ↓
┌─────────────────────────┐
│    Services FastAPI     │ ← Business Logic
│    (src/services/)      │
└────────┬────────────────┘
         │
         ↓ (opcional)
┌─────────────────────────┐
│   Snapshot Store        │ ← Cache TTL 300s
│   (performance)         │
└────────┬────────────────┘
         │
         ↓
┌─────────────────────────┐
│   Rotas FastAPI         │ ← `/v1/*` e `/api/v1/*`
│   (src/interfaces/)       │
└────────┬────────────────┘
         │
         ↓
┌─────────────────────────┐
│   Frontend Vanilla JS   │ ← `frontend/` SPA
│   (app.js, pages/)        │
└─────────────────────────┘
```

**REGRA CRÍTICA:** Frontend NÃO consulta Supabase diretamente. Sempre via FastAPI.

---

## SEÇÃO 2 — O QUE NÃO USAR

### ❌ PROIBIDO — `dashboard-v2/`

| Aspecto | Status |
|---------|--------|
| **Pasta** | `dashboard-v2/` |
| **Stack** | React + Vite |
| **Status** | ⚠️ EXPERIMENTAL / NÃO USAR |
| **Commits** | 3 apenas (template) |
| **Integração** | NENHUMA com sistema real |
| **Dados** | Mock/demo apenas |

**Motivo:** É um template Vite padrão, não é o LOGOS oficial.

**Se você vir:**
- "Get started"
- "Edit src/App.tsx"
- React hooks
- Vite HMR

**→ Você está no projeto errado.**

### ❌ PROIBIDO — Supabase Direto no Frontend

**NUNCA faça:**
```javascript
// ❌ ERRADO - NUNCA FAZER ISSO
const { data } = await supabase.from('fact_venda').select('*')
```

**Sempre faça:**
```javascript
// ✅ CERTO - Via API FastAPI
const response = await fetch('/api/v1/sales')
const data = await response.json()
```

**Motivo:** RLS, multi-tenancy, circuit breaker, auditoria — tudo fica no backend.

### ❌ PROIBIDO — Mocks Sem Autorização

**NUNCA use dados mock/fake sem autorização explícita do usuário.**

**Exceção:** Apenas em desenvolvimento inicial com flag explícita.

---

## SEÇÃO 3 — FLUXO DE DADOS OFICIAL

### Camada de Integração

```
WebPosto API (Quality Automação)
    │
    ├──→ webposto_client.py
    │       ├──→ Circuit Breaker (SimpleCircuitBreaker)
    │       ├──→ Retry com backoff
    │       ├──→ Timeout (30s padrão, 60s endpoints lentos)
    │       └──→ Permission discovery
    │
    ↓
Services FastAPI (src/services/)
    ├──→ NetworkFinancialOverviewService
    ├──→ FinancialIntelligenceService
    ├──→ CashFlowService
    ├──→ SalesService
    ├──→ FuelService
    └──→ [50+ serviços oficiais]
    │
    ↓ (cache opcional)
Snapshot Store (TTL 300s)
    ├──→ finance_center_snapshot_service.py
    ├──→ finance_intelligence_snapshot_service.py
    └──→ cash_flow_snapshot_service.py
    │
    ↓
Rotas FastAPI (src/interfaces/http/routes/)
    ├──→ /v1/financial/*
    ├──→ /api/v1/*
    └──→ /app/*
    │
    ↓
Frontend SPA (frontend/)
    ├──→ app.js (entrypoint)
    ├──→ pages/*.js (50+ páginas)
    └──→ components/*.js (15+ componentes)
```

### Integração WebPosto

**Arquivo:** `src/gateway/webposto_client.py`

**Responsabilidades:**
- ✅ Autenticação com API WebPosto (CHAVE)
- ✅ Circuit Breaker (failure_threshold=3, block_seconds=3600)
- ✅ Retry com backoff exponencial
- ✅ Timeout management
- ✅ Permission discovery
- ✅ DateRangeResolver (auto-injeção de datas)

**Endpoints Integrados:** 49 endpoints mapeados

### Snapshot First Architecture

**Performance:**
- Cache HIT: **13.5 ms**
- Cache MISS: **2-5 segundos**
- TTL: **300 segundos (5 minutos)**

**Arquivos:**
- `finance_center_snapshot_service.py`
- `finance_intelligence_snapshot_service.py`
- `cash_flow_snapshot_service.py`

---

## SEÇÃO 4 — MAPEAMENTO OFICIAL DE FILIAIS

### Regra de Ouro

> **NUNCA exibir `empresaCodigo` cru para o usuário final.**

Sempre resolver via mapping.

### Tabela de Mapeamento

| empresaCodigo | Nome Fantasia | Tipo | Status |
|--------------|---------------|------|--------|
| 5256 | POSTO BR SHOPPING | Filial | ✅ Ativo |
| 5333 | POSTO JANGA | Filial | ✅ Ativo |
| 5556 | POSTO CIDADE PATRIMONIO | Filial | ✅ Ativo |
| **5555** | **AP CASA CAIADA** | **Matriz** | **✅ Principal** |
| 5557 | POSTO ENSEADA DO NORTE | Filial | ✅ Ativo |
| 5560 | POSTO SERTÃ | Filial | ✅ Ativo |
| 7 | POSTO REAL | Filial | ✅ Ativo |
| 5559 | POSTO RJ | Filial | ✅ Ativo |
| 9 | AUTO POSTO GLOBO | Filial | ✅ Ativo |
| **11495** | **POSTO VIP** | **Matriz** | **✅ Principal** |
| 46433 | POSTO DOZE | Filial | ✅ Ativo |
| 74014 | POSTO DOZE FILIAL II | Filial | ✅ Ativo |

### Uso no Código

```python
# Backend: Sempre usar empresaCodigo
params = {
    "empresaCodigo": 11495,  # POSTO VIP
    "dataInicial": "2026-06-01",
    "dataFinal": "2026-06-28"
}

# Frontend: Exibir nome fantasia
// POSTO VIP (11495)
// Ocultar o código, mostrar apenas o nome
```

---

## SEÇÃO 5 — ENDPOINTS FASTAPI OFICIAIS

### Endpoints Base

| Método | Path | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/health` | Health check | Público |
| GET | `/ready` | Readiness probe | Público |
| GET | `/docs` | Swagger UI | Público |
| GET | `/redoc` | ReDoc | Público |

### Endpoints de Permissões

| Método | Path | Descrição | Parâmetros |
|--------|------|-----------|------------|
| GET | `/v1/permissions` | Lista permissões | `tenant` (opcional) |

### Endpoints Financeiros

| Método | Path | Descrição | Datas Obrigatórias | X-Posto-ID |
|--------|------|-----------|-------------------|------------|
| GET | `/v1/financial/overview` | Overview financeiro | ✅ Sim | ✅ Sim |
| GET | `/v1/financial/expenses` | Despesas | ✅ Sim | ✅ Sim |
| GET | `/v1/financial/accounts-payable` | Contas a pagar | ✅ Sim | ✅ Sim |
| GET | `/v1/financial/accounts-receivable` | Contas a receber | ✅ Sim | ✅ Sim |
| GET | `/v1/financial/health-score` | Health score v3 | ❌ Não | ❌ Não |

### Endpoints Comerciais

| Método | Path | Descrição | Datas Obrigatórias |
|--------|------|-----------|-------------------|
| GET | `/v1/sales` | Vendas | ✅ Sim |
| GET | `/v1/stock` | Estoque | ✅ Sim |
| GET | `/api/v1/fuel/executive` | Executivo combustíveis | ❌ Não |
| GET | `/api/v1/products/catalog` | Catálogo produtos | ❌ Não |

### Endpoints Analytics

| Método | Path | Descrição | Cache |
|--------|------|-----------|-------|
| GET | `/api/v1/kpis` | KPIs executivos | ✅ 300s |
| GET | `/api/v1/dre` | DRE | ✅ 300s |
| GET | `/api/v1/data-quality` | Qualidade dados | ❌ Não |

### Endpoints Governance (NOVO — Sprint 25A)

| Método | Path | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/v1/governance/dashboard` | Dashboard governança | Service |
| GET | `/v1/governance/audit-log` | Logs auditoria | Service |
| GET | `/v1/governance/rbac/user-role` | Role do usuário | Service |
| POST | `/v1/governance/rbac/assign-role` | Atribuir role | Admin |

### Parâmetros Comuns

#### Datas (Obrigatórios em endpoints operacionais)

```
dataInicial: string (YYYY-MM-DD)
dataFinal: string (YYYY-MM-DD)
```

**Default aplicado:** `last_7_days` (via `DateRangeResolver`)

#### Tenant

```
tenant: string (opcional)
X-Posto-ID: header (obrigatório em endpoints WebPosto)
```

### Especificação Completa

Para especificação OpenAPI completa, consulte:
- `API_CATALOG.md`
- Swagger UI: `http://127.0.0.1:8040/docs`

---

## SEÇÃO 6 — REGRA DE DATAS OBRIGATÓRIAS

### Regra de Ouro

> **Endpoints operacionais SEMPRE exigem `dataInicial` e `dataFinal`.**

### Cenário

Sem datas → Erro 400 BAD REQUEST → Circuit Breaker abre → Sistema quebra

### Solução Implementada

**Arquivo:** `src/services/date_range_resolver.py`

**Presets disponíveis:**
- `today`
- `yesterday`
- `last_7_days` (default)
- `last_30_days`
- `current_month`
- `previous_month`

**Arquivo:** `src/gateway/webposto_endpoint_contracts.py`

**Contratos de endpoint:**
- Mapeia 49 endpoints
- Indica `requires_date_range: true/false`
- Indica `requires_empresa_codigo: true/false`

### Exemplo de Uso

```python
from src.services.date_range_resolver import DateRangeResolver

# Garantir datas presentes
params = DateRangeResolver.ensure_date_params(params, default_preset="last_7_days")
# Resultado: {"dataInicial": "2026-06-21", "dataFinal": "2026-06-28"}
```

---

## SEÇÃO 7 — CIRCUIT BREAKER

### Arquivo

`src/gateway/webposto_client.py`

### Configuração

```python
class SimpleCircuitBreaker:
    failure_threshold = 3      # Abre após 3 falhas
    block_seconds = 3600       # Fecha após 1 hora
```

### Estados

| Estado | Descrição | Ação |
|--------|-----------|------|
| `CLOSED` | Normal | Requisições passam |
| `OPEN` | Bloqueado | Requisições rejeitadas |
| `HALF_OPEN` | Testando | 1 requisição de teste |

### Causa Raiz de Abertura (Histórico)

**Problema:** Chamadas sem datas obrigatórias → 400 BAD REQUEST

**Status:** ✅ Corrigido por `HOTFIX DATA-PARAMS-01`

### Reset Manual

```bash
# Via endpoint admin
POST /api/v1/admin/circuit-breaker/reset
```

Ou via script:
```bash
python scripts/reset_circuit_breaker.py
```

### Monitoramento

```bash
# Status atual
curl http://127.0.0.1:8040/api/v1/admin/circuit-breaker/status
```

---

## SEÇÃO 8 — TELAS OFICIAIS

### Estrutura do Frontend

```
frontend/
├── index.html                 ← Entrypoint HTML
├── app.js                     ← Aplicação principal
├── styles.css                 ← Estilos globais
├── pages/                     ← 50+ páginas
│   ├── executiveDashboard.js
│   ├── fuelExecutiveDashboard.js
│   ├── sales.js
│   ├── dashboard.js
│   ├── expenses.js
│   ├── accountsPayable.js
│   ├── stock.js
│   ├── security.html          ← NOVO (Sprint 25A)
│   ├── governance.html        ← NOVO (Sprint 25A)
│   └── (47+ páginas)
├── components/                ← 15+ componentes
│   ├── navigationShell.js
│   ├── filters.js
│   ├── table.js
│   └── (12+ componentes)
└── services/                  ← 10+ serviços
    ├── api.js                 ← Cliente API principal
    └── (9+ serviços)
```

### Telas Principais

| Tela | Arquivo | Status | URL |
|------|---------|--------|-----|
| **Dashboard Executivo** | `executiveDashboard.js` | ✅ Pronto | `/app/financial` |
| **Combustíveis** | `fuelExecutiveDashboard.js` | ✅ Pronto | `/app/financial` (tab) |
| **Vendas** | `sales.js` | ✅ Pronto | Via navegação |
| **Financeiro** | `dashboard.js` | ⚠️ Parcial | Via navegação |
| **Despesas** | `expenses.js` | ⚠️ Parcial | Via navegação |
| **Contas** | `accountsPayable.js` | ⚠️ Parcial | Via navegação |
| **Estoque** | `stock.js` | ⚠️ Parcial | Via navegação |
| **Security Center** | `security.html` | ✅ NOVO | `/pages/security.html` |
| **Governance Dashboard** | `governance.html` | ✅ NOVO | `/pages/governance.html` |

### Stack Tecnológico

- **HTML5** sem frameworks
- **Vanilla JavaScript ES6+**
- **CSS3** custom (não Bootstrap)
- **Fetch API** para chamadas HTTP
- **Sem React, Vue, Angular**
- **Sem Vite, Webpack, Parcel**

---

## SEÇÃO 9 — REGRAS PARA NOVAS SPRINTS

### Regras Obrigatórias

1. ✅ **Sempre trabalhar no sistema oficial**
   - Backend: `src/` (FastAPI)
   - Frontend: `frontend/` (Vanilla JS)

2. ❌ **NUNCA usar `dashboard-v2/`**
   - É experimental/template
   - Não tem integração real

3. ❌ **NUNCA usar mock sem autorização**
   - Sempre preferir dados reais
   - Se mock necessário, documentar explicitamente

4. ❌ **NUNCA acessar Supabase direto do frontend**
   - Sempre via FastAPI endpoints
   - Mantém RLS, auditoria, circuit breaker

5. ✅ **Sempre usar FastAPI services**
   - Criar service em `src/services/`
   - Criar rota em `src/interfaces/http/routes/`
   - Registrar em `src/main.py` ou `app.py`

6. ✅ **Sempre passar datas quando necessário**
   - Verificar `webposto_endpoint_contracts.py`
   - Usar `DateRangeResolver` para garantir

7. ✅ **Sempre resolver filial por `empresaCodigo`**
   - Usar tabela de mapeamento oficial
   - Nunca exibir código cru para usuário

8. ✅ **Sempre documentar em `API_MANUAL_INDEX.md`**
   - Novos endpoints
   - Alterações de contrato
   - Mudanças de arquitetura

### Checklist Pré-Sprint

- [ ] Estou na pasta `WebPosto_API/`?
- [ ] Estou editando `src/` ou `frontend/`?
- [ ] Não estou tocando em `dashboard-v2/`?
- [ ] O endpoint usa datas? (verificar contrato)
- [ ] O endpoint resolve empresaCodigo corretamente?
- [ ] Estou evitando mocks?
- [ ] Vou documentar no API_MANUAL_INDEX.md?

---

## SEÇÃO 10 — CHECKLIST DE VALIDAÇÃO

### Antes de Qualquer Hotfix/Sprint

**Verificação de Localização:**
- [ ] Estou na pasta correta (`WebPosto_API/`)?
- [ ] Estou no backend FastAPI (`src/`)?
- [ ] Estou no frontend oficial (`frontend/`)?
- [ ] NÃO estou em `dashboard-v2/`?

**Verificação de Comunicação:**
- [ ] Estou usando porta 8040?
- [ ] O backend está rodando (`uvicorn`)?
- [ ] Consigo acessar `/health`?

**Verificação de Dados:**
- [ ] O endpoint exige `dataInicial` e `dataFinal`?
- [ ] Estou usando `DateRangeResolver`?
- [ ] Estou usando dados reais (não mocks)?

**Verificação de Filiais:**
- [ ] Estou respeitando o mapeamento de `empresaCodigo`?
- [ ] Não estou exibindo código cru para usuário?

**Verificação de Integração:**
- [ ] NÃO estou acessando Supabase direto do frontend?
- [ ] Estou usando os services FastAPI corretamente?
- [ ] O Circuit Breaker está fechado?

### Comandos de Validação Rápida

```bash
# 1. Verificar pasta
pwd
# Deve mostrar: .../WebPosto_API

# 2. Iniciar backend
python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 --reload

# 3. Verificar health
curl http://127.0.0.1:8040/health

# 4. Verificar circuit breaker
curl http://127.0.0.1:8040/api/v1/admin/circuit-breaker/status

# 5. Testar endpoint financeiro
curl "http://127.0.0.1:8040/v1/financial/overview?dataInicial=2026-06-01&dataFinal=2026-06-28" \
  -H "X-Posto-ID: 11495"
```

### No Navegador

```javascript
// Verificar se está no sistema correto
console.log(window.location.href)
// Deve conter: 127.0.0.1:8040/app/

// Verificar se não é Vite
console.log(document.title)
// Deve ser: LOGOS SPACE (não "Vite App")

// Testar chamada API
fetch('/api/v1/kpis')
  .then(r => r.json())
  .then(d => console.log('KPIs:', d))
```

---

## 📚 REFERÊNCIAS

### Documentos Relacionados

| Documento | Propósito |
|-----------|-----------|
| `README.md` | Visão geral do projeto |
| `ARCHITECTURE_BASELINE_2.0.md` | Arquitetura detalhada |
| `API_CATALOG.md` | Catálogo de endpoints |
| `DASHBOARD_CATALOG.md` | Catálogo de dashboards |
| `API_MANUAL_INDEX.md` | Manual de API |
| `LOGOS_RUNBOOK_OFFICIAL_APP.md` | Guia operacional |
| `LOGOS_ARCHITECTURE_REAL_CONSOLIDATED.md` | Arquitetura consolidada |

### Swagger UI

Acesse: `http://127.0.0.1:8040/docs`

### Contato

Para dúvidas sobre arquitetura, consulte este documento primeiro.

---

## ✅ STATUS

**[LOGOS CONTEXT PACK — APROVADO]**

- ✅ Sistema oficial registrado
- ✅ O que NÃO usar documentado
- ✅ Fluxo de dados oficial documentado
- ✅ Mapeamento de filiais incluído
- ✅ Endpoints consolidados
- ✅ Regras de datas incluídas
- ✅ Circuit Breaker documentado
- ✅ Telas oficiais listadas
- ✅ Regras para sprints definidas
- ✅ Checklist de validação criado

**Próxima ação:** Usar este documento como referência em todas as sprints futuras.

---

*Documento criado em: 2026-06-28*  
*Última atualização: Sprint 25A — Advanced Governance*  
*Versão: 1.0*
