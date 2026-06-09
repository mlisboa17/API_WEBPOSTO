# LOGOS SPACE — Architecture Baseline 2.1

**Data:** 2026-06-08 · Release 2.0 Preparation · Pós F01.4-D · Commit `10917af`

Evolução de [ARCHITECTURE_BASELINE_2.0.md](./ARCHITECTURE_BASELINE_2.0.md) com governança de publicação.

---

## EntryPoint oficial

| Componente | Caminho | Porta | Rota UI |
|------------|---------|-------|---------|
| API + SPA | `src/main.py` → `create_app()` | **8040** | `/app/financial` |
| Config | `src/infrastructure/config/settings.py` | — | — |
| Gateway WebPosto | `src/gateway/webposto_client.py` | externo | — |

**Deprecated:** qualquer referência a porta **8050** (Adelaide KPIs legado).

---

## Dashboard oficial

| View | Query param | Página JS | Status |
|------|-------------|-----------|--------|
| Finance Center | `view=finance-center` | `frontend/pages/financeCenter.js` | ✅ Oficial |
| Cash Flow | `view=cash-flow` | `frontend/pages/cashFlow.js` | ✅ Oficial |
| Executive / Fuel | views legadas | `frontend/app.js` | ⚠️ Suporte |

Blocos UI Finance Center (ordem render):

1. KPIs corporativos
2. Aging CP/CR
3. Intelligence (`fc-intelligence-cards`)
4. Advanced F01.4-B (`fc-advanced-cards`)
5. Health Score V3
6. Supplier Intelligence F01.4-C (`fc-supplier-cards`)
7. Segmentation + Cost Matrix F01.4-D (`fc-segmentation-cards`)

---

## Serviços oficiais

### Camada financeira corporativa (F01)

| Domínio | Serviço | Arquivo |
|---------|---------|----------|
| Finance Center | Consolidado CP/CR/Banco/Caixa/Despesa | `corporate_finance_center_service.py` |
| Cash Flow | Fluxo operacional + projeção | `corporate_cash_flow_service.py` |
| Intelligence | Classificação + insights | `financial_intelligence_service.py` |
| Advanced | Benchmark + anomalias + DRE | `financial_intelligence_advanced_service.py` |
| Health V3 | Score composto filial/rede | `financial_health_score_v3_service.py` |
| Supplier Intel | Concentração + risco | `supplier_intelligence_service.py` |
| Segmentation | Strategic suppliers + cost matrix | `supplier_segmentation_service.py` |
| MDM Fornecedor | Normalização VIBRA/OEC | `supplier_mdm.py` |
| Network Overview | Cobertura rede | `network_financial_overview_service.py` |

### Engines oficiais

| Engine | Arquivo | Versão |
|--------|---------|--------|
| Classificação despesa | `logos_expense_classifier_v3.py` | **V3** (oficial) |
| Reconciliação | `financial_reconciliation_engine.py` | Ativo |
| Fuel KPI | `fuel_kpi_engine.py` | Ativo |
| Money normalizer | `money_normalizer.py` | Ativo |

### Snapshots ativos (TTL 300s, Snapshot First)

| Snapshot | Serviço | Conteúdo |
|----------|---------|----------|
| Finance Center | `finance_center_snapshot_service.py` | FC completo |
| Intelligence | `finance_intelligence_snapshot_service.py` | Intel + Advanced + HS V3 + Suppliers + Segmentation |
| Cash Flow | `cash_flow_snapshot_service.py` | Fluxo de caixa |
| Executive / Fuel | `executive_snapshot_service.py`, `fuel_snapshot_service.py` | Legado operacional |

Store: `snapshot_store.py` · diretório `snapshots/`

---

## APIs oficiais

| Prefixo | Router | Endpoints principais |
|---------|--------|---------------------|
| `/api/v1/finance/center/*` | `finance_center.py` | snapshot, overview, export |
| `/api/v1/finance/cash-flow/*` | `cash_flow.py` | snapshot, summary |
| `/api/v1/finance/intelligence/*` | `financial_intelligence.py` | intelligence, advanced, suppliers, segmentation, health |
| `/api/v1/analytics/*` | `analytics.py` | Combustíveis, executive |

**Regra arquitetural imutável:** nunca expor `totalFinanceiro` agregando DESPESA+CP+BANCO+CAIXA+CR.

---

## Data Warehouse (DDL only — ETL A04)

21 objetos em `dw/ddl/` — ver [DW_GOVERNANCE_REPORT.md](./DW_GOVERNANCE_REPORT.md).

---

## Maturidade arquitetural

| Dimensão | Baseline 2.0 | Baseline 2.1 |
|----------|--------------|--------------|
| Consolidação F01 | 9.6/10 | **9.6/10** |
| Snapshot First | ✅ | ✅ |
| Separação camadas | ✅ | ✅ |
| Documentação | 8.5/10 | **9.0/10** (README + governança) |
| Segurança publicação | não auditado | **6.0/10** (credenciais expostas) |

**Maturidade arquitetural global:** **9.2/10**

---

## Risco arquitetural

| Fator | Peso | Baseline 2.0 | Baseline 2.1 |
|-------|------|--------------|--------------|
| Entrypoint duplicado 8050 | 15 | presente | presente |
| Clientes WebPosto legados | 10 | presente | presente |
| Credenciais no Git | — | não medido | **+25** |
| Snapshots versionados | 5 | presente | presente |
| Testes legados quebrados | 5 | presente | presente |

**Risco arquitetural:** **14/100** (2.0) → **39/100** (2.1) — elevação por segurança pré-publicação.

**Meta pós-remediação:** ≤ 15/100.
