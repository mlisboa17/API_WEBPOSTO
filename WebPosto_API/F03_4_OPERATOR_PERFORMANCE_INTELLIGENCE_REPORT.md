# F03.4 — OPERATOR PERFORMANCE INTELLIGENCE

## Respostas executivas

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Melhor operador | **276288** |
| 2 | Pior operador | **294273** |
| 3 | Mais melhorou 90d | **None** |
| 4 | Mais piorou | **None** |
| 5 | Maior saldo devedor | **294273** |
| 6 | Maior saldo credor | **276288** |
| 7 | Melhor PDV | **56764** |
| 8 | Pior PDV | **54193** |
| 9 | Melhor turno | **2** |
| 10 | Pior turno | **1** |
| 11 | Operadores críticos | **6** |
| 12 | Operadores excelentes | **0** |
| 13 | Score médio rede | **40.48** |
| 14 | Melhora operacional 90d | **None** |
| 15 | PDV 54193 crítico? | **True** |
| 16 | PDV 15880 crítico? | **True** |
| 17 | Operador 276288 crítico? | **False** |
| 18 | Operador 294273 crítico? | **True** |
| 19 | Snapshot SLA | **True** (0.0 ms) |
| 20 | Pronto F04? | **True** |
| 21 | Performance individual ou contexto? | **MISTA** |
| 22 | Bons em múltiplos PDVs/turnos | **[]** |
| 23 | Só performam em contexto específico | **[299151, 294273, 178278, 158924, 276288]** |
| 24 | PDVs que prejudicam operadores | **[15880, 54193]** |
| 25 | Turnos que prejudicam operadores | **[]** |
| 26 | Ranking bruto ou ajustado? | **DUAL_BRUTO_E_AJUSTADO** |

## Critérios de aceite

| Meta | Resultado |
|------|-----------|
| Paridade 0,00 | True |
| Snapshot < 500ms | True (0.0 ms) |
| 100% classificados | True |

## Entregáveis

- `src/services/operator_performance_service.py`
- `src/services/operator_performance_snapshot_service.py`
- `src/interfaces/http/routes/operator_performance.py`
- `src/services/operator_context_attribution_service.py`
- `frontend/pages/operatorPerformance.js`
- 12 relatórios MD + DW model

[PARECER FINAL: APROVADO PARA F04]
