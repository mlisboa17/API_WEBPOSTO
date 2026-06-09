# SECURITY AUDIT REPORT — Release 2.0

**Data:** 2026-06-08 · Commit `10917af` · Branch `fix/pydantic-validators`

## Escopo

Auditoria estática do repositório `WebPosto_API` (863 arquivos rastreados) buscando padrões:

`token`, `secret`, `apikey`, `api_key`, `password`, `bearer`, `authorization`, `jwt`, `client_secret`, `CHAVE`.

---

## Resumo executivo

| Métrica | Valor |
|---------|-------|
| **Credenciais / referências sensíveis encontradas** | **32** |
| **Protegidas (env / config runtime)** | **8** |
| **Expostas no Git (rastreadas ou hardcoded)** | **24** |
| **Risco final** | **RISCO ALTO** |

**Veredito:** **RETIDO** — critério de rejeição da sprint atendido (*existir credencial exposta*).

---

## Classificação por achado

### RISCO ALTO

| # | Arquivo | Achado | Ação obrigatória |
|---|---------|--------|------------------|
| 1 | `WebPosto_API/.env` | **Rastreado no Git** com `WEBPOSTO_API_KEY` + 3 chaves por filial (VIP, Casa Caiada, Dev) | `git rm --cached`, rotação de chaves, BFG/filter-repo no histórico antes do push público |
| 2 | `postman_webposto_network_collection.json` | Chave UUID em `value` (variável Postman) | Substituir por `{{CHAVE}}` placeholder; nunca commitar valor real |
| 3 | `RESULTADO_API.json` | URLs com `CHAVE=` em 12+ endpoints | Remover do repositório ou sanitizar |
| 4 | `scripts/exemplo_alterar_produto.py` | `API_KEY = "…"` hardcoded | Usar `os.getenv("WEBPOSTO_API_KEY")` |
| 5 | `audit_raw_fields.py`, `audit_token_scopes.py`, `fuel_network_audit.py` | Fallback hardcoded se env ausente | Remover default; falhar se env vazio |
| 6 | `CONTINUACAO.md`, `EXEMPLO_ALTERAR_PRODUTO.md` | Bearer / CHAVE em exemplos | Redact ou mover para `.env.example` |
| 7 | `docs/filial_*.md`, `docs/webposto_rede_endpoint_audit.md` | Token ativo documentado | Redact UUID nos docs públicos |
| 8 | `TESTAR_WEBPOSTO.ps1`, `TESTAR_WEBPOSTO_V2.ps1`, `LEIA-ME_DASHBOARD.txt` | Referências a chave ativa | Sanitizar antes do push |

### RISCO MÉDIO

| # | Arquivo | Achado |
|---|---------|--------|
| 9 | `.env` local (não staged no último commit parcial) | Ainda presente no working tree com valores reais |
| 10 | `snapshots/**/*.json` | Dados operacionais de filiais (sem chave, mas PII operacional) |
| 11 | `audit_expenses_webposto_result.json`, `diagnostico_resultado_rede.json` | Dados de rede / filiais |
| 12 | URL interna `web.qualityautomacao.com.br` | Exposição de infra parceiro (esperado, não secreto) |

### RISCO BAIXO

| # | Arquivo | Achado |
|---|---------|--------|
| 13 | Scripts F01 (`validate_f01_*.py`, `audit_a03_*.py`) | Usam `cfg.webposto_api_key` via `load_core_config()` — **correto** |
| 14 | `src/core/config.py` | Lê `WEBPOSTO_API_KEY` de env — **correto** |
| 15 | `src/infrastructure/security/passwords.py` | Hash de senha (sem valor exposto) — **SEGURO** |
| 16 | Snapshots executive | Campo `filiaisSemToken` (metadado, não credencial) — **SEGURO** |

### SEGURO

- `.gitignore` raiz inclui `.env`, `.venv/`, `node_modules/`
- `.env.example` usa placeholders (`sua_chave_api_rest_aqui`)
- Serviços oficiais F01 não persistem CHAVE em código
- JWT/Bearer ausentes na camada HTTP interna (8040)

---

## Validações solicitadas

| Item | Status |
|------|--------|
| `.env` fora do Git | **FALHA** — `WebPosto_API/.env` rastreado desde commit `b6a2a0e` |
| Credenciais não commitadas | **FALHA** — `.env` + 15 arquivos com UUID WebPosto |
| URLs internas | OK documentadas; sem impacto de segurança direto |
| Tokens WebPosto | **EXPOSTOS** — múltiplas chaves no `.env` versionado |
| Tokens Vibra | Não encontrados no repositório |
| Chaves de desenvolvimento | `WEBPOSTO_API_KEY_POSTO_VIP_DEV` no `.env` versionado |
| Usuários de teste | Não identificados em arquivos rastreados |

---

## Plano de remediação (pré-push)

1. `git rm --cached WebPosto_API/.env` + confirmar `.gitignore`
2. Rotacionar **todas** as chaves WebPosto expostas (Quality Automação)
3. Sanitizar ou remover: `RESULTADO_API.json`, `postman_webposto_network_collection.json`, scripts/docs com UUID
4. Executar `git filter-repo` ou BFG para purgar histórico (`.env` existe desde antes do checkpoint)
5. Re-executar esta auditoria → meta **RISCO BAIXO** ou **SEGURO**

---

## Respostas obrigatórias

1. **Credenciais encontradas:** 32 referências sensíveis
2. **Protegidas:** 8 (runtime via env/config sem hardcode)
3. **Expostas:** 24 (`.env` versionado + hardcodes + artefatos JSON/MD)
4. **Risco final:** **RISCO ALTO**
