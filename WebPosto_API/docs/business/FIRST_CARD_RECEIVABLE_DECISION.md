# Primeira Observação Card/Receivable — VALUE-04

**Data:** 2026-07-04  
**Estado:** OBSERVATION (confidence 75% < 80%)  
**Tenant:** 11495 — POSTO VIP  
**Detector:** CardReceivableDetector

## Sinal

`OVERDUE_RECEIVABLE` — R$ 2.481,81 em recebíveis vencidos sem evidência de liquidação

## Evidência

| Métrica | Valor |
|---|---:|
| Títulos vencidos | 50 |
| Valor vencido | R$ 2.481,81 |
| Liquidação registrada | R$ 0,00 |
| Reconciliation Level | 1 |
| Fonte expectativa | TITULO_RECEBER |
| Fonte liquidação | pendente/dataPagamento |

## Limitação

Não é gap de cartão TEF — `VENDA_FORMA_PAGAMENTO` vazio no período. Títulos incluem categorias operacionais (DESPERDICIO, PRODUTOS TROCA).

## Money Found

R$ 2.481,81 `ESTIMATED` — ausência de baixa contábil, não perda confirmada.
