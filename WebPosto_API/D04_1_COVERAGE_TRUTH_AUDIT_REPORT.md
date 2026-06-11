# D04.1 — COVERAGE TRUTH AUDIT REPORT

Missão adversarial: **tentar derrubar o D04** · Baseline **2026-06-01 → 2026-06-07** · Filiais **11495, 5555**

## Respostas executivas (20)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | D04 continua válido? | **Sim** (PARCIALMENTE CONFIRMADO) |
| 2 | Trust 100 é real? | **Não** |
| 3 | Trust 100 é apenas técnico? | **Sim** |
| 4 | Cobertura real negócio | **55.78%** |
| 5 | Cobertura real pessoas | **66.67%** |
| 6 | Cobertura real financeira | **33.33%** |
| 7 | Cobertura real operacional | **58.33%** |
| 8 | Cobertura real prestação | **97.5%** |
| 9 | Campos ocultos | funcionarioNome, participacaoIndividual, produtividadeFuncionario, metaFuncionario, fundoCaixa, layoutOperacionalTurno, autorizacaoGerencial |
| 10 | Indicadores inferidos | participacaoIndividual, produtividadeFuncionario, fundoCaixa (rótulo UI), growthScore (F04.7 proxy), goalPercentual parcial |
| 11 | Indicadores comprovados | Cash paridade Δ=0, Receita operacional F04.3, Join venda-operador D01, Finance center despesas/títulos snapshot, Employee ledger F03.3 |
| 12 | Indicadores rebaixados | People Coverage D04, Sales Coverage D04, Financial Coverage D04, Corporate Trust D04 (executivo) |
| 13 | Indicadores bloqueados | metaFuncionario / Metas operacionais, participacaoIndividual oficial UI |
| 14 | Corporate Score confiável | **Não** |
| 15 | Executive Score confiável | **Não** |
| 16 | People Score confiável | **Não** |
| 17 | Logos enxerga 100% operação | **Não** |
| 18 | Logos enxerga 100% pessoas | **Não** |
| 19 | Pronto decisões automatizadas | **Não** |
| 20 | D04 confirmado ou superestimado | **SUPERESTIMADO** |

## Trust Score Challenge

| Camada | Score |
|--------|-------|
| Técnico (D04) | **100.0** |
| Negócio | **55.78** |
| Executivo | **33.33** |

## O que sabemos / achamos / não sabemos

**Sabemos:** Paridade Δ=0 · joins D01 comprovados · finance/cash/vendas nos snapshots

**Achamos que sabemos (mas é parcial):** People100 = Operadores no snapshot F04 — não equipe completa nem métricas gerenciais UI · Prestação = Campos mapeados — 2 exclusivos UI sem API · 3 inferidos

**Não sabemos:** autorizacaoGerencial, lmcDetalhe, metaFuncionarioTurno, redeCompleta

## Relatórios IA

- TECHNICAL_COVERAGE_AUDIT.md (IA-1)
- BUSINESS_COVERAGE_AUDIT.md (IA-2)
- PRESTACAO_GAP_AUDIT.md (IA-3)
- PEOPLE_COVERAGE_CHALLENGE_REPORT.md (IA-4)
- FINANCIAL_GAP_REPORT.md (IA-5)
- OPERATIONAL_GAP_REPORT.md (IA-6)
- HIDDEN_ENDPOINT_DISCOVERY_REPORT.md (IA-7)
- TRUST_SCORE_CHALLENGE_REPORT.md (IA-8)
- D04_CERTIFICATION_REPORT.md (IA-9)

---

[PARECER FINAL: D04 SUPERESTIMOU A COBERTURA]
