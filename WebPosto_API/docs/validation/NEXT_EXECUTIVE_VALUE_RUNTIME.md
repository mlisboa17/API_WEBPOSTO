# NEXT EXECUTIVE VALUE — Runtime Validation

**Data:** 2026-07-09  
**Branch:** `feature/director-value-demo`  
**Período:** 2026-06-05 a 2026-07-04

## Fase 1 — Estado executivo confirmado

| Campo | Valor |
|---|---|
| REPOSITORY | Api_WebPosto/WebPosto_API |
| BRANCH | feature/director-value-demo |
| HEAD | 61ea7e8 |
| DIRECTOR_DEMO_PRESENT | YES |
| TENANTS | 5555, 11495, 74014 |
| ACTIVE_DETECTORS (antes) | FuelRevenueDetector, ExpenseDetector, CardReceivableDetector |
| CURRENT_WINNER (antes) | POSTO DOZE — vale consolidação R$ 7.501 |

## Execução pós-implementação

Comando: `run_owner_analysis('2026-06-05', '2026-07-04')`  
Artefato: `NEXT_EXECUTIVE_VALUE_RUNTIME.json`

| Métrica | Resultado |
|---|---|
| analysis_status | PRIORITY_FOUND |
| monitoring_state | DECISION |
| total_decisions | 2 |
| total_observations | 2 |
| detectors_executed | 4 (inclui **SupplierInvoiceSpikeDetector**) |
| duration_ms | ~135 (cache quente) |

## Winner global (inalterado — sem manipulação de score)

| Campo | Valor |
|---|---|
| GLOBAL_WINNER | Vale consolidação de caixa |
| GLOBAL_WINNER_TENANT | 74014 — POSTO DOZE FILIAL II |
| GLOBAL_WINNER_DETECTOR | ExpenseDetector |
| GLOBAL_WINNER_AMOUNT | R$ 7.501 (ESTIMATED) |
| GLOBAL_WINNER_CONFIDENCE | 0,89 |

## Nova decisão descoberta (gap fechado)

| Campo | Valor |
|---|---|
| DETECTOR | SupplierInvoiceSpikeDetector |
| TENANT | 11495 — POSTO VIP |
| TITLE | R$ 5.979 em NF 001872693 (SOUZA CRUZ LTDA.) sem histórico no período anterior |
| MONEY_TYPE | ESTIMATED |
| CONFIDENCE | 0,902 |
| RANK na rede | #2 (abaixo de 74014 por priority score) |

## Observations (inalteradas em essência)

1. 74014 — CardReceivable — R$ 3.264 vencidos  
2. 11495 — CardReceivable — R$ 2.482 vencidos  

## Validações

| Gate | Status |
|---|---|
| HOME_VISIBLE (Visão da rede) | YES — Playwright 6/6 jornada; 3 tenants, prioridade 74014 |
| EVIDENCE_ACCESSIBLE | YES — evidence_items na decisão VIP |
| ROOT_CAUSE_VISIBLE | YES — SupplierInvoiceRootCause registrado |
| MONEY_LABEL_HONEST | YES — ESTIMATED, não CONFIRMED |
| TENANT_ISOLATION | YES |
| MOCKS / SEEDS | NO |
| RUNTIME_HTTP | YES — API 8046 restart + refresh; top5 com 2 decisões |
| UI_VALIDATED | YES — 4 detectores na cobertura; observations + follow-up Marcio 3/13 |
| TESTS | 4 passed — `test_supplier_invoice_spike_detector.py` |

## President Gate

Nova decisão **não altera** a história principal da demo (winner 74014).  
Adiciona cobertura executiva na **VIP** — posto que antes só tinha observation de recebíveis.

**DIRECTOR_CALL_GATE:** PASS
