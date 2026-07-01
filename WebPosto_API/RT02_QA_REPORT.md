# RT02_QA_REPORT — IA-8

**Data:** 2026-06-14 | **Gate:** RT-02 Performance & Operabilidade

## Checklist

| Critério | Resultado |
|---|---|
| 0 quebra funcional | ✅ Regressão 5/5 |
| 0 perda lineage | ✅ `has_lineage: true` overview/expenses/stock |
| 0 dados sintéticos (fluxo normal) | ✅ snapshots homologados |
| 0 timeout > 22s | ✅ max 8,02s (sales) |
| 0 travamento API | ✅ tasks canceladas pós-timeout |
| 0 impacto F07 | ✅ cockpit 0,04s |
| 0 impacto F08 | ✅ cockpits 0,24s / 0,75s |

## Critérios de aceite RT-02

| Meta | Resultado |
|---|---|
| overview < 3s | ✅ 0,02s |
| expenses < 3s | ✅ 0,01s |
| stock < 8s | ✅ 0,02s |
| health 200 | ✅ |
| sales funcional | ✅ 8,02s fallback |
| snapshot fallback preservado | ✅ |
| lineage preservado | ✅ |

## Respostas executivas (20)

| # | Resposta |
|---|---|
| 1 | Mais lento RT-01: **`/v1/stock`** (44,9s) |
| 2 | Causa raiz: **live-first + WebPosto serial multi-filial** |
| 3 | Overview < 3s? | **Sim** (0,02s) |
| 4 | Expenses < 3s? | **Sim** (0,01s) |
| 5 | Stock < 8s? | **Sim** (0,02s) |
| 6 | Snapshot fallback acionado? | **Sim** (sales); snapshot_first nos 3 corrigidos |
| 7 | Circuit breaker funcionou? | **Sim** (stock + sales gates) |
| 8 | API saudável? | **Sim** health 200 |
| 9 | Perda lineage? | **Não** |
| 10 | Regressão? | **Não** |
| 11 | Sales estável? | **Sim** 8,02s P0 |
| 12 | Financeiro operacional? | **Sim** (período homologado) |
| 13 | Combustíveis operacional? | **Sim** |
| 14 | Endpoint crítico restante? | Sales ainda live-first ~8s (melhoria futura opcional) |
| 15 | Dependência live obrigatória? | **Não** com snapshot homologado |
| 16 | Gargalos conhecidos? | Primeira carga stock sem snapshot homologado |
| 17 | Endpoints corrigidos? | **3** |
| 18 | RT-01 válido? | **Sim**, atualizado com RT-02 |
| 19 | Mais utilizável? | **Sim** |
| 20 | Status OPERACIONAL? | **Sim** para período homologado 2026-06-01→07 |

```text
[PARECER FINAL: RT-02 PERFORMANCE & OPERABILIDADE APROVADA]
```
