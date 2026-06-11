# EXPENSES SCREEN QA REPORT

**Script:** `scripts/p0_validate_expenses_screen.py`  
**Evidência:** `scripts/p0_expenses_screen_validation.json`  
**Testes unitários:** `tests/unit/test_screen_expenses_consolidation.py` (3/3 OK)

---

## Caso obrigatório — AP CASA CAIADA · 08/06/2026

| Métrica | Antes (bug) | Depois (P0) |
|---------|-------------|-------------|
| Total registros | 1 | **5** |
| Financeiro | 1 (BOBINA R$ 135) | **2 · R$ 1.912,00** |
| Caixa | 0 | **2 · R$ 270,00** |
| PDV | 0 | **1 · R$ 135,00** |
| BOBINA TERMICA | visível | **continua visível** |

**Pass:** `total > 1` ✅

---

## Multiselect / Todos

| Cenário | Total | Paridade empresa |
|---------|------:|------------------|
| `5555` | 5 | só 5555 ✅ |
| `11495` | 13 | só 11495 ✅ |
| `11495,5555` | 18 | ambas ✅ |
| Todos | 57 | 10 filiais ✅ |

---

## Paridade Tabela = API = CSV = PDF

| Canal | Mecanismo | Δ esperado |
|-------|-----------|------------|
| API | `GET /v1/financial/expenses` | baseline |
| Tabela | `payload.data` | 0,00 |
| CSV/PDF | `renderTable` export same rows | 0,00 |

Export usa os mesmos `rows` renderizados — diferença **R$ 0,00** quando filtros client-side estão limpos.

---

## QA Veredito

**APROVADO** para caso AP CASA CAIADA 08/06/2026.
