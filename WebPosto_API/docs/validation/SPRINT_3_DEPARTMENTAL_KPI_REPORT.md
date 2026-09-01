# Sprint 3 — KPIs e DRE por departamento

**Data:** 2026-07-24  
**Status:** Margem bruta implementada; resultado operacional bloqueado por despesas

## Entregas

- DRE diária por empresa e por departamento.
- Receita, custo da receita, margem bruta e percentual de margem.
- Despesas, resultado operacional e rentabilidade somente quando a cobertura de
  despesas estiver completa.
- Indicadores de Combustíveis: litros, preço médio, custo e margem por litro.
- Indicadores de Conveniência: quantidade de vendas, ticket médio e itens por venda.
- Indicadores de Lubrificantes: unidades vendidas e margem bruta por unidade.
- Unidade, moeda, empresa, período, status, limitações e linhagem em cada linha.
- API: `GET /api/v1/departmental-kpis/dre?empresaCodigo=...&data=AAAA-MM-DD`.

## Validação real — Posto Doze, 2026-07-23

| Departamento | Receita | CMV | Margem bruta | Margem |
|---|---:|---:|---:|---:|
| Combustíveis | R$ 48.871,87 | R$ 41.647,23 | R$ 7.224,64 | 14,78% |
| Conveniência | R$ 0,00 | R$ 0,00 | R$ 0,00 | — |
| Lubrificantes | R$ 211,47 | R$ 153,70 | R$ 57,77 | 27,32% |

Cobertura de vendas e custos: completa. Cobertura departamental das despesas:
incompleta. Por isso, despesas operacionais, resultado operacional e rentabilidade
permanecem nulos; margem bruta não é rotulada como lucro.

## Revisão profissional

Esta DRE é gerencial e parcial. Antes de uso em reporte financeiro formal, deve ser
revisada por profissional financeiro qualificado e conciliada com despesas, tributos,
ajustes e lançamentos de fechamento.
