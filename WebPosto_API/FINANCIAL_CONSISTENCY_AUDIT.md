# FINANCIAL CONSISTENCY AUDIT — F01.1.1

**Período:** 2026-06-01 → 2026-06-07  
**Evidência:** `scripts/f01_1_1_hardening_results.json`

## Módulos auditados (contagem isolada — sem soma cruzada)

| Fonte WebPosto | HTTP | Registros | ms |
|---|---|---:|---:|
| DESPESAS_REDE | 200 | 435 | 610.1 |
| TITULO_PAGAR | 200 | 70 | 159.5 |
| TITULO_RECEBER | 200 | 11 | 145.0 |
| MOVIMENTO_CONTA | 200 | 200 | 452.4 |
| CAIXA | 200 | 21 | 224.6 |
| CAIXA_APRESENTADO | 200 | 21 | 198.5 |

## Respostas obrigatórias

| Pergunta | Resposta |
|---|---|
| **Existem divergências?** | **Não** entre `summary.contasPagar` e `payables.buckets` (Δ = 0,00 em todos os casos A–F). |
| **Existem duplicidades?** | **Não detectadas** no agregador Finance Center. Despesas rede (435) vs FC filtradas (421) — diferença explicada por filtros/classificação, não duplicidade de chave. |
| **Existem inconsistências?** | **Não críticas.** CAIXA e CAIXA_APRESENTADO alinhados (21 turnos). MOVIMENTO_CONTA paginado (200/request) — FC agrega até 2000 registros. |
| **Existem lacunas?** | **Sim:** buckets aging CP especificados (Hoje/7d/15d/30d) ainda não implementados; fontes recebíveis auxiliares não integradas. |

## Paridade API (6 casos)

Todos os casos A–F: `parity_api_summary_vs_payables = []` (zero diferenças).
