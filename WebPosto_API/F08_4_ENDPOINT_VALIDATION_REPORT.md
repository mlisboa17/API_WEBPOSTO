# F08.4 Endpoint Validation — IA-4

**Período:** `2026-06-01` → `2026-06-07`  
**Método:** FastAPI `TestClient` (snapshot-first, sem WebPosto live)  
**Data:** 2026-06-14

---

## Resultados

| Endpoint | HTTP | `success` | Payload | Runtime |
|----------|------|-----------|---------|---------|
| `GET /api/v1/financial/intelligence-center/cockpit` | **200** | true | executiveFinancialScore, trends, risks, opportunities, cashFlow, commitments, answers | OK |
| `GET /api/v1/financial/intelligence-center/trends` | **200** | true | horizons 7d/30d/90d/12m, overallTrend, lineage | OK |
| `GET /api/v1/financial/intelligence-center/risks` | **200** | true | risks[] com lineage, overallLevel | OK |
| `GET /api/v1/financial/intelligence-center/opportunities` | **200** | true | impacto_estimado, evidencia, origem | OK |

---

## Validações de negócio (cockpit)

| Campo | Valor observado | OK? |
|-------|-----------------|-----|
| `snapshotFirst` | true | ✅ |
| `generativeAi` | false | ✅ |
| `cashFlow.forecast` | null | ✅ sem forecast inventado |
| `executiveCards.length` | 6 | ✅ limite IA-7 |
| Riscos com `lineage` | 100% | ✅ |

---

## Score executivo (evidência snapshot)

- **Score:** 38.5  
- **Classificação:** CRÍTICO  
- **Fluxo:** −R$ 130.794,29 (despesas >> recebimentos no snapshot homologado)

Valores coerentes com `snapshots/financial/financial_overview_2026-06-01_2026-06-07_all.json` — **não inventados**.

---

## Conclusão

**4/4 endpoints OK.** Nenhum erro runtime detectado.
