# Artifact Audit — F05.1 Pre-Commit

## Procurado no commit `6d345ed`

| Padrão | No commit? | Veredito |
|--------|------------|----------|
| `*.tmp` / `*.cache` / `*.bak` | Não | OK |
| `__pycache__` / `*.pyc` | Não | OK |
| `node_modules` | Não | OK |
| `coverage` / `htmlcov` | Não | OK |
| `.claude` / `worktrees` | Não (só unstaged) | OK |
| `*.log` (15 no repo) | Não no commit | IGNORAR local |
| `p0_1b_temporal_run.log` etc. | Não no commit | REMOVER futuro (dívida) |
| JSON gigante não oficial | Não | OK |

## Snapshot no commit

| Arquivo | Tamanho | Veredito |
|---------|---------|----------|
| `snapshots/executive_decision_engine/decision_engine_2026-06-01_2026-06-07_all.json` | ~11k linhas | **MANTER** — evidência homologada (padrão sprint) |
| `scripts/f05_1_executive_decision_engine.json` | Audit oficial | **MANTER** |

## Classificação final

- **MANTER:** 25 arquivos do commit
- **REMOVER:** nada do commit (logs locais fora do escopo)
- **IGNORAR:** worktrees Claude unstaged
