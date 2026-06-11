# PERFORMANCE API — F03.4 · Agente 8

## Rotas

| Método | Rota | Status |
|--------|------|--------|
| GET | `/api/v1/performance/operators` | Implementado |
| GET | `/api/v1/performance/pdvs` | Implementado |
| GET | `/api/v1/performance/turns` | Implementado |
| GET | `/api/v1/performance/summary` | Implementado |
| GET | `/api/v1/performance/snapshot` | Implementado |
| POST | `/api/v1/performance/refresh` | Implementado |

## Contrato

- Query: `dataInicial`, `dataFinal`, `empresaCodigo` (opcional)
- Resposta inclui `snapshot.hit` e `snapshot.stale`
