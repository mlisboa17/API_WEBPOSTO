# F08.4 QA Recheck — IA-6

**Data:** 2026-06-14  
**Script:** `scripts/audit_f08_4_financial_intelligence_center.py`

---

## Gate checklist

| Critério | Resultado |
|----------|-----------|
| 4 endpoints funcionando | ✅ 4/4 HTTP 200 |
| 0 erro de negócio | ✅ payloads válidos |
| 0 dado inventado | ✅ `forecast: null`, `generativeAi: false` |
| 0 quebra F08.0 | ✅ lê `snapshots/financial/` via snapshot service |
| 0 quebra F08.1 | ✅ não altera health engine |
| 0 quebra F08.2 | ✅ não altera scheduler/recovery |
| 0 quebra F08.3 | ✅ rotas operations-center intactas |
| Escopo limpo (git) | ⚠️ commit inclui 12 arquivos extras |
| pytest F08.4 | ✅ 9 passed (`test_financial_intelligence_center.py`) |
| pytest F08.4 + F08.3 | ✅ 17 passed |
| audit script | ✅ `"approved": true` |

---

## Pytest (recheck)

| Modo | Resultado |
|------|-----------|
| Default (`pytest.ini` + `--cov=src`) | 17 passed |
| Audit (`--no-cov`) | 17 passed |
| Falha de código F08.4 | **Nenhuma** |
| Falha de config | **Potencial** em versões antigas cov/no-cov — ver `PYTEST_COVERAGE_CONFLICT_REPORT.md` |

---

## Lineage & live

| Item | Status |
|------|--------|
| KPIs com lineage | ✅ riscos e oportunidades |
| WebPosto Live | ✅ não obrigatório — snapshot-first |
| Cross-tenant | ✅ filtro `empresaCodigo` preservado |

---

## Veredicto QA funcional

**APROVADO** para homologação F08.4.

**Ressalva:** escopo git do commit `2a06c07` contaminado — ver `F08_4_COMMIT_READINESS_REPORT.md`.
