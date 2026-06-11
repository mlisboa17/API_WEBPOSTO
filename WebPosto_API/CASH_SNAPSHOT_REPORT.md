# CASH SNAPSHOT REPORT — F03

## Parâmetros

| Parâmetro | Valor |
|-----------|-------|
| TTL | **300s** (5 min) |
| Estratégia | Snapshot-First + Background Refresh |
| Store | `SnapshotStore` memória + disco |

## Chaves

| Chave | Conteúdo |
|-------|----------|
| `cash:alerts:*` | Motor de alertas |
| `cash:risk:*` | Risk score consolidado |
| `cash:operators:*` | Analytics operadores |
| `cash:pdvs:*` | Analytics PDVs |
| `cash:turns:*` | Analytics turnos |
| `cash:operations:all:*` | Payload master |

## Stale-while-revalidate

1. `load_stale()` serve cache expirado
2. Dispara `refresh_background()` assíncrono
3. UI responde sub-segundo com snapshot existente

**Diretório:** `snapshots/cash_operations/`
