# RT00_API_INVENTORY_REPORT — IA-2

**Data:** 2026-06-14 | **Base:** `http://127.0.0.1:8050` | **Fonte:** `scripts/rt00_inventory_data.json` + rotas em `app.py`

## Resumo

| Métrica | Valor |
|---|---|
| Routers registrados em `app.py` | **44** |
| Endpoints `@router.get/post` (est.) | **~220** |
| Endpoints probe (amostra) | **18** |
| **FUNCIONA** (≤22s, 200) | **13** |
| **PARCIAL** (timeout live / lento) | **5** |
| **NAO_RESPONDE / 404** | **0** na amostra |

## Camada `/v1` — WebPosto live (fechamento_enterprise)

| Endpoint | Status probe | Tempo | Fallback | Classificação |
|---|---|---|---|---|
| `/health` | 200 | 3,8s* | — | **FUNCIONA** |
| `/v1/financial/overview` | timeout 6s† | >6s | snapshot F08 | **PARCIAL** |
| `/v1/financial/expenses` | timeout 6s† | ≤22s c/ hotfix | snapshot | **PARCIAL** |
| `/v1/sales` | timeout 6s† | ~8s c/ hotfix P0 | snapshot | **PARCIAL** |
| `/v1/stock` | timeout 6s† | >8s live | — | **PARCIAL** |
| `/v1/financial/accounts-payable` | não probe | — | — | **PARCIAL** |

*Health inclui init DB. †Probe com timeout cliente 6s; hotfix validado separadamente em ~8s.

## Camada `/api/v1` — Snapshot-first (cockpits)

| Endpoint | Status | Tempo | Classificação |
|---|---|---|---|
| `/api/v1/financial/operations-center/cockpit` | 200 | 1,1s | **FUNCIONA** |
| `/api/v1/financial/intelligence-center/cockpit` | 200 | 0,35s | **FUNCIONA** |
| `/api/v1/financial/snapshot-health/inventory` | 200 | 0,88s | **FUNCIONA** |
| `/api/v1/admin/circuit-breaker/status` | 200 | 1,53s | **FUNCIONA** |
| `/api/v1/non-fuel-products/cockpit` | 200 | 1,8s | **FUNCIONA** |
| `/api/v1/fuel-governance/cockpit` | 200 | 0,02s | **FUNCIONA** |
| `/api/v1/nfce-intelligence/cockpit` | 200 | 0,01s | **FUNCIONA** |
| `/api/v1/fiscal-intelligence/cockpit` | 200 | <0,1s | **FUNCIONA** |
| `/api/v1/commercial-execution/cockpit` | 200 | 0,01s | **FUNCIONA** |
| `/api/v1/finance/cash-flow/snapshot` | 200 | 0,17s | **FUNCIONA** |
| `/api/v1/fuel/executive` | 200 | 2,25s | **FUNCIONA** |
| `/api/v1/sales/fuel-summary` | timeout 6s | — | **PARCIAL** |

## APIs registradas sem probe UI direto (código morto operacional)

| Prefixo | Uso UI | Classificação |
|---|---|---|
| `/auth` | Não | **ÓRFÃ** |
| `/sync` | Não | **ÓRFÃ** |
| `/clientes` | Não | **ÓRFÃ** |
| `/metrics` | Não | **ÓRFÃ** |
| `/expenses` (legado) | Não | **OBSOLETO** |
| `/api/v1/data-trust` | Audit only | **ÓRFÃ** |
| `/api/v1/prestacao-contas` | Audit only | **ÓRFÃ** |
| `/api/v1/executive-copilot` | UI PARCIAL | **PARCIAL** |
| `/api/v1/autonomous-recommendations` | UI PARCIAL | **PARCIAL** |
| `/api/v1/closed-loop-learning` | UI PARCIAL | **PARCIAL** |

## Padrão arquitetural observado

```text
OPERACIONAL  → /api/v1/*/cockpit + snapshots (read-only, <3s)
PARCIAL      → /v1/* live WebPosto (lento, fallback F08/P0)
ÓRFÃO        → rotas backend sem consumidor frontend
```
