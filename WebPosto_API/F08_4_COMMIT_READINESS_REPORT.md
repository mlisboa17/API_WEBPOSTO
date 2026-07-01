# F08.4 Commit Readiness — IA-5

**Estado:** commit `2a06c07` **já realizado e pushed** — este documento define o escopo **ideal** e o que **não deveria** ter entrado.

---

## COMMITAR (escopo limpo F08.4 — 20 arquivos)

```bash
git add src/services/financial_trend_intelligence_service.py
git add src/services/financial_risk_intelligence_service.py
git add src/services/financial_opportunity_service.py
git add src/services/cash_flow_intelligence_service.py
git add src/services/financial_commitments_intelligence.py
git add src/services/financial_intelligence_center_service.py
git add src/services/financial_intelligence_evidence.py
git add src/interfaces/http/routes/financial_intelligence_center.py
git add src/interfaces/http/app.py
git add tests/unit/test_financial_intelligence_center.py
git add frontend/pages/financialIntelligence.js
git add frontend/app.js
git add frontend/config/navigation.js
git add frontend/index.html
git add frontend/services/api.js
git add frontend/styles.css
git add dw/ddl/fact_financial_intelligence.sql
git add scripts/audit_f08_4_financial_intelligence_center.py
git add scripts/f08_4_financial_intelligence_center.json
git add F08_4_FINANCIAL_INTELLIGENCE_CENTER_REPORT.md
```

---

## NÃO COMMITAR (fora F08.4)

```text
dw/ddl/fact_commercial_execution.sql
snapshots/cash_flow/*
snapshots/goals_campaign_engine/*
snapshots/operator_performance/*
snapshots/operator_profitability/*
snapshots/people_intelligence/*
snapshots/non_fuel_products/*
snapshots/product_master_cache/index.json
theme/produtos.js
.claude/worktrees/*
```

---

## Situação do commit `2a06c07`

| Métrica | Valor |
|---------|-------|
| Arquivos no commit | 32 |
| Escopo F08.4 puro | ~20 |
| Contaminação | **12 arquivos** (~37%) |

**Risco de commit contaminado:** **SIM** — funcionalidade F08.4 OK, escopo git **não limpo**.

**Ação corretiva (futura, fora deste audit):** commit de limpeza removendo artefatos FORA_DO_ESCOPO ou PR com nota de escopo.

---

## Funcionalidade vs escopo git

| Dimensão | Pronto? |
|----------|---------|
| Código F08.4 | ✅ |
| Endpoints | ✅ |
| Testes | ✅ |
| Escopo git ideal | ⚠️ commit já inclui extras |
