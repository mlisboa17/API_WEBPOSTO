# RT00_GHOST_FEATURES_REPORT — IA-7

**Data:** 2026-06-14 | **Princípio:** código existente ≠ operacional

## FANTASMA (código completo, zero uso operacional)

| Item | Evidência | Classificação |
|---|---|---|
| `src/presentation/app.py` | Gateway Adelaide paralelo porta 8050, DEPRECATED docs | **FANTASMA** |
| `logos-webposto-gateway/` | Subprojeto duplicado 8050 | **FANTASMA** |
| `/auth`, `/sync`, `/clientes` routes | Registrados em app.py, sem UI | **FANTASMA** |
| `financialMonitoring` + `financialOperations` views | Duplicam F08.3/F08.4 centros | **FANTASMA** |
| `scripts/audit_*.py` (40+) | QA gates, não runtime | **FANTASMA** (esperado) |

## ÓRFÃO (backend sem consumidor UI)

| API / Serviço | Router | UI |
|---|---|---|
| `data_trust_baseline` | `/api/v1/data-trust` | Nenhuma |
| `prestacao_contas` | `/api/v1/prestacao-contas` | Nenhuma |
| `statements` | `/api/v1/finance/statements` | Nenhuma |
| `metrics` | `/metrics` | Nenhuma |
| `gateway_expenses` | gateway | Nenhuma |
| `auditoria.py` | routes | Nenhuma |
| `closed_loop_learning_engine` | API + snapshot | learning view PARCIAL |
| `autonomous_recommendation_engine` | API + snapshot | recommendations PARCIAL |

## OBSOLETO (substituído ou legado)

| Item | Substituído por |
|---|---|
| `FinancialOperationalSnapshotService` (TTL 5min) | F08.0 FinancialSnapshotService |
| Views `financialMonitoring` / `financialOperations` | F08.3 / F08.4 centers |
| `expenses` router `/expenses` | `/v1/financial/expenses` |
| Snapshot soltos na raiz `snapshots/*.json` | Kinds estruturados |
| Motor `dashboard` live-first | Snapshot executive |

## Branch / escopo nunca integrado (git)

| Evidência | Status |
|---|---|
| F08.4 commit com 12 arquivos fora escopo (snapshots cash_flow, operator_performance, etc.) | Contaminado, consumo indireto |
| Pytest.ini vs audit `--no-cov` conflito | Config, não runtime |

## Telas sem menu (motor strip only)

Views acessíveis só via motor strip inferior, não via abas UX-01:

```text
benchmark, corporateHub, executiveDecision, executiveCopilot,
recommendations, learning, operatorPerformance, peopleIntelligence,
peopleRoi, operationRoi, managementAction, fuelExecutive
```

Classificação: **ÓRFÃO de navegação primária** (acessível, mas oculto)

## Resumo

| Classificação | Itens estimados |
|---|---|
| FANTASMA | 8 |
| ÓRFÃO | 12 |
| OBSOLETO | 6 |
