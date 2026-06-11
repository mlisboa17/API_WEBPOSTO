# OPERATOR COCKPIT — F04.0 · Agente 9

Rota UI: `view=operator-performance`

## Widgets

| Widget | Fonte |
|--------|-------|
| Top Operadores | productivityEngine.top 10 |
| Operadores Críticos | operatorRiskEngine (band Critico) |
| Vendas | salesPerformance |
| Descontos | discountIntelligence |
| Risco | operatorRiskEngine |
| Accountability | cashAccountability |

API: `GET /api/v1/operator-intelligence/cockpit`

Top operadores (amostra):

| Operador | Score | Banda |
|---|---|---|
| APOIO LOJA . | 66.06 | NORMAL |
| WANDERSON GUILHERME DOS SANTOS OLIV | 64.25 | NORMAL |
| RICART ABEL DE PAIVA RIBEIRO | 60.93 | NORMAL |
| MARINALDO RIBEIRO DA SILVA | 46.88 | BAIXA |
| LUCIANO PEREIRA DA SILVA JUNIOR | 46.16 | BAIXA |
