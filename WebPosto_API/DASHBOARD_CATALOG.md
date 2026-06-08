# LOGOS SPACE — Dashboard Catalog
## Sprint A02 — Catálogo Oficial de Dashboards

| Campo | Valor |
|---|---|
| **Dashboard oficial** | `frontend/index.html` → `/app/financial` (porta 8040) |
| **Data** | 2026-06-08 |

---

## 1. Resumo

| Pergunta | Resposta |
|---|---|
| Quantos dashboards existem? | **16 arquivos HTML/JSX** + **1 SPA modular** + **3 rotas gateway** |
| Qual é o oficial? | SPA `frontend/` servida em `/app/financial` |
| Quantos continuam? | **1 oficial** + **1 auxiliar transitório** (gateway 8050) |
| Quantos serão descontinuados? | **14 legados/experimentais** |

---

## 2. Catálogo Completo

### PRODUÇÃO — Oficial

| ID | Arquivo / Rota | Views | Classificação | Status Futuro |
|---|---|---|---|---|
| **D-001** | `frontend/index.html` → `/app/financial` | executive, dashboard, fuels, sales, expenses, accounts, stock | **PRODUÇÃO** | **OFICIAL** |

**Views do dashboard oficial:**

| View | Arquivo JS | Domínio | Maturidade |
|---|---|---|---|
| `executive` | `executiveDashboard.js` | Gestão | PARCIAL (snapshot) |
| `fuels` | `fuelExecutiveDashboard.js` | **Combustíveis** | PRONTO |
| `sales` → fuels | `sales.js` | Vendas/Combustíveis | PRONTO |
| `dashboard` | `dashboard.js` | Financeiro | PARCIAL |
| `expenses` | `expenses.js` | Financeiro | PARCIAL |
| `accounts` | `accountsPayable.js` | Financeiro | PARCIAL |
| `stock` | `stock.js` | Estoque | PARCIAL |

---

### PRODUÇÃO — Auxiliar (transitório)

| ID | Arquivo / Rota | Classificação | Status Futuro |
|---|---|---|---|
| **D-002** | `static/dashboard_logos.html` → `/dashboard` (8050) | LEGADO ativo | **DEPRECATED** |
| **D-003** | Gateway `/produtos` → `static/produtos_crud.html` | LEGADO ativo | **DEPRECATED** |
| **D-004** | Gateway `/app/vendas` → HTML vendas | LEGADO ativo | **DEPRECATED** |

---

### LEGADO — Descontinuar

| ID | Arquivo | Propósito original | Status Futuro |
|---|---|---|---|
| **D-005** | `dashboard_vendas.html` | Vendas com filtros | **REMOVER FUTURAMENTE** |
| **D-006** | `vendas-dashboard.html` | Relatórios com gráficos | **REMOVER FUTURAMENTE** |
| **D-007** | `dashboard_abastecimento.html` | Abastecimentos | **REMOVER FUTURAMENTE** |
| **D-008** | `dashboard_filtros.html` | Filtros genéricos | **REMOVER FUTURAMENTE** |
| **D-009** | `dashboard_demo.html` | Demonstração | **REMOVER FUTURAMENTE** |
| **D-010** | `admin-dashboard.html` | CRUD financeiro/caixa | **REMOVER FUTURAMENTE** |
| **D-011** | `static/painel_webposto.html` | Painel técnico | **REMOVER FUTURAMENTE** |
| **D-012** | `static/explorador_integracao.html` | Explorador integração | **REMOVER FUTURAMENTE** |
| **D-013** | `static/explorador_tecnico.html` | Explorador técnico | **REMOVER FUTURAMENTE** |
| **D-014** | `diagnostico.html` | Diagnóstico conexão API | **REMOVER FUTURAMENTE** |
| **D-015** | `src/frontend/dashboard.jsx` | React isolado (não integrado) | **REMOVER FUTURAMENTE** |
| **D-016** | `theme/executive.js` + `theme/cockpit.js` | Shell JS Adelaide | **REMOVER FUTURAMENTE** |
| **D-017** | `theme/audit_subcentro.js` | Auditoria sub-centro | **REMOVER FUTURAMENTE** |
| **D-018** | `index.html` (raiz) | Landing unclear | **REMOVER FUTURAMENTE** |

---

### EXPERIMENTAL — Descontinuar

| ID | Arquivo | Status Futuro |
|---|---|---|
| **D-019** | `temp_dashboard.html` | **REMOVER FUTURAMENTE** |
| **D-020** | `test_dashboard.html` | **REMOVER FUTURAMENTE** |
| **D-021** | `explorador_standalone.py` (app FastAPI) | **REMOVER FUTURAMENTE** |

---

## 3. Matriz de Decisão

| Critério | D-001 (SPA oficial) | D-002..D-021 (legados) |
|---|---|---|
| Conecta analytics `/api/v1` | Sim | Não / parcial |
| Snapshot-first | Sim (executive) | Não |
| Export CSV/PDF | Sim | Parcial |
| FilialMaster fallback | Sim | Não |
| Manutenção ativa | Sim | Não |
| Testes automatizados | Parcial | Não |

---

## 4. Migração de Funcionalidades Legadas

| Funcionalidade legada | Dashboard legado | Destino oficial |
|---|---|---|
| Vendas com filtros | `vendas-dashboard.html` | `frontend` view `sales` |
| Abastecimentos | `dashboard_abastecimento.html` | Fase F (Operação) |
| CRUD financeiro | `admin-dashboard.html` | Fase C (Financeiro) |
| Adelaide métricas | `dashboard_logos.html` | `executive` + `fuels` |
| Explorador técnico | `explorador_*.html` | Ferramenta dev (fora prod) |
| Diagnóstico API | `diagnostico.html` | `/health` + `/ready` |

---

## 5. Regras Oficiais

1. **Proibido** criar novos dashboards HTML fora de `frontend/`
2. **Proibido** adicionar features em dashboards legados
3. Toda nova tela → view em `frontend/pages/`
4. Gateway 8050 dashboards → congelados (bugfix only) até deprecação
5. Remoção física de legados → Fase 4 do plano de migração

---

*Sprint A02 — catálogo oficial. Sem alteração de código.*
