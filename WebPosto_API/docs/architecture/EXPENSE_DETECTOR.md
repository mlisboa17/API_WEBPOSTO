# ExpenseDetector — VALUE-03

## Objetivo

Detectar **anomalias explicáveis** em despesas reais (WebPosto), não listar despesas.

Pergunta: *existe despesa acima do comportamento de referência que merece atenção?*

## Fontes

| Endpoint | Uso |
|---|---|
| `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` | Lançamentos por categoria (`planoConta`) |
| `/INTEGRACAO/TITULO_PAGAR` | Fornecedor (complementar) |

Service: `NetworkFinancialOverviewService._load_filtered_expenses`, `_fetch_titulo_pagar`

## Anomalias

| Tipo | Critério |
|---|---|
| `CATEGORY_SPIKE` | Categoria +R$ 3.000 e +20% vs baseline 30d |
| `SUPPLIER_SPIKE` | Fornecedor (titulo) acima do baseline |
| `DUPLICATE_PAYMENT_SIGNAL` | Mesma categoria + valor, ≥2 lançamentos — **POSSÍVEL DUPLICIDADE** |

Não implementados nesta sprint: `VALUE_OUTLIER`, `CROSS_TENANT`.

## Baseline

- Período atual: 30 dias até `data_final`
- Baseline: 30 dias imediatamente anteriores
- Confidence: `ConfidenceFactors` (qualidade, comparação, período, cálculo)

## Money Found

Sempre `ESTIMATED`. Linguagem: *"R$ X acima do comportamento de referência"* — nunca perda confirmada.

## Cache

- Dir: `snapshots/discovery_expense`
- Key: `discovery_expense:{tenant_id}:{empresa_codigo}:{start}:{end}`
- TTL: 5 min (período corrente) / 24h (fechado)
- Métricas: `expense_cache_hit_count`, `expense_cache_miss_count`

## Integração

- Herda `BaseDetector`
- Registrado em `owner_analysis_runner`, `decision_discovery` router
- `DETECTOR_SET_SIGNATURE`: `ExpenseDetector,FuelRevenueDetector`
- Compete com `FuelRevenueDetector` no Discovery Engine

## Root Cause

`ExpenseRootCause` → categoria, frequência, tipo de anomalia, recomendações específicas.
