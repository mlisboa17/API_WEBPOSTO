# QA BASELINE 2.0

## Unit Tests (F01 core)

**47/47 PASS** — cash flow, finance center, classifiers V2/V3, advanced, supplier MDM/segmentation, multiselect.

## Playwright

- `e2e/financial_intelligence.spec.ts`
- `e2e/finance_supplier_segmentation.spec.ts`

## Paridade

API = Snapshot = UI (Snapshot First TTL 300s). Export CSV/PDF via widgets existentes.

## Legado

7 testes unitários antigos com erro de collection (test_client, post_*) — fora escopo F01.
