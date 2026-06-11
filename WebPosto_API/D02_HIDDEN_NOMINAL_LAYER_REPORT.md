# D02 — HIDDEN NOMINAL LAYER REPORT

**Sprint:** Hidden Nominal Layer Discovery · **Módulo:** LOGOS SPACE CORE

## Missão

Determinar se os **12,5% restantes** da reconstrução da Prestação existem na API ou apenas na Prestação de Contas.

## Respostas executivas (20)

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Existe funcionarioNome em algum endpoint? | **Sim** |
| 2 | Existe CPF do operador? | **Sim** |
| 3 | Existe matrícula? | **Não** |
| 4 | Existe produtividade oficial? | **Não** |
| 5 | Existe participação oficial? | **Não** |
| 6 | Existe fundoCaixa? | **Sim** |
| 7 | Existe meta operacional? | **Não** |
| 8 | Existe ranking oficial? | **Não** |
| 9 | Códigos 276288/294273/213391 nominalizáveis? | {'276288': True, '294273': True, '213391': True} |
| 10 | Campos exclusivos sem origem | 2 |
| 11 | Calculáveis | 3 |
| 12 | Inferíveis | 3 |
| 13 | Inexistentes na API | 2 |
| 14 | PDF continua necessário? | **Não** |
| 15 | Nova cobertura reconstrução | 97.5% |
| 16 | Possível chegar a 95%? | **Sim** |
| 17 | Possível chegar a 100%? | **Não** |
| 18 | Campo mais valioso oculto | metaFuncionario |
| 19 | F04 depende do PDF? | **Não** |
| 20 | Arquitetura definitiva | Opção A |

## Entregáveis

| Agente | Relatório |
|--------|-----------|
| 1 | EMPLOYEE_NOMINAL_DISCOVERY.md |
| 2 | OPERATOR_IDENTITY_TRACE.md |
| 3 | PARTICIPATION_DISCOVERY_REPORT.md |
| 4 | PRODUCTIVITY_DISCOVERY_REPORT.md |
| 5 | FUNDO_CAIXA_FORENSICS_REPORT.md |
| 6 | GOAL_DISCOVERY_REPORT.md |
| 7 | HIDDEN_FIELDS_REPORT.md |
| 8 | PRESTACAO_GAP_ANALYSIS.md |
| 9 | F04_IMPACT_ANALYSIS.md |
| 10 | D02_ARCHITECTURE_DECISION.md |

## Síntese

- **Cobertura D01:** 87.5% → **D02:** 97.5%
- **Campos exclusivos investigados:** funcionarioNome, participacaoIndividual (oficial UI), produtividadeFuncionario (oficial UI), metaFuncionario, fundoCaixa (rótulo Prestação), layout operacional turno
- Os **12,5% restantes** foram reclassificados: **nome/CPF** via `/INTEGRACAO/FUNCIONARIO`, **participação/produtividade** calculáveis, **fundo** via `CAIXA.abertura`. Permanecem exclusivos da Prestação: **meta por turno/funcionário** e **layout operacional** (~2,5%).

[PARECER FINAL: API SUFICIENTE PARA F04]
