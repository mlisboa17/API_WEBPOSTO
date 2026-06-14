# IA-1 — Filial Source Discovery

## Fontes mapeadas

| Fonte | Path | Registros |
|-------|------|-----------|
| Master Python | `src/domain/entities/filial_master.py` | 12 |
| Frontend hardcoded (legado) | `frontend/components/filiais.js` | 12 (agora adapter) |
| Registry Onda 1 | `app_core/filial_registry.py` | 12 |
| Manifest | `frontend/data/filiais.json` | 12 |
| Snapshot executive | `snapshots/executive/*.json` → `kpis.empresasCodigos` | 10 códigos ativos |

## Respostas

- **Filiais oficiais:** 12 (`FILIAIS_MASTER`)
- **Ativas em registry:** 10 (status CONFIRMADA + `empresaCodigo` definido)
- **Ativas em snapshot:** 10 (`5256,5333,5555,5556,5557,5559,5560,11495,46433,74014`)
- **Divergentes:** `5558` (INATIVA, fora snapshot) · `AUTO POSTO GLOBO` (sem COD WEB)
- **Sem CNPJ:** 0
- **Sem Nome Fantasia:** 0
- **Duplicidade de código:** 0

## Pendências

- `AUTO POSTO GLOBO` → `PENDENTE_EVIDENCIA` (sem `empresaCodigo`/`codWeb`)
- `POSTO REAL` (5558) → `INATIVA` / encerrada 2026-05-20
