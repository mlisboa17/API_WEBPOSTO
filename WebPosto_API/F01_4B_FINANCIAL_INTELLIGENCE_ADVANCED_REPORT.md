# F01.4-B — FINANCIAL INTELLIGENCE ADVANCED — RELATÓRIO FINAL

**Gerado:** 2026-06-08 · Evidência: `scripts/f01_4b_validation_results.json`

## Parecer executivo

### ✅ **APROVADO PARA F01.4 ADVANCED**

---

## Respostas obrigatórias

| # | Item | Resposta |
|---|------|----------|
| 1 | Top 20 Planos de Conta | **20** planos · total R$ 127978.10 |
| 2 | Top Centros de Custo | Ver COST_CENTER_ANALYTICS_REPORT.md |
| 3 | Benchmark Filiais | **10** filiais · melhor 5333 |
| 4 | Anomalias detectadas | **8** alertas |
| 5 | DRE Readiness atual | **89.81%** |
| 6 | Meta DRE futura | **85%** — Integrar receitas TITULO_RECEBER + catálogo contábil completo na A04 |
| 7 | Health Score V3 | **94** (saudavel) |
| 8 | Data Quality Score | **83.7** |
| 9 | Status DW | DDL v2 completo — DW_FINANCIAL_READY_V2.md |
| 10 | Status Data Mart | **~72%** pronto |
| 11 | Snapshot First | ✅ TTL 300s · advanced + healthScoreV3 no payload |
| 12 | Performance | **29918 ms** (advanced direct) |
| 13 | Nova maturidade | **9.4/10** |
| 14 | Novo risco | **10/100** |
| 15 | Pronto F01.4 Advanced? | **Sim** |

## Top 5 Planos (evidência)

| Plano | Valor | Part.% |
| --- | --- | --- |
| B01 - SALARIOS | 57567.91 | 44.98 |
| DESPESA POSTO | 18580.33 | 14.52 |
| SR. MOISES | 16707.49 | 13.05 |
| A13 - UNIFORMES/FARDAMENTOS E EPI´S | 6882.00 | 5.38 |
| REF NF:000064790 - SOLAR INOVE - PERNAMBUCO - SOLAR INOVE - PERNAMBUCO | 5016.48 | 3.92 |


## Top 5 Centros

| Centro | Valor |
| --- | --- |
| PISTA | 404777.42 |
| LOJA | 7387.64 |
| FOOD | 2635.50 |
| LUBRIFICANTE | 501.80 |


## Benchmark

| Filial | Índice | Class. |
| --- | --- | --- |
| 11495 | 1.9571 | Critico |
| 46433 | 1.6164 | Critico |
| 5557 | 1.4171 | Critico |
| 74014 | 1.1824 | Medio |
| 5256 | 1.1406 | Medio |
| 5559 | 0.9593 | Bom |
| 5555 | 0.5769 | Excelente |
| 5556 | 0.5633 | Excelente |
| 5560 | 0.4984 | Excelente |
| 5333 | 0.0886 | Excelente |


## OUTROS V3 (F01.4-A baseline)

- OUTROS V3: **0.52%**
- confidenceScore max: **0.95**

## Parecer final

### ✅ **APROVADO PARA F01.4 ADVANCED**

Camada de inteligência executiva operacional: analytics por plano/centro, benchmark de filiais, detecção de anomalias, DRE readiness documentado, Health Score V3 e Data Mart v2 preparados para A04/A05.
