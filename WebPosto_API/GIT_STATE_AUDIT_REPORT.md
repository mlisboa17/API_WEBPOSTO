# IA-1 — Git State Audit

**Data:** 2026-06-13  
**Repositório:** `Api_WebPosto` (subdir `WebPosto_API/`)

## Comandos executados

```text
git branch --show-current
git status
git log --oneline -10
Test-Path .git/index.lock / ../.git/index.lock
Get-Process git
git rev-parse HEAD origin/feature/app-core-filiais-registry
```

## Respostas

| Item | Resultado |
|------|-----------|
| **Branch atual** | `feature/app-core-filiais-registry` |
| **Último commit** | `ef851ae` — `feat(app-core): create filial registry and manifest synchronization` |
| **Arquivos staged** | **Nenhum** |
| **Arquivos untracked** | **Sim** — 30+ arquivos (relatórios IA, F07.9, `app_core/__init__.py`, snapshots, etc.) |
| **Arquivos modificados (unstaged)** | **Sim** — 8 paths (F07.9/cockpit, worktrees Claude, cache) + drift em `frontend/data/filiais.json` |

## Commit Onda 1 (`ef851ae`) — conteúdo real

9 arquivos commitados:

```text
WebPosto_API/APP_CORE_FILIAIS.md
WebPosto_API/ONDA_1_APP_CORE_FILIAIS_REPORT.md
WebPosto_API/app_core/filial_registry.py
WebPosto_API/frontend/components/filiais.js
WebPosto_API/frontend/data/filiais.json
WebPosto_API/frontend/filiais.js
WebPosto_API/scripts/audit_app_core_filiais.py
WebPosto_API/scripts/sync_filiais_manifest.py
WebPosto_API/tests/unit/test_filial_registry_parity.py
```

**Não commitado:** `app_core/__init__.py` (existe localmente, untracked).

## Push / remote

```text
HEAD     = ef851aeb6dafa5ee010db5dd786e9db4ef53326c
origin   = ef851aeb6dafa5ee010db5dd786e9db4ef53326c
Branch tracking: up to date with origin/feature/app-core-filiais-registry
```

## Lock Git

| Verificação | Resultado |
|-------------|-----------|
| `WebPosto_API/.git/index.lock` | Ausente |
| `Api_WebPosto/.git/index.lock` | Ausente |
| Processos `git` presos | **Nenhum** |

## Erros operacionais observados

| Erro | Diagnóstico |
|------|-------------|
| `fatal: : '' is outside repository` | **Operacional** — típico de path/cwd incorreto no PowerShell (repo root é `Api_WebPosto`, cwd deve ser `WebPosto_API/` ou path completo) |
| `fatal: Unable to create .git/index.lock` | **Operacional transitório** — lock não existe mais; commit `ef851ae` foi criado com sucesso depois |

## Conclusão IA-1

O commit da Onda 1 **existe e está no remote**. Erros Git anteriores foram **operacionais**, não estruturais. Há pendências locais **fora do escopo Onda 1** (F07.9, worktrees) e **dentro do escopo** (`__init__.py`, relatórios IA untracked, `generatedAt` do manifest).
