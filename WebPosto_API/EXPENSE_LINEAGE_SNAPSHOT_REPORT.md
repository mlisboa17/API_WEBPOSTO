# EXPENSE LINEAGE SNAPSHOT — F03.1-B · Agente 8

## Configuração

| Parâmetro | Valor |
|-----------|-------|
| TTL | **300 segundos** |
| Diretório | `snapshots/expense_lineage/` |

## Chaves

| Chave | Conteúdo |
|-------|----------|
| `expense:lineage:*` | Linhas enriquecidas + cobertura |
| `expense:sources:*` | Distribuição origem real |
| `expense:categories:*` | Classificação + top descrições |
| `expense:operators:*` | Ranking operadores |
| `expense:pdvs:*` | Ranking PDVs |

## Endpoint

`GET /v1/financial/expenses/lineage/snapshot?dataInicial=&dataFinal=&domain=lineage`

Última coleta: **2026-06-09T20:16:19** · Cobertura: **100.0%**
