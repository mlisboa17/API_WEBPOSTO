# IA-2 — Onda 1 Artifact Audit

**Data:** 2026-06-13

## Artefatos obrigatórios

| Artefato | Disco | Git (HEAD) | Status |
|----------|-------|------------|--------|
| `app_core/filial_registry.py` | ✅ | ✅ `ef851ae` | **Presente** |
| `app_core/__init__.py` | ✅ | ❌ untracked | **Parcial** — local OK, não versionado |
| `scripts/sync_filiais_manifest.py` | ✅ | ✅ | **Presente** |
| `scripts/audit_app_core_filiais.py` | ✅ | ✅ | **Presente** |
| `frontend/data/filiais.json` | ✅ | ✅ | **Presente** (drift `generatedAt` unstaged) |
| `frontend/filiais.js` | ✅ | ✅ | **Presente** |
| `frontend/components/filiais.js` | ✅ | ✅ | **Presente** (adapter reexport) |
| `tests/unit/test_filial_registry_parity.py` | ✅ | ✅ | **Presente** |
| `APP_CORE_FILIAIS.md` | ✅ | ✅ | **Presente** |
| `ONDA_1_APP_CORE_FILIAIS_REPORT.md` | ✅ | ✅ | **Presente** |

## Relatórios IA-1 a IA-7

| Relatório | Disco | Git (HEAD) | Status |
|-----------|-------|------------|--------|
| `FILIAL_SOURCE_DISCOVERY_REPORT.md` (IA-1) | ✅ | ❌ | **Presente local, não commitado** |
| `FILIAL_REGISTRY_CORE_REPORT.md` (IA-2) | ✅ | ❌ | **Presente local, não commitado** |
| `FILIAIS_MANIFEST_SYNC_REPORT.md` (IA-3) | ✅ | ❌ | **Presente local, não commitado** |
| `FRONTEND_FILIAIS_ADAPTER_REPORT.md` (IA-4) | ✅ | ❌ | **Presente local, não commitado** |
| `FILIAIS_PARITY_TEST_REPORT.md` (IA-5) | ✅ | ❌ | **Presente local, não commitado** |
| `APP_CORE_FILIAIS_REPORT.md` (IA-6) | ✅ | ❌ | **Presente local, não commitado** |
| `APP_CORE_FILIAIS_QA_REPORT.md` (IA-7) | ✅ | ❌ | **Presente local, não commitado** |

## Conclusão IA-2

**Núcleo funcional da Onda 1:** completo e commitado.  
**Gap documental:** relatórios IA-1…IA-7 e `app_core/__init__.py` existem no disco mas **não entraram no commit** `ef851ae`.
