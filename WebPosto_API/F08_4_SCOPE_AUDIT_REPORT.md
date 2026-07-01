# F08.4 Scope Audit — IA-2

**Commit analisado:** `2a06c07` — `feat(f08.4): financial intelligence center`  
**Branch:** `feature/f08-4-financial-intelligence-center`

---

## OBRIGATÓRIO_F08_4

| Arquivo | Papel |
|---------|-------|
| `src/services/financial_trend_intelligence_service.py` | IA-1 Trend Engine |
| `src/services/financial_risk_intelligence_service.py` | IA-2 Risk Engine |
| `src/services/financial_opportunity_service.py` | IA-3 Opportunity Engine |
| `src/services/cash_flow_intelligence_service.py` | IA-4 Cash Flow Intelligence |
| `src/services/financial_commitments_intelligence.py` | IA-5 Receivables/Payables |
| `src/services/financial_intelligence_center_service.py` | Orquestrador + Executive Score |
| `src/services/financial_intelligence_evidence.py` | Loader snapshot-first (suporte) |
| `src/interfaces/http/routes/financial_intelligence_center.py` | API read-only |
| `tests/unit/test_financial_intelligence_center.py` | Testes unitários |
| `frontend/pages/financialIntelligence.js` | Cockpit IA-7 |
| `dw/ddl/fact_financial_intelligence.sql` | DW IA-8 |
| `scripts/audit_f08_4_financial_intelligence_center.py` | QA gate IA-9 |
| `scripts/f08_4_financial_intelligence_center.json` | Artefato QA |
| `F08_4_FINANCIAL_INTELLIGENCE_CENTER_REPORT.md` | Relatório sprint |

---

## INTEGRAÇÃO_F08_4

Alterações mínimas para expor a feature (presentes no commit):

| Arquivo | Motivo |
|---------|--------|
| `src/interfaces/http/app.py` | Registro router `financial_intelligence_center` |
| `frontend/app.js` | View, alias, refresh, render |
| `frontend/config/navigation.js` | Aba Financeiro → Intelligence |
| `frontend/index.html` | `#financialIntelligenceView` |
| `frontend/services/api.js` | `fetchFinancialIntelligenceCockpit` |
| `frontend/styles.css` | Classes `.fin-intel-*` |

---

## FORA_DO_ESCOPO (incluídos no commit `2a06c07`)

| Arquivo | Motivo |
|---------|--------|
| `dw/ddl/fact_commercial_execution.sql` | DW F08.2 / commercial — não F08.4 |
| `snapshots/cash_flow/*` | Módulo cash flow corporativo — não motor F08.4 |
| `snapshots/goals_campaign_engine/*` | Metas/campanhas — não F08.4 |
| `snapshots/operator_performance/*` | People/performance — não F08.4 |
| `snapshots/operator_profitability/*` | Rentabilidade operador — não F08.4 |
| `snapshots/people_intelligence/*` | People intelligence — não F08.4 |
| `snapshots/non_fuel_products/*` | Produtos vendidos — não F08.4 |
| `snapshots/product_master_cache/index.json` | Catálogo produtos — não F08.4 |

---

## Snapshots que F08.4 **consome** (não alterados neste commit)

F08.4 lê **`snapshots/financial/*`** (overview, expenses, receivables, payables) — já homologados em F08.0–F08.3. Esses arquivos **não precisam** entrar no commit F08.4 se já existem na branch base.

---

## Resumo

- **Escopo limpo ideal:** 14 obrigatórios + 6 integração = **20 arquivos**
- **Commit real:** 32 arquivos → **12 fora do escopo** (contaminação por `git add .`)
