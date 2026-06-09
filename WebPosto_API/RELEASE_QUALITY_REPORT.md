# RELEASE QUALITY REPORT — Release 2.0

**Data:** 2026-06-08 · Commit `10917af`

---

## Veredito global: **WARNING**

Funcionalidade F01 validada; bloqueio de publicação por segurança (ver SECURITY_AUDIT_REPORT).

---

## Matriz de validação

| Área | Teste | Resultado | Evidência |
|------|-------|-----------|-----------|
| **Finance Center** | Unit + E2E exports/filters/snapshot | **PASS** | 14/15 Playwright; unit PASS |
| **Cash Flow** | Unit `test_cash_flow_service.py` | **PASS** | 39/39 subset F01 |
| **Supplier Intelligence** | Unit MDM + validate F01.4-C | **PASS** | `f01_4c_validation_results.json` |
| **Supplier Segmentation** | Unit + F01.4-D validation | **PASS** | 47/47 baseline; 35 tests segmentation |
| **Exports** | CSV/PDF paridade E2E | **PASS** | `finance_center_exports.spec.ts` |
| **Snapshots** | MISS/HIT + consistência | **WARNING** | HIT rede 13,5ms ✅; JSON `pass:false` em miss script |
| **Playwright** | Suite finance | **WARNING** | 14/15 — 1 falha ECONNREFUSED (API offline no teste API-only) |
| **Unit Tests** | F01 core | **PASS** | 39 passed (execução direta, `-o addopts=`) |
| **Unit Tests legado** | Collection | **FAIL** | 7 testes `test_client`/`post_*` — fora escopo F01 |
| **Segurança** | Credenciais | **FAIL** | `.env` + hardcodes no Git |

---

## Detalhamento Playwright

Execução recente (`npm run test:e2e:finance`):

- ✅ 14 testes Finance Center (exports, filtros, snapshot UI)
- ❌ 1 teste `API snapshot MISS vs HIT (rede)` — `ECONNREFUSED 127.0.0.1:8040`

**Causa:** teste de API requer servidor ativo; falha de ambiente, não regressão funcional.

---

## Detalhamento Unit Tests

```
39 passed, 1 warning (Pydantic ConfigDict deprecation)
```

Suites executadas:

- `test_cash_flow_service.py`
- `test_finance_center_service.py`
- `test_expense_classifier_v2.py` / `v3.py`
- `test_financial_intelligence_advanced.py`
- `test_supplier_mdm.py` / `test_supplier_segmentation.py`
- `test_multiselect_utils.py`

**Nota:** `pytest.ini` define `--cov` que falha sem plugin; usar `-o addopts=` em CI.

---

## Snapshots

| Check | Status |
|-------|--------|
| Paridade API ↔ UI | ✅ Snapshot First TTL 300s |
| HIT rede < 500ms | ✅ 13,5 ms |
| Arquivos versionados | ⚠️ 28 JSON em `snapshots/` (dados operacionais) |
| Script `f01_snapshot_miss_hit.json` | ⚠️ `"pass": false` — revisar critério miss vs hit |

---

## Resumo PASS / WARNING / FAIL

| Status | Count | Itens |
|--------|-------|-------|
| **PASS** | 6 | FC, Cash Flow, Supplier Intel, Segmentation, Exports, Unit F01 |
| **WARNING** | 2 | Playwright (1 env), Snapshots (artefatos) |
| **FAIL** | 2 | Segurança, Unit legado collection |

**Gate Release 2.0:** **WARNING** (funcional OK, publicação bloqueada por segurança)
