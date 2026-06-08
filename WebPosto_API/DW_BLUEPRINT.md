# DW BLUEPRINT — Data Warehouse LOGOS SPACE
## Sprint A03 — Planejamento (sem implementação)

| Campo | Valor |
|---|---|
| **Data** | 2026-06-08 |
| **Sprint implementação** | A04 |
| **Princípio** | Snapshot → DW ingest → Dashboard lê DW |

---

## Arquitetura Alvo

```
WebPosto → Snapshot Services → DW Ingest (batch) → DW Tables → Dashboard/API
```

---

## Tabelas DW

### dw_sales

| Campo | Valor |
|---|---|
| **Origem** | `VENDA`, `VENDA_ITEM`, `VENDA_FORMA_PAGAMENTO` |
| **Snapshot fonte** | `FinancialOperationalSnapshotService.vendas` |
| **Frequência** | 15 min (alinhado fuel) / 5 min intraday |
| **Retenção** | 24 meses rolling |
| **Granularidade** | empresa_codigo × data × produto |

### dw_expenses

| Campo | Valor |
|---|---|
| **Origem** | `CONSULTAR_DESPESAS_FINANCEIRO_REDE` |
| **Snapshot fonte** | `FinancialOperationalSnapshotService.expenses` |
| **Frequência** | 5 min |
| **Retenção** | 36 meses |
| **Granularidade** | empresa × data × plano_conta × centro_custo |

### dw_accounts

| Campo | Valor |
|---|---|
| **Origem** | `CONTA` (accounts payable/receivable) |
| **Snapshot fonte** | `FinancialOperationalSnapshotService.accounts` |
| **Frequência** | 5 min |
| **Retenção** | 36 meses |
| **Granularidade** | titulo × vencimento × status |

### dw_stock

| Campo | Valor |
|---|---|
| **Origem** | `PRODUTO_ESTOQUE`, `PRODUTO`, `TANQUE` |
| **Snapshot fonte** | Financial snapshot + `/v1/stock` |
| **Frequência** | 15 min |
| **Retenção** | 12 meses |
| **Granularidade** | empresa × produto × data |

### dw_fuel

| Campo | Valor |
|---|---|
| **Origem** | `CONSULTAR_LMC_REDE` |
| **Snapshot fonte** | `FuelSnapshotService` |
| **Frequência** | 15 min |
| **Retenção** | 24 meses |
| **Granularidade** | empresa × combustível × data (litros LMC) |

---

## Camada de Ingestão (A04)

| Job | Trigger | Input | Output |
|---|---|---|---|
| `ingest_executive` | POST refresh / cron 5min | `snapshots/executive/*.json` | `dw_kpis`, `dw_dre` |
| `ingest_financial` | POST refresh / cron 5min | `snapshots/financial/*.json` | `dw_expenses`, `dw_accounts` |
| `ingest_fuel` | POST refresh / cron 15min | `snapshots/fuel/*.json` | `dw_fuel` |
| `ingest_sales` | cron 15min | `/v1/sales` paginado | `dw_sales` |
| `ingest_stock` | cron 15min | `/v1/stock` paginado | `dw_stock` |

---

## Tecnologia Sugerida

| Camada | Opção A | Opção B |
|---|---|---|
| Storage | PostgreSQL (existente) | SQLite local (MVP) |
| Ingest | Python scripts + cron | Celery workers |
| API leitura | Novas rotas `/api/v1/dw/*` | Views materializadas |

---

## Pré-requisitos A03 ✅

- [x] Snapshot First (executive, fuel, financial)
- [x] Multiselect backend
- [x] TTL definidos (5min / 15min)
- [x] Chaves snapshot padronizadas `{dataIni}:{dataFim}:{empresas}`
- [x] Coverage score para metadados DW

---

## Próximo Passo A04

1. Criar schema `dw_*` no Postgres
2. Job ingest a partir de `snapshots/`
3. Rotas read-only `/api/v1/dw/kpis`, `/dw/fuel`
4. Dashboard lê DW com fallback snapshot

---

*Blueprint A03 — sem implementação de DW nesta sprint.*
