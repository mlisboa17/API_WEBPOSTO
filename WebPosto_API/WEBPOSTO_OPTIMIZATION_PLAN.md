# WEBPOSTO OPTIMIZATION PLAN — Sprint A03
## LOGOS SPACE Combustíveis

| Campo | Valor |
|---|---|
| **Data** | 2026-06-08 |
| **Foco** | Chamadas repetidas, duplicadas e cacheáveis |

---

## P0 — Bloqueadores (ação externa + A04)

| # | Consulta | Problema | Ação | Ganho |
|---|---|---|---|---|
| 1 | Token combustíveis 2/11 filiais | 82% rede sem LMC | Quality: expandir token | +400% cobertura |
| 2 | `VENDA_ITEM_REDE` / `LMC_REDE` 401 | Fallback N×empresa | Quality: habilitar `_REDE` | -67% loops |
| 3 | KPIs: 3 calls síncronas/empresa | Latência 30-90s | Snapshot-first ✅ A03 | -80% UI timeout |

---

## P1 — Alto Impacto (A03 parcial + A04)

| # | Consulta | Problema | Ação | Status |
|---|---|---|---|---|
| 4 | Multiselect frontend N requests | 3× latência | Backend agrega ✅ A03 | **FEITO** |
| 5 | Fuel executive sem cache longo | Hit a cada refresh | Cache 15min ✅ A03 | **FEITO** |
| 6 | Executive snapshot sem TTL | Dados stale | TTL 5min ✅ A03 | **FEITO** |
| 7 | `discover_permissions` no boot | 26+ probes | Cache boot-only | A04 |
| 8 | Paginação expenses 500 limit | Dados incompletos | Cursor/offset fix | A04 |
| 9 | `EMPRESAS` 2× no boot 8050 | +10s startup | Unificar call | A04 |

---

## P2 — Médio Impacto (A04-A05)

| # | Consulta | Problema | Ação |
|---|---|---|---|
| 10 | ProdutoCatalog por empresa | Sequencial | Batch `_REDE` ou cache 24h ✅ |
| 11 | Coverage sem cache | Hit EMPRESAS toda vez | Cache 5min snapshot |
| 12 | Sync logs memória | Re-fetch após restart | SQLite persist |
| 13 | `analise_vendas_combustivel` | Timeout | Deprecar → fuel-summary |
| 14 | Financial snapshot paginação | 500 limit | DW ingest A04 |

---

## Consultas Evitáveis (pós-A03)

| Consulta | Evitada por | Redução |
|---|---|---|
| N × `/api/v1/kpis` | 1 request multiselect | -67% |
| N × `/v1/financial/expenses` | 1 request multiselect | -67% |
| Live fuel em toda visita | Fuel snapshot 15min | -70% |
| Re-fetch executive stale | TTL 5min + background | -50% polling |

---

## Consultas Cacheáveis

| Endpoint WebPosto | TTL atual | TTL alvo |
|---|---|---|
| `CONSULTAR_LMC_REDE` | 60s analytics | **15min** snapshot ✅ |
| `VENDA_ITEM` (fuel) | 60s | 5min snapshot |
| `EMPRESAS` | Sem cache | 15min |
| `DESPESAS_FINANCEIRO_REDE` | Sem cache | 5min financial snapshot |
| `PRODUTO` / catálogo | 24h | 24h ✅ |

---

*Plano alinhado com TOP_20_PERFORMANCE_BOTTLENECKS.md e implementação A03.*
