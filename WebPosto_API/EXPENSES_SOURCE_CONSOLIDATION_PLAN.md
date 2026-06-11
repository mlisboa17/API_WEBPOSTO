# EXPENSES SOURCE CONSOLIDATION PLAN

## Objetivo

Listar todas as despesas da filial/período **sem somar fatos incompatíveis**, separando `origem`.

## Fontes e mapeamento

| Fonte WebPosto | Endpoint key | Origem UI | Valor principal |
|----------------|--------------|-----------|-----------------|
| `DESPESAS_FINANCEIRO_REDE` | `despesas_financeiro_rede` | `financeiro` | `valor` / `descricaoDocumento` |
| `CAIXA_APRESENTADO` | `caixa_apresentado` | `caixa` | `despesaApresentado` (via merge) |
| `CAIXA_APRESENTADO_REDE` | `caixa_apresentado_rede` | `caixa` | idem |
| `CAIXA_REDE` | `caixa_rede` | `pdv` | `despesaApurado` (via merge) |
| `CAIXA` | `caixa` | `pdv` | idem |

## Algoritmo (`_load_screen_expenses`)

1. Buscar financeiro (1× rede).
2. Buscar caixa + apresentado paginados (paralelo).
3. Montar `ap_map[(empresaCodigo, caixaCodigo)]`.
4. Para cada fechamento caixa:
   - `origem=caixa` se `despesaApresentado > 0`
   - `origem=pdv` se `despesaApurado > 0`
5. Classificar categoria (LOGOS v3 para financeiro; `OPERACIONAL` para caixa/pdv).
6. `matchFinanceiro` por chave `(empresa, data, valor)`.
7. Dedupe por `(origem, empresa, data, valor, caixaCodigo, pdvCodigo, funcionarioCodigo, descricao)`.

## Campos expostos

`data`, `valor`, `descricao`, `filial`, `origem`, `categoria`, `planoConta`, `centroCusto`, `caixaCodigo`, `pdvCodigo`, `funcionarioCodigo`, `matchFinanceiro`, `fonte`.

## Regras preservadas

- `_load_filtered_expenses()` **não alterado** → overview / DRE / Finance Center intactos.
- Totais por origem em `resumoPorOrigem` — **não** soma cross-origem no consolidado financeiro.

## Implementação

- `src/services/network_financial_overview_service.py` — `_load_screen_expenses`, normalizers, match engine.
- `get_financial_expenses()` passou a usar screen loader.
