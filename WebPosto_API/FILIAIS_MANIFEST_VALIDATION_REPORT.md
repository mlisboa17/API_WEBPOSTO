# IA-4 — Manifest Audit

**Arquivo:** `frontend/data/filiais.json`  
**Data:** 2026-06-13

## Metadados

| Campo | Valor |
|-------|-------|
| `source` | `app_core.filial_registry` |
| `count` | **12** |
| `activeCount` | **10** |
| `filiais.length` | **12** (consistente com `count`) |

## Validações

| Regra | Resultado |
|-------|-----------|
| Códigos duplicados (`empresaCodigo`) | **0** |
| `empresaCodigo` ausente | **0** |
| `statusEvidencia` inválido | **0** — apenas `COMPROVADA` e `PENDENTE_EVIDENCIA` |
| `PENDENTE_EVIDENCIA` com `ativa: true` | **0** |
| Formato estrito (9 campos por row) | ✅ |

## Distribuição

| statusEvidencia | Qtd | ativa=true |
|-----------------|-----|------------|
| COMPROVADA | 11 | 10 |
| PENDENTE_EVIDENCIA | 1 (AUTO POSTO GLOBO) | 0 |

## Drift Git

Após execução de `sync_filiais_manifest.py` durante auditoria:

```text
git diff frontend/data/filiais.json → 1 linha (generatedAt)
```

Manifest **conteúdo funcional idêntico**; apenas timestamp regenerado. Não commitado.

## Conclusão IA-4

Manifest **válido e consistente** com registry Python. Drift mínimo operacional no `generatedAt`.
