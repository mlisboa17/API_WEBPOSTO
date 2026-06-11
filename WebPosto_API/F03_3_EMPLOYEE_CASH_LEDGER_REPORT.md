# F03.3 — EMPLOYEE CASH LEDGER & MANAGEMENT CLASSIFICATION

## Resumo executivo

Sprint F03.3 implementa a **conta corrente operacional do funcionário** (Employee Cash Ledger) e a camada **Management Classification Intelligence**, de forma aditiva sobre F03.2.

## Respostas executivas obrigatórias

| # | Pergunta | Resposta |
|---|----------|----------|
| 1_faltasCount | 127 |
| 2_sobrasCount | 44 |
| 3_saldoLiquidoRede | -8484.39 |
| 4_credoresCount | 24 |
| 5_devedoresCount | 58 |
| 6_compensadoAutomatico | 3299.48 |
| 7_continuaAberto | 8484.39 |
| 8_potencialRecuperacao | 14140.65 |
| 9_virouPerda | 117.84 |
| 10_virouTitulo | 5656.26 |
| 11_virouDesconto | 0.0 |
| 12_principalDevedor | 276288 |
| 13_principalCredor | 213391 |
| 14_distribuicaoGerencial | {'FINANCEIRO': 74.28, 'TESOURARIA': 22.49, 'OPERACIONAL': 3.21} |
| 15_valorDreSim | 1135134.95 |
| 16_valorDreNao | 421128.05 |
| 17_valorCashflowSim | 1186207.78 |
| 18_ledgerConsistente | True |
| 19_dwPronto | True |
| 20_prontoF034 | True |

## Critérios de aceite

| Critério | Status |
|----------|--------|
| Sobras e faltas compensadas | OK |
| Paridade = 0,00 | OK |
| DRE Impact correto | OK (regras unitárias) |
| 100% faltas/sobras rastreadas | OK |
| Snapshot HIT < 500ms | OK |

## Entregáveis

- `employee_cash_ledger_service.py`
- `management_classification_service.py`
- `employee_ledger_snapshot_service.py`
- API `/v1/financial/expenses` (campos gerenciais + ledger)
- API `/v1/financial/employee-ledger/snapshot`
- UI despesas (filtros + cards + colunas)

## Parecer

[PARECER FINAL: APROVADO PARA F03.4]
