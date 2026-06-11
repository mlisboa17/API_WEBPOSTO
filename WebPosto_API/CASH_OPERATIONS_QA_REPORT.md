# CASH OPERATIONS QA REPORT — F03

**Status paridade:** **APROVADO**

## Critério

```
Valor Base = Snapshot = API = UI = Export CSV
Margem aceitável: R$ 0,00
```

## Resultados

| Check | Resultado |
|-------|-----------|
| Paridade base ↔ snapshot | OK |
| TTL 300s | OK |
| Pesos risk score | OK (soma 1.0) |
| Performance total | 25225.7 ms |

## Falhas

- Nenhuma divergência decimal detectada.

## Evidência

Arquivo: `scripts/f03_cash_operations_qa.json`
