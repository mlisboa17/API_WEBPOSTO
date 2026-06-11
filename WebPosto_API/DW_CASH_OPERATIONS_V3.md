# DW CASH OPERATIONS V3 — F03

**Status:** DDL físico implantado (`dw/ddl/`)

## Star Schema

### Facts

| Tabela | Grain |
|--------|-------|
| `fact_cash_closing` | caixaCodigo + dataMovimento |
| `fact_cash_component` | closing + component_code |
| `fact_cash_alert` | alerta por closing |
| `fact_cash_risk` | entity + date snapshot |

### Dimensions

| Tabela | NK |
|--------|-----|
| `dim_operator` | funcionarioCodigo |
| `dim_pdv` | pdvCodigo |
| `dim_turn` | turnoCodigo + turno_nome |
| `dim_cash_date` | data_movimento |

## Arquivos DDL

- `dw/ddl/fact_cash_closing.sql`
- `dw/ddl/fact_cash_component.sql`
- `dw/ddl/fact_cash_alert.sql`
- `dw/ddl/fact_cash_risk.sql`
- `dw/ddl/dim_operator.sql`
- `dw/ddl/dim_pdv.sql`
- `dw/ddl/dim_turn.sql`
- `dw/ddl/dim_cash_date.sql`
