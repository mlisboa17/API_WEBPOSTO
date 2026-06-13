# IA-3 — Python Import Audit

**Data:** 2026-06-13

## Imports analisados

### `app_core/filial_registry.py`

```python
from src.domain.entities.filial_master import FILIAIS_MASTER, FilialMaster
```

- Tipo: **import absoluto** (depende de `src` no PYTHONPATH)
- Sem imports relativos
- Sem chamadas WebPosto/HTTP

### `tests/unit/test_filial_registry_parity.py`

```python
from app_core.filial_registry import discovery_summary, get_filiais_ativas, list_filiais
```

- Tipo: **import absoluto** (depende de cwd = `WebPosto_API/`)

### Scripts (`sync_filiais_manifest.py`, `audit_app_core_filiais.py`)

```python
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
```

- Inserem raiz do projeto no `sys.path` antes de importar — **padrão correto**.

## Matriz de execução

| Cenário | cwd | Comando | Resultado |
|---------|-----|---------|-----------|
| A | `WebPosto_API/` | `python -c "import app_core.filial_registry"` | ✅ OK |
| B | `WebPosto_API/` | `python -m pytest tests/unit/test_filial_registry_parity.py` | ✅ 6/6 PASS |
| C | `WebPosto_API/` | `python scripts/audit_app_core_filiais.py` | ✅ OK |
| D | `WebPosto_API/` | `python scripts/sync_filiais_manifest.py` | ✅ OK |
| E | `Api_WebPosto/` (pai) | `python -c "import app_core.filial_registry"` | ❌ `ModuleNotFoundError: app_core` |
| F | `WebPosto_API/` | `python app_core/filial_registry.py` | ❌ `ModuleNotFoundError: src` |

## Classificação do `ModuleNotFoundError`

**Resposta: B + C** — execução incorreta + PYTHONPATH/cwd ausente.

| Opção | Aplica? |
|-------|---------|
| A) bug real de estrutura | ❌ Não — estrutura alinhada ao monorepo (`WebPosto_API/` como raiz Python) |
| B) execução incorreta | ✅ Sim — rodar arquivo como script ou a partir do diretório pai |
| C) PYTHONPATH ausente | ✅ Sim — `src` e `app_core` exigem cwd=`WebPosto_API/` ou `sys.path.insert` |
| D) estrutura incorreta | ❌ Não |

## Observações

- `pytest.ini` não define `pythonpath`; funciona porque pytest é invocado de `WebPosto_API/`.
- `tests/conftest.py` **não** adiciona raiz ao path; testes Onda 1 dependem do cwd padrão.
- `app_core/__init__.py` existe localmente mas não está no Git; import ainda funciona via namespace/submódulo.

## Recomendação (sem alterar código nesta auditoria)

Documentar que comandos devem rodar com:

```powershell
cd WebPosto_API
python scripts/sync_filiais_manifest.py
python -m pytest tests/unit/test_filial_registry_parity.py -q
```

Opcional futuro: commit de `__init__.py` + `pythonpath = .` no pytest.
