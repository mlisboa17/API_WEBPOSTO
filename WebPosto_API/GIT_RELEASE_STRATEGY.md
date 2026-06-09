# GIT RELEASE STRATEGY — Release 2.0

**Data:** 2026-06-08 · Commit baseline `10917af`

---

## Estado atual

| Item | Valor |
|------|-------|
| Branch | `fix/pydantic-validators` |
| Commit | `10917af` — checkpoint baseline 2.0 |
| Remote `logos` | `https://github.com/mlisboa17/LogosPostos.git` (vazio) |
| Remote `origin` | `https://github.com/mlisboa17/API_WEBPOSTO.git` (legado) |
| Branch `main` | **Não existe localmente** |
| Branch `develop` | **Não existe** |
| Tags | Nenhuma `v2.0*` |

---

## Modelo de branches proposto (GitFlow adaptado)

```
main          ← releases estáveis (v2.0, v2.1…)
  │
develop       ← integração contínua pós-release
  │
feature/*     ← novas funcionalidades (F02, A04…)
release/*     ← hardening pré-tag (ex: release/2.0)
hotfix/*      ← correções urgentes em main
```

### Mapeamento imediato

| Branch atual | Ação recomendada |
|--------------|------------------|
| `fix/pydantic-validators` | Renomear → `release/2.0-prep` ou merge em `main` após remediação segurança |
| `claude/*` (remotes) | Arquivar / não usar em produção |

---

## Migração segura (passo a passo)

### Fase 1 — Remediação (bloqueante)

1. Remover `.env` do índice Git
2. Sanitizar arquivos com CHAVE hardcoded (ver SECURITY_AUDIT_REPORT)
3. Rotacionar chaves WebPosto expostas
4. Purga histórico Git (`git filter-repo`) **antes** do primeiro push público
5. Commit: `security: remove credentials from repository`

### Fase 2 — Estrutura de branches

```powershell
git checkout -b main
git merge fix/pydantic-validators
git checkout -b develop
git tag -a v2.0-baseline -m "Baseline 2.0 - Finance Center + Supplier Intelligence"
```

### Fase 3 — Primeiro push (manual, após aprovação)

```powershell
git push -u logos main --tags
```

### Fase 4 — Deprecar origin (opcional)

```powershell
git remote rename origin origin-legacy
git remote rename logos origin
```

---

## Tag obrigatória

| Tag | Condição | Status |
|-----|----------|--------|
| `v2.0-baseline` | Todos critérios aprovados | **NÃO APLICADA** — segurança RETIDA |

Comando (somente após aprovação):

```bash
git tag -a v2.0-baseline -m "Baseline 2.0 - Finance Center + Supplier Intelligence"
```

---

## Política de commits pós-release

- `main`: apenas merges de `release/*` ou `hotfix/*`
- `develop`: merges de `feature/*`
- Conventional commits recomendados: `feat:`, `fix:`, `docs:`, `security:`

---

## Checklist pré-push

- [ ] SECURITY_AUDIT → RISCO BAIXO ou SEGURO
- [ ] `.env` ausente do índice e histórico purgado
- [ ] README.md presente
- [ ] ARCHITECTURE_BASELINE_2.1.md presente
- [ ] Unit tests F01 PASS
- [ ] RELEASE_2_0_FINAL_REPORT → APROVADO

**Push recomendado:** **NÃO** — aguardar remediação P0.
