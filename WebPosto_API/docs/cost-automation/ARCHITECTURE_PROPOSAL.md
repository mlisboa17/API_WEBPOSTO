# Proposta — atualizador de custos

Fase 1 entregue: propostas read-only. PUT de custo continua sem implementação.

## Fluxo

```
DF-e recebido
 → item por EAN exato
 → custo calculado (mesma política do cadastro)
 → comparação com cadastro
 → CostUpdateProposal
 → política / fila de aprovação
 → PUT controlado
 → GET independente
 → histórico
```

## Requisitos

- Idempotência por EAN + chave mascarada + valor.
- Guardar custo anterior e novo, variação percentual e margem.
- Atualização automática só dentro de limites configuráveis.
- Fora do limite: fila de aprovação.
- Rollback lógico = nova atualização compensatória. Histórico nunca é apagado.

## Contratos

`CostUpdateCandidate`, `CostUpdateProposal`, `CostUpdatePolicy`, `CostUpdateGateway`, `CostUpdateVerifier`.
