# Atualizador de custos por DF-e

Fase 1: motor **read-only** de propostas. Não há PUT.

Empresa desta fase: **118508 — CONVENIÊNCIA 24 HORAS**.

## Fluxo

```
DF-e local
 → CostEvidenceResolver (EAN exato, mesma fórmula do cadastro)
 → GET PRODUTO + PRODUTO_EMPRESA
 → comparação Decimal
 → CostUpdateProposal
 → revisão humana
 → futura aprovação
 → futuro PUT /INTEGRACAO/ALTERAR_PRODUTO/{id}
 → futura verificação GET independente
```

Proposta não é aprovação. Custo e margem ficam na trilha de auditoria.

## O que esta fase não faz

- Não escreve no WebPosto.
- Não consulta SEFAZ se o XML já está no `data/dfe_store`.
- Não altera preço de venda.
- Não cadastra produto.
- Não integra IA.

## CLI

```bash
python scripts/cost_update_118508.py scan
python scripts/cost_update_118508.py propose
python scripts/cost_update_118508.py status
```

`--execute` sai com `COST_UPDATE_WRITES_NOT_IMPLEMENTED`.
