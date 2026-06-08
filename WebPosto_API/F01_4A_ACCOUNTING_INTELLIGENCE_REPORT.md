# F01.4-A — PLANO DE CONTAS INTELIGENTE — RELATÓRIO FINAL

**Gerado:** 2026-06-08 · Evidência: `scripts/f01_4a_validation_results.json`

## Parecer executivo

### ✅ **APROVADO PARA F01.4**

---

## Respostas obrigatórias

| # | Item | Resposta |
|---|------|----------|
| 1 | Cobertura Plano Conta Gerencial | **100.0%** (DESPESAS_REDE) |
| 2 | Cobertura Plano Conta Contábil | **0.0%** (planoContaCodigo em MOVIMENTO) |
| 3 | Cobertura Centro de Custo | DESPESAS 0% · TITULO_PAGAR **100%** · MOVIMENTO parcial |
| 4 | Cobertura por fato | Ver `PLANO_CONTAS_INTELLIGENCE_REPORT.md` |
| 5 | Redução potencial OUTROS | V2 4.35% → V3 **0.52%** (−3.82 pp) |
| 6 | classificationSource | ✅ PLANO_CONTA · MANUAL · HIBRIDO · DESCRICAO |
| 7 | confidenceScore V3 | ✅ 0.0–1.0 (max 0.95) |
| 8 | dim_plano_conta | ✅ DDL + JSON mapping |
| 9 | dim_centro_custo | ✅ DDL (lacuna catálogo 401) |
| 10 | DRE Readiness | ~65% — ver DRE_READINESS_REPORT.md |
| 11 | DW Readiness | 78/100 |
| 12 | Health Score V2 | ✅ componente planoConta |
| 13 | Maturidade | **9.2/10** |
| 14 | Risco | **12/100** |
| 15 | Pronto F01.4? | **Sim** |

## Parecer final

### ✅ **APROVADO PARA F01.4**

Classificação V3 reduz OUTROS de 4.35% para **0.52%** usando plano de contas gerencial (100% cobertura em despesas), com linhagem documentada e dimensões DW preparadas.
