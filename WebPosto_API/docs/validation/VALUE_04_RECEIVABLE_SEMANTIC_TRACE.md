# VALUE-04 — Semantic Trace (Recebíveis)

**Data:** 2026-07-04 | Evidência: `VALUE_04_CARD_RECEIVABLE_RAW.json`

## Classificação por fonte

| Fonte | Representa | Classificação |
|---|---|---|
| `VENDA_FORMA_PAGAMENTO` | Pagamento informado na venda (POS) | **SOURCE_OF_EXPECTATION** (quando disponível) |
| `TITULO_RECEBER` | Obrigação financeira a receber (cliente/prazo/frotista) | **SOURCE_OF_EXPECTATION** + **SOURCE_OF_SETTLEMENT** (via `pendente`/`dataPagamento`) |
| `MOVIMENTO_CONTA` | Movimento bancário (crédito/débito) | **SOURCE_OF_BANK_MOVEMENT** (evidência complementar, não prova TEF) |
| `vendaCodigo` em titulo | Ligação fraca venda↔título | **SUPPORTING_EVIDENCE** (não prova cartão) |
| NSU / bandeira / adquirente | — | **UNUSABLE_FOR_RECONCILIATION** (ausente) |

## Semântica comprovada

**Venda ≠ recebível.** Titulos incluem clientes como "DESPERDICIO", "F.J. SERVICOS" — não são liquidações de adquirente.

**Recebível ≠ dinheiro recebido.** `pendente=true` + vencimento passado = sem evidência de liquidação contábil.

**Baixa contábil ≠ movimento bancário.** `MOVIMENTO_CONTA` tem créditos (R$ 3.935 VIP / R$ 6.820 Doze) mas sem match 1:1 com titulos.

## Amostras sanitizadas

**POSTO VIP (11495):** 51 titulos pendentes, 50 vencidos, R$ 2.481,81 vencido — clientes operacionais (DESPERDICIO, PRODUTOS TROCA).

**POSTO DOZE (74014):** 2 vencidos R$ 3.263,51 — F.J. SERVICOS E COMERCIO LTDA (frotista/prazo, não cartão TEF).

**AP CASA CAIADA (5555):** zero registros nas 3 fontes no período.
