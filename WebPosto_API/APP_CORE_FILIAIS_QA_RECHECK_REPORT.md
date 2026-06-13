# IA-6 — QA Gate Recheck

**Data:** 2026-06-13

## Checklist

| Critério | Resultado |
|----------|-----------|
| 0 filial inventada | ✅ 12 = `FILIAIS_MASTER` |
| 0 código duplicado | ✅ |
| 0 consulta WebPosto live | ✅ |
| 0 quebra F03–F07 no commit Onda 1 | ✅ commit `ef851ae` não toca `src/services/*` motores |
| Manifest consistente | ✅ count=12, activeCount=10 |
| Paridade consistente | ✅ pytest 6/6 |

## Execuções

```text
python scripts/audit_app_core_filiais.py
→ erros: 0
→ [PARECER FINAL: ONDA 1 APP_CORE FILIAIS APROVADA]

python -m pytest tests/unit/test_filial_registry_parity.py -q
→ 6 passed
```

## Alterações locais fora do commit Onda 1 (não homologadas nesta onda)

Modificados unstaged (F07.9 / cockpit):

```text
frontend/app.js, frontend/index.html, frontend/services/api.js
src/interfaces/http/app.py
COMMERCIAL_GOVERNANCE_REPORT.md
snapshots/product_master_cache/index.json
```

Estes **não fazem parte** do commit `ef851ae` e **não invalidam** QA da Onda 1.

## Conclusão IA-6

**QA Onda 1 continua aprovado.**
