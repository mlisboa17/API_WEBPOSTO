# IA-5 — Registry Runtime Audit

**Arquivo:** `app_core/filial_registry.py`  
**Data:** 2026-06-13

## Funções obrigatórias

| Função | Existe | Runtime (cwd=WebPosto_API) |
|--------|--------|------------------------------|
| `list_filiais()` | ✅ | 12 filiais |
| `get_filial(empresa_codigo)` | ✅ | `get_filial('5256')` → POSTO BR SHOPPING |
| `is_filial_ativa(empresa_codigo)` | ✅ | `is_filial_ativa('5256')` → `True` |
| `get_filiais_ativas()` | ✅ | 10 filiais |

## Fontes de dados

| Fonte | Usada |
|-------|-------|
| `FILIAIS_MASTER` (`src/domain/entities/filial_master.py`) | ✅ |
| Snapshots executive (`snapshots/executive/*.json`) | ✅ (somente leitura local) |
| WebPosto live (HTTP/API) | ❌ **Não** |

## WebPosto live

Busca em `filial_registry.py`: apenas string documental `"sem WebPosto live"`.  
Nenhum import de `webposto_client`, `requests`, `httpx`.

## Snapshot observado na auditoria

`discovery_summary()` reportou **8** códigos ativos no snapshot mais recente (`2026-06-12_2026-06-12_all.json`), vs fallback de 10.  
Isso **não invalida** o registry — `ativa` deriva de `FILIAIS_MASTER` + `statusEvidencia`, não do snapshot.

## Conclusão IA-5

Registry **operacional**, funções mínimas presentes, dados válidos, **sem WebPosto live**.
