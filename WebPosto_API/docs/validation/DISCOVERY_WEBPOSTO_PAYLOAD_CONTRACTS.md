# Contratos WebPosto — Motor de Descoberta (Sprint 2)

**Atualizado:** 2026-07-12  
**Escopo:** Campos obrigatórios por detector do Top 5

---

## Filtros comuns (multitenancy)

| Campo | Tipo | Obrigatório | Uso |
|-------|------|-------------|-----|
| `dataInicial` | `YYYY-MM-DD` | Sim | Janela de análise |
| `dataFinal` | `YYYY-MM-DD` | Sim | Janela de análise |
| `empresaCodigo` | int ou CSV | Não | Drill-down por filial; omitido = rede |

---

## ExpenseDetector

| Endpoint ERP | Rota gateway | Campos-chave |
|--------------|--------------|--------------|
| `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` | `/v1/financial/expenses` | `data`, `valor`, `planoConta`, `empresaCodigo`, `centroCusto` |

**Sinais:** `CATEGORY_SPIKE`, `SUPPLIER_SPIKE`, `DUPLICATE_PAYMENT_SIGNAL`  
**Baseline:** média histórica por categoria no período de referência  
**Evidência:** `snapshots/discovery_expense/`

---

## SupplierInvoiceSpikeDetector

| Endpoint ERP | Campos-chave |
|--------------|--------------|
| Despesas financeiras rede | `nf_number`, `supplier`, `valor`, `data`, `empresaCodigo` |

**Sinais:** `SUPPLIER_INVOICE_SPIKE` (NF sem baseline histórico)  
**Limitação:** NF referenciada pode não ter histórico comparável

---

## CardReceivableDetector

| Endpoint ERP | Rota gateway | Campos-chave |
|--------------|--------------|--------------|
| `/INTEGRACAO/TITULO_RECEBER` | `/v1/financial/accounts-receivable` | `vencimento`, `valor`, `empresaCodigo`, `situacao` |

**Sinais:** `OVERDUE_RECEIVABLE` (LEVEL 1)  
**Threshold decisão:** confidence ≥ 80% (abaixo → observation)

---

## FuelRevenueDetector

| Endpoint ERP | Rota analytics | Campos-chave |
|--------------|----------------|--------------|
| Venda item combustível | `/api/v1/sales/fuel-summary` | `litros`, `combustivel`, `participacao`, `empresaCodigo` |

**Sinais:** queda de receita/litros vs baseline  
**Agregação:** rede → filial → combustível

---

## Resolução de decisão (evidence / explain)

| Endpoint | Fonte |
|----------|-------|
| `GET /api/v1/decisions/{id}/evidence` | `snapshots/owner_analysis/owner_analysis_last_valid_*.json` |
| `GET /api/v1/discovery/explain/{id}` | Mesmo snapshot + `RootCauseEngine` |

**IDs válidos:** `top_5_decisions[].candidate.id`, `stored_candidates[].id`, `action.id`
