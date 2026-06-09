# BUSINESS MATURITY REPORT — Release 2.0

**Data:** 2026-06-08 · Baseline 2.0 → Release 2.0 Preparation

---

## Maturidade por dimensão

| Dimensão | Baseline 2.0 | Release 2.0 | Δ |
|----------|--------------|-------------|---|
| **Financeiro** | 9.6/10 | **9.6/10** | — |
| **Combustíveis** | 8.8/10 | **8.9/10** | +0.1 cobertura LMC |
| **Analytics** | 9.4/10 | **9.4/10** | — |
| **Supplier Intelligence** | 9.2/10 | **9.5/10** | +segmentation F01.4-D |
| **DW** | 8.5/10 | **8.5/10** | DDL 85%; ETL pendente |
| **Compras** | 5.5/10 | **5.5/10** | COMPRA 401 |
| **Tesouraria** | 7.5/10 | **7.5/10** | F02 planejado |
| **Governança / Publicação** | — | **6.0/10** | Segurança RETIDA |

**Maturidade global ponderada:** **9.1/10** (funcional) · **7.8/10** (publicação)

---

## Top 20 oportunidades

| # | Oportunidade | Domínio | ROI |
|---|--------------|---------|-----|
| 1 | Negociação corporativa VIBRA (monitoramento sem falso alerta) | Supplier | Alto |
| 2 | Consolidação O.E.C. contabilidade multi-filial | Financeiro | Alto |
| 3 | Centralização TITULO_PAGAR rede | Financeiro | Alto |
| 4 | Redução OUTROS residual 0,52% → <0,3% | Classificação | Médio |
| 5 | DRE 89,81% → meta 95% via TITULO_RECEBER | DRE | Alto |
| 6 | Procurement — 23 oportunidades F01.4-D | Compras | Alto |
| 7 | Economia contratos descentralizados (Cost Matrix) | Supplier | Alto |
| 8 | A04 ETL dim_supplier + fact_supplier_cost | DW | Estratégico |
| 9 | F02 Tesouraria — CP/CR aging consolidado | Tesouraria | Alto |
| 10 | Token COMPRA_REDE / NOTA_ENTRADA | Compras | Bloqueador |
| 11 | CENTRO_CUSTO_REDE catálogo 401 | DW | Médio |
| 12 | Health Score V3 drill-down por filial | Analytics | Médio |
| 13 | Benchmark filiais combustível | Combustíveis | Médio |
| 14 | Data Quality fornecedor 96,6 → 98% | Supplier | Médio |
| 15 | Snapshot HIT < 50ms rede (Redis) | Performance | Médio |
| 16 | Playwright CI gate no push | QA | Médio |
| 17 | LogosPostos remote unificado | DevOps | Estratégico |
| 18 | Remoção entrypoint 8050 | Tech debt | Baixo |
| 19 | Classificação V3 plano conta 100% | DRE | Alto |
| 20 | Corporate Cost Matrix drill-down A04 UI | Supplier | Alto |

---

## ROI potencial (estimativa qualitativa)

| Iniciativa | Economia / valor | Horizonte |
|------------|------------------|-----------|
| VIBRA negociação corporativa | **5–15%** custo combustível rede | 6–12 meses |
| Procurement F01.4-D (23 ops) | **R$ 150k–400k/ano** (estimativa rede) | 3–6 meses |
| OUTROS 0,52% → DRE 95% | Visibilidade + **2–4%** eficiência despesa | 6 meses |
| F02 Tesouraria | Redução inadimplência + float caixa | 12 meses |
| A04 DW | Decisões data-driven; base BI | 12–18 meses |
| Remediação segurança pré-push | Evita vazamento chaves WebPosto | **Imediato** |

**Maior ROI imediato (sem token novo):** Finance Center + Supplier Segmentation + remediação segurança.

---

## Risco de negócio

| Fator | Score |
|-------|-------|
| Dependência token WebPosto (2/11 filiais) | 35/100 |
| Credenciais expostas pré-publicação | 40/100 |
| Concentração VIBRA monitorada | 15/100 |
| COMPRA 401 | 25/100 |

**Risco de negócio consolidado:** **29/100** (aceitável pós-remediação segurança)
