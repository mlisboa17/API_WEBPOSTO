# API Catalog
## Catálogo Oficial de Endpoints - LOGOS SPACE

**Versão:** 1.0  
**Data:** 2026-06-28  
**Status:** Ativo  
**Base URL:** `http://127.0.0.1:8040`

---

## 🎯 Índice por Categoria

1. [Base](#base)
2. [Health & Monitoring](#health--monitoring)
3. [Financeiro](#financeiro)
4. [Comercial](#comercial)
5. [Fiscal](#fiscal)
6. [Dashboard & Analytics](#dashboard--analytics)
7. [Governança](#governança)
8. [IA & Copilot](#ia--copilot)
9. [Admin](#admin)

---

## Base

| Método | Path | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/` | Root - redirect para app | Público |
| GET | `/docs` | Swagger UI | Público |
| GET | `/redoc` | ReDoc Documentation | Público |
| GET | `/openapi.json` | OpenAPI Schema | Público |

---

## Health & Monitoring

| Método | Path | Descrição | Datas | Cache |
|--------|------|-----------|-------|-------|
| GET | `/health` | Health check | ❌ Não | ❌ Não |
| GET | `/ready` | Readiness probe | ❌ Não | ❌ Não |
| GET | `/metrics` | Prometheus metrics | ❌ Não | ❌ Não |

### Exemplo:
```bash
curl http://127.0.0.1:8040/health
```

---

## Financeiro

### Overview

| Método | Path | Descrição | Datas | X-Posto-ID | Service |
|--------|------|-----------|-------|------------|---------|
| GET | `/v1/financial/overview` | Overview financeiro | ✅ Sim | ✅ Sim | `network_financial_overview_service.py` |
| GET | `/v1/financial/companies` | Lista empresas | ❌ Não | ❌ Não | - |

### Despesas

| Método | Path | Descrição | Datas | X-Posto-ID | Service |
|--------|------|-----------|-------|------------|---------|
| GET | `/v1/financial/expenses` | Despesas | ✅ Sim | ✅ Sim | `expense_service.py` |
| GET | `/v1/financial/accounts-payable` | Contas a pagar | ✅ Sim | ✅ Sim | `accounts_payable_service.py` |
| GET | `/v1/financial/accounts-receivable` | Contas a receber | ✅ Sim | ✅ Sim | `accounts_receivable_service.py` |

### Inteligência

| Método | Path | Descrição | Datas | Cache |
|--------|------|-----------|-------|-------|
| GET | `/v1/financial/health-score` | Health Score v3 | ❌ Não | ✅ 300s |
| GET | `/v1/financial/forecast` | Forecast financeiro | ✅ Sim | ✅ 300s |
| GET | `/v1/financial/benchmark` | Benchmark | ✅ Sim | ✅ 300s |

### Cash Flow

| Método | Path | Descrição | Datas | Service |
|--------|------|-----------|-------|---------|
| GET | `/v1/financial/cash-flow` | Fluxo de caixa | ✅ Sim | `corporate_cash_flow_service.py` |
| GET | `/v1/financial/cash-operations` | Operações caixa | ✅ Sim | `cash_operations_service.py` |

### Exemplo:
```bash
# Com datas obrigatórias
curl "http://127.0.0.1:8040/v1/financial/overview?dataInicial=2026-06-01&dataFinal=2026-06-28" \
  -H "X-Posto-ID: 11495"
```

---

## Comercial

### Vendas

| Método | Path | Descrição | Datas | Cache |
|--------|------|-----------|-------|-------|
| GET | `/v1/sales` | Vendas consolidadas | ✅ Sim | ✅ 300s |
| GET | `/v1/sales/by-product` | Vendas por produto | ✅ Sim | ✅ 300s |
| GET | `/v1/sales/by-filial` | Vendas por filial | ✅ Sim | ✅ 300s |

### Estoque

| Método | Path | Descrição | Datas | Cache |
|--------|------|-----------|-------|-------|
| GET | `/v1/stock` | Estoque atual | ❌ Não | ✅ 300s |
| GET | `/v1/stock/movements` | Movimentações | ✅ Sim | ✅ 300s |

### Combustíveis

| Método | Path | Descrição | Datas | Cache |
|--------|------|-----------|-------|-------|
| GET | `/api/v1/fuel/executive` | Dashboard combustíveis | ❌ Não | ✅ 300s |
| GET | `/api/v1/fuel/abastecimento` | Abastecimentos | ✅ Sim | ✅ 300s |
| GET | `/api/v1/fuel/tanks` | Tanques | ❌ Não | ✅ 300s |

### Produtos

| Método | Path | Descrição | Datas | Cache |
|--------|------|-----------|-------|-------|
| GET | `/api/v1/products/catalog` | Catálogo de produtos | ❌ Não | ✅ 300s |
| GET | `/v1/products/stock` | Estoque de produtos | ❌ Não | ✅ 300s |

---

## Fiscal

| Método | Path | Descrição | Datas | Circuit Breaker |
|--------|------|-----------|-------|-----------------|
| GET | `/api/v1/fiscal/nfce` | Notas fiscais consumidor | ✅ Sim | ✅ Sim |
| GET | `/api/v1/fiscal/lmc` | LMC (Livro Movimentação Combustível) | ✅ Sim | ✅ Sim |
| GET | `/api/v1/fiscal/reconciliation` | Conciliação fiscal | ✅ Sim | ✅ Sim |

---

## Dashboard & Analytics

### Executive

| Método | Path | Descrição | Datas | Cache |
|--------|------|-----------|-------|-------|
| GET | `/api/v1/executive/snapshot` | Snapshot executivo | ❌ Não | ✅ 300s |
| POST | `/api/v1/executive/refresh` | Força refresh snapshot | ❌ Não | ❌ Não |
| GET | `/api/v1/kpis` | KPIs executivos | ❌ Não | ✅ 300s |
| GET | `/api/v1/dre` | DRE (Demonstração Resultado) | ✅ Sim | ✅ 300s |

### Data Quality

| Método | Path | Descrição | Datas |
|--------|------|-----------|-------|
| GET | `/api/v1/data-quality` | Qualidade dos dados | ❌ Não |
| GET | `/api/v1/network/coverage` | Cobertura de rede | ❌ Não |

### Sync

| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/api/v1/sync/control` | Controle de sync |
| GET | `/api/v1/sync/logs` | Logs de sincronização |
| GET | `/api/v1/sync/errors` | Erros de sync |

---

## Governança

| Método | Path | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/v1/governance/dashboard` | Dashboard governança | Service |
| GET | `/v1/governance/audit-log` | Logs auditoria | Service |
| GET | `/v1/governance/audit-log/stats` | Estatísticas audit | Service |
| GET | `/v1/governance/rbac/user-role` | Role do usuário | Service |
| POST | `/v1/governance/rbac/assign-role` | Atribuir role | Admin |
| GET | `/v1/governance/rbac/check-permission` | Verificar permissão | Service |
| GET | `/v1/governance/security/events` | Eventos segurança | Service |

### Exemplo:
```bash
curl "http://127.0.0.1:8040/v1/governance/dashboard?tenant=POSTO_VIP"
```

---

## IA & Copilot

| Método | Path | Descrição | Auth |
|--------|------|-----------|------|
| POST | `/v1/copilot/query` | Query ao copilot | Autenticado |
| GET | `/v1/copilot/history` | Histórico de queries | Autenticado |
| GET | `/v1/copilot/suggestions` | Sugestões IA | Autenticado |

---

## Admin

### Circuit Breaker

| Método | Path | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/api/v1/admin/circuit-breaker/status` | Status CB | Admin |
| POST | `/api/v1/admin/circuit-breaker/reset` | Reset CB | Admin |

### Permissions

| Método | Path | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/v1/permissions` | Lista permissões | Autenticado |

---

## 📊 Resumo por Categoria

| Categoria | Endpoints | Datas Obrigatórias | Cache |
|-----------|-----------|-------------------|-------|
| Base | 4 | 0 | 0 |
| Health | 3 | 0 | 0 |
| Financeiro | 10 | 8 | 6 |
| Comercial | 12 | 8 | 10 |
| Fiscal | 3 | 3 | 3 |
| Dashboard | 8 | 2 | 6 |
| Governança | 7 | 0 | 0 |
| IA | 3 | 0 | 0 |
| Admin | 3 | 0 | 0 |
| **TOTAL** | **53** | **21** | **25** |

---

## 🔒 Parâmetros Obrigatórios

### Datas (para endpoints operacionais)

```
dataInicial: string (YYYY-MM-DD)
dataFinal: string (YYYY-MM-DD)
```

**Default:** `last_7_days` via `DateRangeResolver`

### Headers

```
X-Posto-ID: string (empresaCodigo)
Authorization: Bearer <token> (quando aplicável)
```

### Query Params Comuns

```
tenant: string (opcional, default: POSTO_VIP)
limit: integer (opcional, default: 100)
offset: integer (opcional, default: 0)
```

---

## 📋 Convenções

### Nomenclatura

- **Base:** `/` ou `/health`
- **Versão:** `/v1/` ou `/api/v1/`
- **Recurso:** substantivo plural (ex: `/expenses`)
- **Ação:** verbo no POST (ex: `/refresh`)

### Respostas

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2026-06-28T12:00:00Z",
    "cache_hit": true
  }
}
```

### Erros

```json
{
  "success": false,
  "error": {
    "code": "CIRCUIT_OPEN",
    "message": "Circuit breaker is open"
  }
}
```

---

## 🔄 Atualização

**Quando:** Novo endpoint criado

**Processo:**
1. Implementar endpoint
2. Testar localmente
3. Documentar neste arquivo
4. Atualizar `01_API_MANUAL_INDEX.md`
5. Atualizar Swagger/OpenAPI

---

**[API CATALOG — APROVADO]**

*Atualizar ao adicionar novos endpoints*
