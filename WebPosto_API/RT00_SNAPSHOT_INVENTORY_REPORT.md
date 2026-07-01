# RT00_SNAPSHOT_INVENTORY_REPORT — IA-4

**Data:** 2026-06-14 | **Diretório:** `snapshots/` | **Total:** 167 arquivos JSON em **42 kinds**

## Resumo por status

| Status | Kinds | Descrição |
|---|---|---|
| **ATIVO** | 18 | Consumidos por UI/API homologados |
| **PARCIAL** | 14 | Existem, refresh irregular ou QA-only |
| **OBSOLETO** | 10 | Duplicatas, audit-only, legado |

## Snapshots ATIVOS (consumo operacional confirmado)

| Kind | Arquivos | Consumidor | Lineage | Atualiza |
|---|---|---|---|---|
| `financial` | 18 | F08.0–F08.4, `/v1` fallback | expenses sim | Scheduler F08.2 |
| `executive` | 19 | executiveWorkspace, scorecard | parcial | Manual/scheduler |
| `non_fuel_products` | 7 | commercial views | sim F07 | Snapshot service |
| `commercial_execution` | 6 | commercialExecution | sim | Snapshot service |
| `commercial_learning` | 6 | commercialLearning | sim | Snapshot service |
| `commercial_copilot` | 1 | commercialCopilot | sim | Snapshot service |
| `fuel_governance` | 5 | fuelGovernance | sim | Snapshot service |
| `nfce_intelligence` | 5 | nfceIntelligence | sim | Snapshot service |
| `fiscal_intelligence` | 1 | fiscalIntelligence | sim | Snapshot service |
| `fiscal_reconciliation` | 1 | fiscalReconciliation | sim | Snapshot service |
| `lmc_intelligence` | 1 | lmcIntelligence | sim | Snapshot service |
| `cash_flow` | 4 | cashFlow view | não | TTL 5min |
| `cash_operations` | 14 | cashOperations | parcial | Snapshot service |
| `finance_center` | 10 | financeCenter | parcial | Snapshot service |
| `operator_performance` | 5 | operatorPerformance | sim | Snapshot service |
| `benchmark_intelligence` | 5 | benchmark | sim | Snapshot service |
| `executive_scorecard` | 5 | executiveScorecard | sim | Snapshot service |
| `product_master_cache` | 1 | F07 enrichment | N/A | Cache 24h |

## Snapshots PARCIAL (existem, uso limitado)

| Kind | Nota |
|---|---|
| `expense_lineage` | F08 enrichment, não UI direta |
| `expense_semantic` | Bootstrap F08.0 |
| `employee_ledger` | API snapshot endpoint |
| `people_intelligence` | Motor strip |
| `operator_profitability` | Motor strip |
| `goals_campaign_engine` | goalsCampaign |
| `management_action_center` | managementAction |
| `action_center` | actionCenter |
| `fuel` | Combustível analytics |
| `cash_operations_qa` | QA only |
| `operator_performance_audit` | Audit only |
| `prestacao_contas_audit` | Audit only |
| `coverage_truth_audit` | Audit only |
| `data_trust_baseline` | D04 audit |

## Snapshots OBSOLETO / órfãos

| Kind | Motivo |
|---|---|
| `executive_ai_copilot` | UI PARCIAL, sem homologação |
| `autonomous_recommendation_engine` | F05 experimental |
| `closed_loop_learning_engine` | F05 experimental |
| `corporate_intelligence_hub` | Motor sem aba |
| `executive_decision_engine` | Motor sem aba |
| `store_shift_profitability` | operationRoi motor |
| `operator_intelligence` | Duplicata F04 |
| `executive_coverage_recovery` | One-off |
| `snapshot_20260601_20260607.json` | Arquivo solto na raiz |
| `snapshot_20260606.json` | Arquivo solto na raiz |

## Kinds financeiros F08 (homologados)

```text
financial_overview
financial_expenses
financial_receivables
financial_payables
financial_sales  ← HOTFIX P0
```

Período homologado principal: `2026-06-01 → 2026-06-07` e rolling `2026-06-09 → 2026-06-14`.

## Evidência refresh

- `_executions.jsonl` em `snapshots/financial/` — histórico scheduler F08.2
- `_retention_removed.jsonl` — retenção 30 dias ativa
