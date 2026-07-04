# CardReceivableDetector — VALUE-04

## Objetivo

Detectar gaps entre **expectativa de recebível** e **evidência de liquidação contábil**, sem confundir venda/baixa/movimento bancário.

## Reconciliation Level

**LEVEL 1 — AGGREGATE SIGNAL** (ver `CARD_RECONCILIATION_CAPABILITY.md`)

## Fontes

| Papel | Endpoint |
|---|---|
| Expectativa | `/INTEGRACAO/TITULO_RECEBER` |
| Liquidação contábil | `/INTEGRACAO/TITULO_RECEBER` (`pendente`, `dataPagamento`) |
| Cartão POS (quando disponível) | `/INTEGRACAO/VENDA_FORMA_PAGAMENTO` |
| Movimento bancário (suporte) | `/INTEGRACAO/MOVIMENTO_CONTA` |

## Sinais

| Signal | Condição |
|---|---|
| `OVERDUE_RECEIVABLE` | Títulos vencidos, `pendente=true`, gap ≥ R$ 2.000 |
| `DUPLICATE_SETTLEMENT_SIGNAL` | Mesmo cliente/valor/vencimento ≥2x |
| `EXPECTED_VS_SETTLED_GAP` | Só se houver dados cartão + gap agregado |

## Confidence (LEVEL 1)

```
data_quality × record_volume × reconciliation_level_factor × overdue_factor
Cap: 0.92 — LEVEL 1 raramente ≥ 80% → OBSERVATION
```

## Money Found

Sempre `ESTIMATED`. Linguagem: *"sem evidência de liquidação"* — nunca *"não recebido"* confirmado.

## Cache

`snapshots/discovery_receivable` — key `discovery_receivable:{tenant}:{empresa}:{start}:{end}`
