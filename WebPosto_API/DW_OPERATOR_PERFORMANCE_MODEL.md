# DW OPERATOR PERFORMANCE MODEL — F03.4

## Facts

| Tabela | Granularidade | Medidas |
|--------|---------------|---------|
| `fact_operator_performance` | operador × dia | score, dif_acum, recorrência, risk, saldo_ledger |
| `fact_pdv_performance` | pdv × dia | score, dif_total, recorrência, risk |
| `fact_turn_performance` | turno × dia | score, volume, dif, recorrência, risco |

## Dimensions

| Dimensão | Chaves |
|----------|--------|
| `dim_operator` | funcionario_codigo, banda, filial |
| `dim_pdv` | pdv_codigo, empresa_codigo |
| `dim_turn` | turno_codigo, turno_label |
| `dim_performance_band` | banda, faixa_min, faixa_max |

## Fontes

CAIXA · CAIXA_REDE · Employee Cash Ledger · Cash Operations · Cash Risk Score
