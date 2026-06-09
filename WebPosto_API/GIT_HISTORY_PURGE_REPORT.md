# GIT HISTORY PURGE REPORT — Security P0

**Data:** 2026-06-08

## Ferramenta

| Item | Valor |
|------|-------|
| Ferramenta | `git-filter-repo` (via `pip install git-filter-repo`) |
| Versão | `a40bce548d2c` |
| Duração | ~16,5 segundos |
| Commits reescritos | 9 |

## Comando executado

```bash
python -m git_filter_repo \
  --invert-paths \
  --path .env \
  --path .env.production \
  --path WebPosto_API/.env \
  --path WebPosto_API/RESULTADO_API.json \
  --replace-text filter-repo-replacements.txt \
  --force
```

## Paths removidos do histórico

- `.env` (incluía JWT private key, AES_KEY, SECRET_KEY, DB_PASSWORD)
- `.env.production`
- `WebPosto_API/.env` (4 chaves WebPosto)
- `WebPosto_API/RESULTADO_API.json`

## Substituições globais no histórico

| Original | Substituído |
|----------|-------------|
| UUID VIP WebPosto | `<WEBPOSTO_API_TOKEN>` |
| UUID Casa Caiada | `<WEBPOSTO_API_KEY_CASA_CAIADA>` |
| UUID Dev | `<WEBPOSTO_API_KEY_DEV>` |

## Pós-purge

| Check | Resultado |
|-------|-----------|
| `git grep 4d6bbe21` | **0 ocorrências** |
| `git grep eabd1f99` | **0 ocorrências** |
| `git grep "BEGIN PRIVATE KEY"` | **0 ocorrências** |
| Remotes removidos pelo filter-repo | Re-adicionados `origin` + `logos` |
| Novo HEAD checkpoint | `f7ca944` (hash reescrito) |
| Novo HEAD security | `cbd1d32` |

## Alternativa documentada (não usada)

Se `git-filter-repo` indisponível:

```bash
# BFG Repo-Cleaner
bfg --delete-files .env
bfg --replace-text replacements.txt

# ou git filter-branch (legado, lento)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env WebPosto_API/.env" HEAD
```

**Veredito:** Histórico Git **purgado com sucesso**.
