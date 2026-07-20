# D02 — Payment Normalization (Agente 2)

> [D02_CONCEPTUAL_CORRECTION.md](./D02_CONCEPTUAL_CORRECTION.md)

## Regra POS/TEF (crítica)

| Conceito | Tratamento |
|---|---|
| POS | `CaptureOrigin.POS_MANUAL` — lançamento manual na operação |
| TEF | `CaptureOrigin.TEF` — captura eletrônica pinpad |
| Natureza financeira | CREDIT / DEBIT / DIGITAL_WALLET / PIX etc. via `PaymentNatureCode` |

**Proibido:** natureza `POS`, saldo POS, conta POS, conferência POS isolada.

## Taxonomia implementada

- `src/domain/reconciliation/models.py` — enums `PaymentNatureCode`, `CaptureOrigin`, `ExpectedDestination`
- `src/domain/reconciliation/payment_normalization.py` — mapeamento CAIXA_APRESENTADO + inferência VFP

## Mapeamento CAIXA_APRESENTADO → Natureza

| PaymentNatureCode | Campos API |
|---|---|
| DINHEIRO | dinheiroApresentado/Apurado/Diferenca |
| NOTAS | notaPrazo* |
| CHEQUE_VISTA | cheque* |
| CHEQUE_PRE | chequePre* |
| CARTAO | cartao* |
| … | ver `NATURE_FIELD_MAP` |

## Inferência de origem

```text
"TEF" / "PINPAD"           → CaptureOrigin.TEF
"POS" / "MANUAL"           → CaptureOrigin.POS_MANUAL
"TRANSF" / "PIX"           → CaptureOrigin.BANK_TRANSFER
default com label          → CaptureOrigin.INTERNAL ou UNKNOWN
```

## Destino financeiro esperado

Cada natureza possui `ExpectedDestination` (CASH, BANK_ACCOUNT, ACQUIRER_RECEIVABLE, …) — ver `EXPECTED_DESTINATION` no código.
