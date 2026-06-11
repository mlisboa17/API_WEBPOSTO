# CASH NULL ROOT CAUSE — P0 · IA-1

## Erro reproduzido

```text
TypeError: bad operand type for unary -: 'NoneType'
```

Origem: `_operator_analytics()` · `sorted(..., key=lambda x: (-x.get("cashRiskScore") or 0, ...))`

Quando `cashRiskScore=None`, Python avalia `-None` **antes** do `or 0`.

## Pontos corrigidos

| Local | Padrão inseguro | Correção |
|-------|-----------------|----------|
| `_operator_analytics` | `-x.get("cashRiskScore")` | `safe_float()` |
| Rankings risk/pdv | `x["score"]` direto | `safe_float(x.get("score"))` |
| Alertas sort | `-a["diferencaAbsoluta"]` | `safe_float()` |
| Critical entities | `-x["diferencaAbsoluta"]` | `safe_float()` |
