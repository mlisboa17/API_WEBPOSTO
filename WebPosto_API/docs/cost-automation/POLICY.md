# Política de proposta de custo

Versão `1.0.0`. Limites ficam aqui, não espalhados em scripts.

## Evidência

- EAN exato.
- Destinatário `02080237000155`.
- NF-e autorizada (`cStat=100`), não cancelada, mais recente.
- Fórmula única em `dfe_cost_resolver.compute_unit_cost` (Decimal).
- Sem fator inventado para KG, CX, FARDO ou DISPLAY.

## Classificação

| Status | Quando |
| --- | --- |
| PROPOSED | ativo em 118508, EAN ok, DF-e válido, custo > 0, diferença relevante, sem risco de bloqueio/revisão |
| NO_CHANGE | \|Δ\| < R$ 0,01 ou variação ≤ tolerância percentual |
| DFE_NOT_FOUND | nenhum DF-e válido pelo EAN |
| REVIEW_REQUIRED | custo > venda, Δ > ±30% (se custo atual > 0), margem < 0 ou abaixo do mínimo, conversão incomum, conflito NCM/CEST, múltiplos itens |
| BLOCKED | empresa errada, EAN diverge, inativo, nota inválida, quantidade indeterminável, custo ≤ 0, GET ambíguo |

Custo atual zero para custo positivo **não** dispara a regra de +30%.

## Futuro PUT

Pesquisa em código existente: `PUT /INTEGRACAO/ALTERAR_PRODUTO/{id}` com `precoCusto` (`ProdutosEndpoints.atualizar`, `produto_crud`). Não testado nesta fase.
