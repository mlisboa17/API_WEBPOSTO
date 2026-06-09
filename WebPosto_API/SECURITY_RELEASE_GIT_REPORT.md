# SECURITY RELEASE GIT REPORT — Security P0

**Data:** 2026-06-08

## Commits

| Hash | Mensagem |
|------|----------|
| `f7ca944` | checkpoint: baseline 2.0 after F01.4-D… *(hash reescrito)* |
| `cbd1d32` | security: remove exposed credentials and sanitize release baseline |

## Branch

`fix/pydantic-validators`

## Remotes (re-adicionados pós filter-repo)

| Remote | URL |
|--------|-----|
| `logos` | https://github.com/mlisboa17/LogosPostos.git |
| `origin` | https://github.com/mlisboa17/API_WEBPOSTO.git (legado) |

## Alterações no commit de segurança

- 33 arquivos alterados
- `.env`, `.env.production`, `WebPosto_API/.env` deletados do Git
- `RESULTADO_API.json` removido
- `.gitignore` + `.env.example` atualizados
- Scripts/docs sanitizados

## Tag

**Não criada** — aguardar rotação de chaves WebPosto (ver `SECRET_ROTATION_PLAN.md`).

## Push

**NÃO executado** (conforme sprint).

Comando futuro (após rotação + aprovação):

```bash
git checkout -b main
git push -u logos main --tags
```

**Veredito Git:** Commit seguro criado · histórico purgado · push pendente rotação.
