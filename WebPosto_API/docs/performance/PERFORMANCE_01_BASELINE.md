# PERFORMANCE-01 — Baseline de Performance (Medido)

Data: 2026-07-03  
analysis_id: `7be8b0a0-6b2e-4a8c-a6eb-cdb4d30955ab`  
Período: 2026-06-26 → 2026-07-03  
Modo: pipeline real, cache de permissão limpo no início

## Referência BUILD-03B

| métrica | BUILD-03B | PERFORMANCE-01 (instrumentado) |
|---|---:|---:|
| Tempo total | **205.500 ms** | **~86.000 ms** (wall clock engine) |
| Tenant 5555 | 79.542 ms | 37.990 ms |
| Tenant 11495 | 61.023 ms | 24.288 ms |
| Tenant 74014 | 60.649 ms | 23.704 ms |

Variação explicada por: latência de rede, timeouts em `CONSULTAR_ANALISE_VENDAS_COMBUSTIVEL` (~20s no cold probe BUILD-03B), e estado do permission cache global.

**Baseline oficial para comparação:** usar **205,5s BUILD-03B** como pior caso documentado; **~86–97s** como medição instrumentada desta sprint (cold permission, sem snapshot).

---

## Onde estão os ~86s (ranking medido)

| # | Operação | ms | % do engine |
|---|---|---:|---:|
| 1 | **Fuel data via WebPosto (`VENDA_ITEM` paginado)** | **52.431** | **~61%** |
| 2 | **`EMPRESAS` redundante dentro de `get_fuel_summary`** | **17.772** | **~21%** |
| 3 | **Permission probe (cold, 1× credencial VIP)** | **12.728** | **~15%** |
| 4 | `VENDA` + `PRODUTO` + pagamentos auxiliares | ~15.630 | ~18%* |
| 5 | Tenant discovery (`/EMPRESAS` inicial) | 1.900 | ~2% |
| 6 | Config / serialização | <10 | ~0% |

\*Soma parcial — endpoints auxiliares incluídos no bloco fuel-summary por tenant.

---

## Breakdown por tenant (engine)

| tenant | empresaCodigo | ms | detector |
|---|---|---:|---|
| AP CASA CAIADA | 5555 | 37.990 | FuelRevenueDetector |
| POSTO VIP | 11495 | 24.288 | FuelRevenueDetector |
| POSTO DOZE FILIAL II | 74014 | 23.704 | FuelRevenueDetector |
| **Total engine** | | **~86.000** | |

---

## WebPosto requests (138 total)

| endpoint | count | ms acumulado |
|---|---:|---:|
| `/INTEGRACAO/VENDA_ITEM` | 60 | 52.431 |
| `/INTEGRACAO/EMPRESAS` | 6 | 17.772 |
| `/INTEGRACAO/VENDA` | 6 | 5.655 |
| `/INTEGRACAO/PRODUTO` | 6 | 5.104 |
| `/INTEGRACAO/CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE` | 6 | 4.871 |

**Por tenant (HTTP):** ~22–23s cada (5555: 23.393ms, 11495: 22.688ms, 74014: 21.980ms)

---

## TOP 5 bottlenecks (comprovados)

1. **Paginação `VENDA_ITEM`** — 60 requests, 52,4s — núcleo do `get_fuel_summary`
2. **`EMPRESAS` repetido** — 6× dentro da análise (2 períodos × 3 tenants via `_resolve_empresas`)
3. **Permission probe cold** — 12,7s (29 endpoints × 1 credencial); hits subsequentes 0ms (cache global)
4. **Execução sequencial multi-tenant** — 3 tenants somados (~86s vs ~24s se paralelo ideal)
5. **Ausência de Analysis Snapshot** — Home bloqueia em análise síncrona completa

---

## Permission probe — causa do overhead

| pergunta | resposta medida |
|---|---|
| Por que executa? | `WebPostoClient.call_endpoint` chama `discover_permissions()` antes de cada endpoint |
| O que valida? | 29 endpoints mapeados em `ENDPOINTS` |
| Executa em toda análise? | Sim, na primeira `call_endpoint` com cache frio |
| Cache atual | **Global** (`permission_cache.py`) — não keyed por `credential_fingerprint` |
| Cold cost | 12,7s (esta medição) / ~20s (BUILD-03B com timeouts) |
| Após warm | 0ms por chamadas subsequentes na mesma sessão |

---

## Requests “duplicadas”

| tipo | count | observação |
|---|---:|---|
| Paginação `VENDA_ITEM` | 60 | **Necessária** (10 páginas × 2 períodos × 3 tenants) |
| `EMPRESAS` intra-análise | 6 | **Redundante** — pode cachear registry + resultado fuel |
| Permission probe calls | 29 (cold) | **Reduzível** — cache por credencial + probe lazy |

`duplicate_request_count` do tracer: 112 — inclui paginação legítima; classificar separadamente.

---

## O que NÃO consome tempo significativo

- Config load: 0ms
- Credential discovery: 0ms  
- Priority score / candidate build: dentro do engine, <1s
- HTTP serialization: 0ms

---

## Implicações para otimização (somente gargalos provados)

| gargalo | estratégia |
|---|---|
| VENDA_ITEM 52s | Cache/snapshot fuel por `tenant+period` (reutilizar `FuelSnapshotService` / `SnapshotStore`) |
| EMPRESAS 17s | Tenant registry TTL + evitar `get_companies` repetido |
| Permission 12s | Cache por `credential_fingerprint`, TTL configurável |
| Home bloqueada | Analysis Snapshot + refresh background |
| Sequencial 86s | Concurrency controlada após teste 429 |

Raw: `docs/performance/PERFORMANCE_01_BASELINE_RAW.json`
