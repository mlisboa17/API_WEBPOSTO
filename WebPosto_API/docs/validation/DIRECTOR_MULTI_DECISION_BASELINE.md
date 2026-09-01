# Director Multi-Decision — Baseline (pré-hierarquia)

**Data:** 2026-07-09  
**Branch:** `feature/director-value-demo`  
**HEAD:** `61ea7e8`

## Runtime HTTP (8046)

| Campo | Valor |
|-------|-------|
| RUNTIME_DECISIONS_COUNT | 2 |
| RUNTIME_OBSERVATIONS_COUNT | 2 |
| RUNTIME_DETECTORS | FuelRevenueDetector, ExpenseDetector, CardReceivableDetector, SupplierInvoiceSpikeDetector |

### RUNTIME_DECISION_1

- Tenant: 74014 — POSTO DOZE FILIAL II
- Detector: ExpenseDetector
- Valor: R$ 7.501 ESTIMATED
- Confidence: 89%

### RUNTIME_DECISION_2

- Tenant: 11495 — POSTO VIP
- Detector: SupplierInvoiceSpikeDetector
- Valor: R$ 5.979 ESTIMATED
- Confidence: 90,2%
- NF: 001872693 — SOUZA CRUZ LTDA.

## Teste visual 15s (antes da correção)

**Pergunta:** Consigo perceber em até 15 segundos que existem duas decisões?

**Resultado:** **PARTIAL**

- Duas decisões existiam no contrato `top_5_decisions[]`
- UI anterior usava grid com cards visualmente equivalentes
- Prioridade #1 e #2 competiam sem hierarquia clara
- Follow-up e observations presentes

## Ação planejada

Hierarquia executiva: Prioridade da rede → Próximas decisões → Sinais → Acompanhamento → Cobertura.
