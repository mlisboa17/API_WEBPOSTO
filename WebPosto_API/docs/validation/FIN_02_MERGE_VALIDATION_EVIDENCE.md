# FIN-02 — Merge Validation Evidence

Pacote de evidências para merge. **FIN-02 funcionalmente validado.**

Data de captura: 2026-07-08

---

## 1. Testes unitários — 25 passed

**Comando:**

```bash
python -m pytest tests/unit/test_financial_review_assignment.py tests/unit/test_financial_review_inbox.py -q --no-cov
```

**Resultado:** `25 passed, 18 warnings in ~6s`

**Artefato:** `docs/validation/FIN_02_TEST_RUN.txt`

| Suite | Arquivo | Casos FIN-02 relevantes |
|-------|---------|-------------------------|
| Assignment | `test_financial_review_assignment.py` | 16 — REQUESTED→ASSIGNED, idempotência, conflito 409, Diretoria/Financeiro reflexo, API POST |
| Inbox FIN-01 | `test_financial_review_inbox.py` | 9 — regressão inbox/detail |

**POST assign coberto por unit:**

- `test_assign_api_endpoint` — POST 200, conflito 409, idempotência
- `test_requested_to_assigned`, `test_idempotent_same_responsible`, `test_conflict_different_responsible`
- `test_financeiro_reflects_assignment`, `test_diretoria_reflects_assignment`

---

## 2. Runtime HTTP + performance — PASS

**Script:** `scripts/fin02_financial_review_assignment_validation.py`

**Artefatos:**

- `docs/validation/FIN_02_FINANCIAL_REVIEW_ASSIGNMENT_RUNTIME_FIRST.json` — **primeira execução** (REQUESTED → ASSIGNED)
- `docs/validation/FIN_02_FINANCIAL_REVIEW_ASSIGNMENT_RUNTIME.json` — re-execução idempotente
- `docs/validation/FIN_02_FINANCIAL_REVIEW_ASSIGNMENT_RUNTIME.md`

**Primeira execução (assignment real):** ver `FIN_02_FINANCIAL_REVIEW_ASSIGNMENT_RUNTIME_FIRST.json`

| Métrica | Valor |
|---------|-------|
| `http_assign_status` | **200** |
| `status_before` | REQUESTED |
| `status_after` | ASSIGNED |
| `responsible_after` | Marcio de Lima |
| `detail_seconds_before_assign` | 0.14 s |
| `detail_seconds_after_assign` | 0.05 s |
| `detail_fast_path` | true |
| `pass` | true |

**Re-execução (idempotente):** POST 200, `assign_idempotent: true` — store preservado.

**Live server POST (merge check):** `docs/validation/FIN_02_HTTP_ASSIGN_LIVE.json` → HTTP **200**

---

## 3. UI visual — PASS

**Script:** `scripts/fin02_ui_assign_validation_playwright.py`

**Artefato:** `docs/validation/FIN_02_UI_ASSIGN_VALIDATION.json`

| Check | Resultado |
|-------|-----------|
| Detalhe carrega POSTO DOZE | ✅ |
| Responsável visível (Marcio de Lima) | ✅ |
| Status Atribuído | ✅ |
| Fluxo assign (1ª execução) | ✅ validado na sessão FIN-02 |
| Fluxo assign (re-run) | ✅ `already_assigned: true`, `ui_pass: true` |

**Playwright — ambiente:**

- 1ª tentativa: falhou com `ERR_CONNECTION_REFUSED` (servidor `:8040` parado) — **problema de ambiente, não falha funcional**
- Reexecução com `uvicorn` ativo: `ui_pass: true` (`FIN_02_UI_ASSIGN_VALIDATION.json`)

**URL:** `http://127.0.0.1:8040/app/financial?view=financial-review-detail&requestId=d7ff3eae-…`

**Cobertura visual POST assign:**

1. Botão **Assumir conferência** → formulário nome → **Confirmar responsabilidade**
2. Sucesso **somente após HTTP 2xx** (`assignFinancialReview` em `app.js`)
3. Re-run com request já ASSIGNED → UI exibe responsável sem botão falso

---

## 4. Escopo FIN-02 — sem expansão arquitetural

Incluído neste merge:

- POST assign + persistência `ExecutiveReviewStore`
- UI assign no frontend runtime oficial (`WebPosto_API/frontend`)
- Projeções Financeiro + Diretoria (mesma request)
- Fast path detail (`enrich_nominal=False`)

**Fora deste merge (follow-up separado):**

- Migração NewWebLogos
- Lifespan FastAPI / warnings Pydantic
- Conferência operacional (FIN-03+)

---

## 5. Veredito merge

| Gate | Status |
|------|--------|
| 25 unit tests | ✅ PASS |
| Runtime JSON | ✅ PASS |
| POST assign HTTP 200 | ✅ PASS |
| UI Playwright | ✅ PASS |
| Escopo contido | ✅ |

**FIN-02 pronto para merge.**
