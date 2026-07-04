# VALUE-03 — Expense Data Survey

**Data:** 2026-07-04  
**Escopo:** WebPosto_API (backend real). Sem mocks.

## Fontes WebPosto mapeadas

| Endpoint WebPosto | Key gateway | Service | Arquivo |
|---|---|---|---|
| `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` | `despesas_financeiro_rede` | `NetworkFinancialOverviewService._fetch_despesas_rede` | `network_financial_overview_service.py` |
| `/INTEGRACAO/TITULO_PAGAR` | `financeiro` | `NetworkFinancialOverviewService._fetch_titulo_pagar` | idem |
| `/INTEGRACAO/MOVIMENTO_CONTA` | `movimento_conta` | `WebPostoClient` | `webposto_client.py` |
| `/INTEGRACAO/CONTA` | `conta` | fallback financeiro | idem |
| Caixa/fechamento | — | `_load_screen_expenses` | idem (derivado) |

## Serviços reutilizáveis

| Service | Uso |
|---|---|
| `NetworkFinancialOverviewService._load_filtered_expenses` | Despesas normalizadas por tenant (`empresaCodigo` no row) |
| `NetworkFinancialOverviewService._normalize_expense` | valor, data, planoConta, centroCusto, tipoDespesa, status |
| `NetworkFinancialOverviewService._normalize_titulo_pagar` | fornecedor, vencimento, valor, situacao |
| `ExpenseSemanticService` | Classificação operacional/financeira (derivado) |
| `ExpensesService.get_periodo` | TITULO_PAGAR simplificado |
| `analytics_service.get_dre` | DRE agregado (derivado) |

## Campos por despesa (CONSULTAR_DESPESAS_FINANCEIRO_REDE)

| Campo | Disponível |
|---|---|
| tenant/empresaCodigo | SIM (filtro client-side) |
| período | SIM (dataInicial/dataFinal obrigatórios) |
| paginação | NÃO (payload único; dedupe interno) |
| categoria | SIM (`planoConta` / planoContaGerencial) |
| fornecedor | PARCIAL (mais forte em TITULO_PAGAR) |
| valor | SIM |
| data | SIM |
| status | SIM |
| documento/NF | PARCIAL (`descricaoDocumento` raw) |
| centro de custo | SIM |
| forma pagamento | NÃO direto neste endpoint |
| origem | SIM (`origem`) |

## Respostas (1–18)

1. **Endpoint direto de despesas?** SIM — `CONSULTAR_DESPESAS_FINANCEIRO_REDE`
2. **Contas a pagar?** SIM — `TITULO_PAGAR` (`financeiro`)
3. **Histórico de pagamentos?** PARCIAL — titulo + movimento_conta
4. **Fornecedor?** SIM em TITULO_PAGAR; limitado em despesas rede
5. **Categoria?** SIM — plano de contas / classificador v3
6. **Centro de custo?** SIM
7. **DRE?** SIM — derivado (`analytics_service`)
8. **Despesa operacional?** SIM — via semantic/screen expenses
9. **Despesa por posto?** SIM — `empresaCodigo` nos rows
10. **Baseline histórico?** SIM — comparar 30d vs 30d anteriores
11. **Período atual vs anterior?** SIM
12. **Comportamento histórico?** SIM — média/contagem por categoria
13. **Aumento por categoria?** SIM
14. **Aumento por fornecedor?** SIM (titulo)
15. **Pagamento duplicado?** SINAL POSSÍVEL — mesma categoria/valor/datas próximas
16. **Valor fora do padrão?** SIM — outlier vs mediana da categoria
17. **Recorrência anormal?** SIM — contagem vs baseline
18. **Rastreabilidade?** SIM — endpoint + raw row em metadata

## Limitações reais

- `despesas_financeiro_rede` retorna rede; filtro por posto é client-side.
- Fornecedor fraco no endpoint principal; titulo complementa.
- Sem paginação oficial — volume limitado ao retorno WebPosto.
- Caixa/pista mistura movimentações operacionais — semantic filter recomendado.
