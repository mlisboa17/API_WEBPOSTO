# MULTISELECT BACKEND REPORT — Sprint A03
## LOGOS SPACE Combustíveis

| Campo | Valor |
|---|---|
| **Data** | 2026-06-08 |
| **Objetivo** | Eliminar `fetchByCompaniesSequential` e agregação no frontend |

---

## Problema Resolvido

**Antes:**
```
Frontend → N requests (1 por empresa) → agregação JS → resposta
```

**Depois:**
```
Frontend → empresaCodigo=11495,5555,5333 → Backend agrega → 1 resposta
```

---

## Backend — Endpoints Atualizados

| Endpoint | Parâmetro | Agregação |
|---|---|---|
| `GET /api/v1/kpis` | `empresaCodigo: str` (vírgula) | `_aggregate_kpis` |
| `GET /api/v1/dre` | `empresaCodigo: str` | `_aggregate_dre` |
| `GET /api/v1/data-quality` | `empresaCodigo: str` | `_aggregate_data_quality` |
| `GET /api/v1/fuel/executive` | `empresaCodigo: str` | `aggregate_fuel_executive_payload` |
| `GET /api/v1/sales/fuel-summary` | `empresaCodigo: str` | merge por empresa |
| `GET /v1/financial/expenses` | `empresaCodigo: str` | `_resolve_empresas` multiselect |
| `GET /v1/financial/accounts-payable` | `empresaCodigo: str` | `_resolve_empresas` multiselect |
| `GET /v1/sales` | `empresaCodigo: str` | `_resolve_empresas` multiselect |
| `GET /v1/stock` | `empresaCodigo: str` | `_resolve_empresas` multiselect |
| `GET /v1/financial/overview` | `empresaCodigo: str` | `_resolve_empresas` multiselect |

---

## Arquivos Criados/Modificados

| Arquivo | Mudança |
|---|---|
| `src/services/analytics_multiselect.py` | **NOVO** — helpers agregação |
| `src/services/multiselect_utils.py` | **NOVO** — parse vírgula |
| `src/services/fuel_aggregate.py` | **NOVO** — agregação fuel |
| `src/services/network_financial_overview_service.py` | `empresa_codigos: tuple` |
| `src/interfaces/http/routes/analytics.py` | `empresaCodigo: str` |
| `src/interfaces/http/routes/fechamento_enterprise.py` | `empresaCodigo: str` |

---

## Frontend — Removido

| Função | Status |
|---|---|
| `fetchByCompaniesSequential` | **REMOVIDA** |
| `aggregateKpiResults` | **REMOVIDA** |
| `aggregateDreResults` | **REMOVIDA** |
| `aggregateDataQualityResults` | **REMOVIDA** |
| `rebuildFuelExecutivePayload` | **REMOVIDA** |
| `filterFuelSummaryByCompanies` | **REMOVIDA** |
| Loop em `fetchDatasetAcrossCompanies` | **REMOVIDO** |

---

## Frontend — Atualizado

| Função | Mudança |
|---|---|
| `baseFilterParams` | Envia `empresaCodigo` como vírgula (multiselect) |
| `fetchKpis/Dre/DataQuality` | 1 request com vírgula |
| `fetchFuelExecutive/Summary` | 1 request com vírgula |
| `fetchDatasetAcrossCompanies` | 1 request (backend filtra) |

---

## Validação

```
GET /api/v1/kpis?empresaCodigo=11495,5555 → 200 ✅
GET /api/v1/fuel/executive?empresaCodigo=11495,5555 → 200 ✅
GET /v1/financial/expenses?empresaCodigo=11495,5555 → 200 ✅
```

`lineage.aggregate` agora retorna `"multiselect_backend"` nos KPIs agregados.

---

*Sprint A03 — multiselect backend operacional.*
