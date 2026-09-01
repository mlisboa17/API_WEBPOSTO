# D02 — Card Reconciliation (Agente 3)

> Decomposição interna VFP/TEF/POS — **não** liquidação adquirente. [D02_CONCEPTUAL_CORRECTION.md](./D02_CONCEPTUAL_CORRECTION.md)

## Decomposição obrigatória

| Dimensão | Fonte | Gap |
|---|---|---|
| crédito/débito | `nomeFormaPagamento` / heurística | OK agregado |
| origem TEF/POS | label + `tipoFormaPagamento` | OK metadado |
| bandeira | heurística (VISA, ELO, …) | parcial |
| adquirente | `administradoraCodigo` ou hint no label | **UNKNOWN** se ausente |
| taxa | `taxaPercentual` (VFP) | 73,9% cobertura amostra |
| liquidação | `vencimento` (VFP) | parcial |
| conta destino | — | **gap** — próxima camada bancária |

## Normalização

- `src/domain/reconciliation/card_normalization.py`
- `normalizedAcquirer = UNKNOWN` quando sem `administradoraCodigo` e sem hint bancário
- Nunca inventar adquirente

## Labels observados (Prestação)

AMERICAN EXPRESS, ELO CREDITO, ELO DEBITO, MAESTRO, MASTERCARD, VISA CREDITO, VISA ELECTRON, variantes ITAU.

## Nível atual

**LEVEL 1+** — decomposição por label agregado (sem NSU). Alinhado a VALUE-04 `reconciliation_level=1`.
