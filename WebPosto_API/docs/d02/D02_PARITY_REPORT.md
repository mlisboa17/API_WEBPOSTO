# D02 — Parity Report (Agente 9)

> Paridade **expectativa Prestação/PDF × API WebPosto** — não recebimento externo. [D02_CONCEPTUAL_CORRECTION.md](./D02_CONCEPTUAL_CORRECTION.md)

## Caso de teste

| Campo | Valor |
|---|---|
| Filial | POSTO VIP (11495) |
| Período | 29/06/2026 – 05/07/2026 |

## Referência Prestação (oráculo — script QA, não app)

| Métrica | Referência PDF |
|---|---|
| Apresentado | R$ 191.420,46 |
| Sangria | R$ 41.436,00 |
| Apurado | R$ 217.005,34 |
| Diferença total | R$ -25.584,88 |

### Divergências por natureza (referência)

| Natureza | Diferença ref. |
|---|---|
| Dinheiro | -9.943,52 |
| Notas | -4,61 |
| Cartão | -8.235,12 |
| Despesa | -236,00 |
| Vale Funcionário | -2.733,41 |
| Transferência Crédito | -4.432,22 |

## Execução

```bash
python scripts/audit_d02_parity_vip.py
```

Saída: `docs/d02/D02_PARITY_RUN.json` (gerado em runtime contra API live).

## Classificação de gaps

| Gap | Impacto |
|---|---|
| Dataset VIP parcial (10/28 dias histórico) | paridade período longo |
| VFP vazio cartão TEF VIP 30d | decomposição cartão LEVEL 1 |
| Sangria vs depósito bancário | dinheiro — evidência parcial |
| Adquirente/bandeira sem NSU | cartão — UNKNOWN adm |

## Critério

Match centavo a centavo quando `|delta| ≤ R$ 0,05` entre API e referência externa.
