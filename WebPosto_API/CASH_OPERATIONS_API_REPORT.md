# CASH OPERATIONS API REPORT — F03

**Prefixo:** `/api/v1/cash/operations`  
**Formato:** REST JSON (`WebPostoResponse` pattern)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/summary` | KPIs rede + risk score |
| GET | `/alerts` | Alertas ativos + listas vermelhas |
| GET | `/operators` | Rankings Top 20 |
| GET | `/pdvs` | Terminais + alvos críticos |
| GET | `/turns` | Matriz por turno |
| GET | `/risk-score` | Score consolidado + sub-scores |
| GET | `/snapshot` | Master snapshot (stale OK) |
| POST | `/refresh` | Background refresh |

**Query params:** `dataInicial`, `dataFinal`, `empresaCodigo`

**Restrição:** read-only — não altera tabelas WebPosto originais.
