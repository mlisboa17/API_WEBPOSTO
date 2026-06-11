# EXPENSES FILTER FIX REPORT

## Filtros validados

| Parâmetro | Backend | Frontend | Regra |
|-----------|---------|----------|-------|
| `dataInicial` | ✅ | ✅ | Intervalo inclusivo |
| `dataFinal` | ✅ | ✅ | Intervalo inclusivo |
| `empresaCodigo` | ✅ multiselect | ✅ MultiSelectLogos | Vírgula = OR |
| `origem` | ✅ `_expense_matches` | ✅ select Todos/Financeiro/Caixa/PDV | Vazio = todas |
| `categoria` | ✅ via `categoria_logos` | ✅ coluna + filtro tabela | Vazio = todas |
| `texto` | ✅ **novo** | ✅ campo Texto | Vazio = todas |
| `valorMin/Max` | ✅ | ✅ | Numérico |
| `centroCusto` | ✅ contains | ✅ | Parcial |
| `tipoDespesa` | ✅ | ✅ | Parcial |

## Filtros indevidos removidos / ausentes

- ❌ Nenhum filtro hardcoded por `financeiro`, `desconhecido`, `BOBINA TERMICA` no backend.
- ✅ `origem` vazio → traz financeiro + caixa + pdv.
- ✅ `texto` vazio → traz todas as descrições.
- ✅ Limpar filtros (`clearFilters`) zera `origem` e `texto`.

## Arquivos alterados

- `network_financial_overview_service.py` — `_expense_matches` + `FinancialOverviewFilters.texto`
- `fechamento_enterprise.py` — query `texto`
- `frontend/components/filters.js` — origem + texto
- `frontend/services/api.js` — repasse parâmetros

## Comportamento esperado

Sem filtros opcionais selecionados → **todas** as origens e categorias do período/filial.
