# EXPENSES TABLE UI REPORT

## Colunas implementadas

| Coluna | Campo API |
|--------|-----------|
| Data | `data` |
| Valor | `valor` |
| Descrição | `descricao` |
| Empresa | `filial` |
| Origem | `origem` |
| Categoria | `categoria` |
| Plano Conta | `planoConta` |
| Centro Custo | `centroCusto` |
| PDV | `pdvCodigo` |
| Operador | `funcionarioCodigo` |
| Status Match | `matchFinanceiro` (Sim/Não) |

## Filtro Origem (barra global)

```text
Todos | Financeiro | Caixa | PDV
```

Enviado como `origem` na query string.

## Totais

- **Total filtrado:** soma coluna Valor na tabela (`renderTable` sum).
- **Total da página:** paginação `{ page, limit, total }` da API.
- **Resumo por origem:** linha `expense-origin-summary` acima da tabela (`resumoPorOrigem`).

## Export CSV/PDF

- Mesma fonte `payload.data` da tabela → paridade estrutural garantida.
- `exportName`: `despesas_{data}`.
- `pdfDescription` atualizado para mencionar multi-origem.

## Arquivo

- `frontend/pages/expenses.js` — colunas + resumo origem.
