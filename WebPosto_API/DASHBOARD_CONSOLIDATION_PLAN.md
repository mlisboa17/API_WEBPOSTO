# DASHBOARD CONSOLIDATION PLAN — LOGOS SPACE
## Sprint A02.5 | Agente 5 — Frontend

| Campo | Valor |
|---|---|
| **Dashboard oficial** | `frontend/index.html` → `/app/financial` (8040) |
| **Total catalogados** | 21 superfícies |
| **Permanecem** | 1 oficial + 1 auxiliar transitório |
| **Data** | 2026-06-08 |

---

## Catálogo Completo

| ID | Arquivo / Rota | Tecnologia | Classificação | Status Futuro |
|---|---|---|---|---|
| D-001 | `frontend/index.html` → `/app/financial` | SPA Vanilla JS | **OFICIAL** | Manter |
| D-002 | `static/dashboard_logos.html` → `/dashboard` (8050) | HTML/JS Adelaide | **LEGADO** | DEPRECATED → redirect |
| D-003 | `static/produtos_crud.html` → `/produtos` | HTML/JS | **LEGADO** | DEPRECATED → aba futura |
| D-004 | `static/painel_webposto.html` | HTML técnico | **LEGADO** | REMOVER |
| D-005 | `static/explorador_tecnico.html` | HTML debug | **LEGADO** | REMOVER |
| D-006 | `static/explorador_integracao.html` | HTML debug | **LEGADO** | REMOVER |
| D-007 | Gateway `/app/vendas` | HTML vendas | **LEGADO** | DEPRECATED → `view=sales` |
| D-008 | `dashboard_vendas.html` | HTML raiz | **OBSOLETO** | REMOVER |
| D-009 | `vendas-dashboard.html` | HTML raiz | **OBSOLETO** | REMOVER |
| D-010 | `admin-dashboard.html` | HTML CRUD | **OBSOLETO** | REMOVER |
| D-011 | `dashboard_abastecimento.html` | HTML operação | **OBSOLETO** | REMOVER (Fase F) |
| D-012 | `dashboard_filtros.html` | HTML protótipo | **OBSOLETO** | REMOVER |
| D-013 | `dashboard_demo.html` | HTML demo | **OBSOLETO** | REMOVER |
| D-014 | `diagnostico.html` | HTML diagnóstico | **OBSOLETO** | REMOVER → `/health` |
| D-015 | `temp_dashboard.html` | HTML teste | **EXPERIMENTAL** | REMOVER |
| D-016 | `test_dashboard.html` | HTML teste | **EXPERIMENTAL** | REMOVER |
| D-017 | `src/frontend/dashboard.jsx` | React isolado | **EXPERIMENTAL** | REMOVER |
| D-018 | `theme/executive.js` + `theme/cockpit.js` | JS Adelaide | **LEGADO** | REMOVER |
| D-019 | `theme/audit_subcentro.js` | JS auditoria | **LEGADO** | REMOVER |
| D-020 | `index.html` (raiz) | Landing unclear | **OBSOLETO** | REMOVER |
| D-021 | `explorador_standalone.py` | FastAPI explorador | **EXPERIMENTAL** | REMOVER |

---

## Views Oficiais (SPA)

| View | Arquivo | Domínio | Maturidade |
|---|---|---|---|
| `executive` | `executiveDashboard.js` | Gestão | PARCIAL (snapshot) |
| `fuels` | `fuelExecutiveDashboard.js` | **Combustíveis** | PRONTO |
| `sales` → fuels | `sales.js` | Vendas/Combustíveis | PRONTO |
| `dashboard` | `dashboard.js` | Financeiro | PARCIAL |
| `expenses` | `expenses.js` | Financeiro | PARCIAL |
| `accounts` | `accountsPayable.js` | Financeiro | PARCIAL |
| `stock` | `stock.js` | Estoque | PARCIAL |

---

## Cronograma de Remoção

| Fase | Sprint | Ação |
|---|---|---|
| 1 | A02.5 | Documentar oficial; congelar legados |
| 2 | A03 | Remover HTML obsoletos da raiz (D-008..D-014) |
| 3 | A04 | Redirect `/dashboard` (8050) → `/app/financial` |
| 4 | A04 | Migrar funcionalidades úteis de Adelaide → SPA |
| 5 | A05 | Arquivar `static/`, `theme/` → `_archive/` |
| 6 | A05 | Remover rotas UI do `presentation/app.py` |

---

## Regras Oficiais

1. Proibido criar dashboards HTML fora de `frontend/`
2. Proibido adicionar features em legados (bugfix only)
3. Nova tela → `frontend/pages/*.js` + view em `app.js`
4. Export CSV/PDF → manter padrão `export.js`

---

*Agente 5 — sem alteração de código nesta sprint.*
