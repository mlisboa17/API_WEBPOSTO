# DW PRESTAÇÃO MODEL — F03.4-B · Agente 9

## Dimensions

| Tabela | Chaves |
|--------|--------|
| `dim_employee_accountability` | funcionario_codigo, saldo, classe_saldo, banda_risco |
| `dim_cash_document` | documento_tipo, filial, turno, pdv, data |

## Facts

| Tabela | Granularidade | Medidas |
|--------|---------------|---------|
| `fact_cash_employee` | operador × turno | falta, sobra, vale, saldo |
| `fact_cash_expense` | despesa × origem | valor, classe_origem, dre_impact |
| `fact_cash_variance` | fechamento × operador | diferenca, rastreabilidade_pct |

## Fontes

Prestação de Contas · CAIXA · CAIXA_APRESENTADO · MOVIMENTO_CONTA · DESPESAS_REDE · Employee Ledger F03.3
