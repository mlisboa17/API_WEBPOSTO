# NEXT EXECUTIVE VALUE — Ranking de Oportunidades

Critério de seleção: **VALUE = MONEY × EVIDENCE × ACTIONABILITY**

Período: **2026-06-05 a 2026-07-04**

---

## RANK 1

**PROBLEM:** NF de fornecedor sem histórico no baseline (SOUZA CRUZ)  
**TENANT:** 11495 (POSTO VIP)  
**FINANCIAL_EXPOSURE:** R$ 5.979,47  
**MONEY_TYPE:** ESTIMATED  
**EVIDENCE:** `REF NF:001872693 - SOUZA CRUZ LTDA.` — 1 lançamento, baseline R$ 0, confidence calculada 90,2% com rastreio de NF  
**CONFIDENCE_ESTIMATE:** 0,90  
**DIRECTOR_ACTION:** Conferir NF 001872693, pedido e recebimento de mercadoria; comparar preço com compras anteriores do fornecedor  
**WHY_LOGOS_ADDS_VALUE:** ExpenseDetector descarta o sinal (confidence 46% por lançamento único). Diretor não vê compra nova de quase R$ 6k na VIP  
**IMPLEMENTATION_COST:** Baixo — detector especializado reutilizando bundle de despesas + root cause NF

---

## RANK 2

**PROBLEM:** Vale de consolidação de caixa acima do baseline  
**TENANT:** 74014 (POSTO DOZE FILIAL II)  
**FINANCIAL_EXPOSURE:** R$ 7.501,00  
**MONEY_TYPE:** ESTIMATED  
**EVIDENCE:** 16 lançamentos vs 7 no baseline; categoria já coberta por ExpenseDetector (winner atual)  
**CONFIDENCE_ESTIMATE:** 0,89  
**DIRECTOR_ACTION:** Revisar os 16 vales de consolidação e confrontar com fechamentos de turno  
**WHY_LOGOS_ADDS_VALUE:** Já exibido — mantém prioridade global por valor maior  
**IMPLEMENTATION_COST:** N/A (já implementado)

---

## RANK 3

**PROBLEM:** Recebíveis vencidos com concentração em um cliente  
**TENANT:** 74014  
**FINANCIAL_EXPOSURE:** R$ 3.263,51 (66% em F.J. SERVICOS E COMERCIO LTDA.)  
**MONEY_TYPE:** AT_RISK  
**EVIDENCE:** 2 títulos vencidos; `top_client_share` 100% nos vencidos  
**CONFIDENCE_ESTIMATE:** 0,50 (observation)  
**DIRECTOR_ACTION:** Cobrar posição de F.J. SERVICOS sobre títulos vencidos há ~19 dias  
**WHY_LOGOS_ADDS_VALUE:** Parcialmente visível como observation CardReceivable; concentração não está no título executivo  
**IMPLEMENTATION_COST:** Médio — overlap com CardReceivable; não selecionado para evitar duplicidade

---

## Seleção (Fase 5)

| Campo | Valor |
|---|---|
| **SELECTED_PROBLEM** | NF fornecedor SOUZA CRUZ sem histórico no baseline |
| **SELECTED_TENANT** | 11495 |
| **FINANCIAL_EXPOSURE** | R$ 5.979,47 |
| **MONEY_TYPE** | ESTIMATED |
| **WHY_SELECTED** | Única oportunidade nova com exposição ≥R$5k, evidência documental (NF) e ação financeira clara; VIP estava sem decisão |
| **WHY_NOT_RANK_2** | Já é winner global — não é gap de visibilidade |
| **WHY_NOT_RANK_3** | Confidence insuficiente para decisão; overlap com detector existente |
| **EXPECTED_DIRECTOR_ACTION** | Ligar para financeiro/compras da VIP e exigir comprovação da NF 001872693 |

---

## Gate "Diretor liga para o gerente"

**DIRECTOR_QUESTION:** "Por que a NF 001872693 da SOUZA CRUZ de R$ 5.979 foi lançada em junho sem qualquer despesa equivalente da mesma fornecedora no período anterior?"  
**WHO_SHOULD_ANSWER:** Gerente financeiro / responsável de compras — POSTO VIP  
**FINANCIAL_VALUE_INVOLVED:** R$ 5.979,47 (ESTIMATED)  
**EVIDENCE_AVAILABLE:** Lançamento ERP com REF NF, baseline zero, evidence items anexados  
**EXPECTED_ACTION:** Validar pedido, nota e recebimento; descartar ou corrigir lançamento  
**GATE:** PASS
