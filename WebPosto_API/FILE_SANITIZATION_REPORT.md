# FILE SANITIZATION REPORT — Security P0

**Data:** 2026-06-08

## Arquivos sanitizados (substituição)

| Arquivo | Ação | Placeholder |
|---------|------|-------------|
| `postman_webposto_network_collection.json` | Substituído | `<WEBPOSTO_API_TOKEN>` |
| `scripts/exemplo_alterar_produto.py` | Refatorado | env var |
| `audit_raw_fields.py` | Refatorado | env obrigatório |
| `audit_token_scopes.py` | Refatorado | env obrigatório |
| `fuel_network_audit.py` | Refatorado | env obrigatório |
| `TESTAR_WEBPOSTO.ps1` | Refatorado | `$env:WEBPOSTO_API_KEY` |
| `TESTAR_WEBPOSTO_V2.ps1` | Refatorado | `$env:WEBPOSTO_API_KEY` |
| `CONTINUACAO.md` | Redact | `<WEBPOSTO_API_TOKEN>` |
| `EXEMPLO_ALTERAR_PRODUTO.md` | Redact | `<WEBPOSTO_API_TOKEN>` |
| `LEIA-ME_DASHBOARD.txt` | Redact | `<WEBPOSTO_API_TOKEN>` |
| `docs/filial_audit_5256_7_9.md` | Redact | `<WEBPOSTO_API_TOKEN>` |
| `docs/filial_coverage_report.md` | Redact | `<WEBPOSTO_API_TOKEN>` |
| `docs/webposto_rede_endpoint_audit.md` | Redact | `<WEBPOSTO_API_TOKEN>` |
| `PROMPT_PARA_IA.txt` | Redact | `<WEBPOSTO_API_TOKEN>` |
| `OPERACOES_COMPLETAS_COM_TOKEN.md` | Redact | `<REDACTED>` |
| `diagnostico_resultado.json` | Redact | `<REDACTED>` |

## Arquivos removidos do Git

| Arquivo | Motivo |
|---------|--------|
| `WebPosto_API/RESULTADO_API.json` | Artefato de probe com URLs + CHAVE |
| `.env` | Segredos reais (WebPosto + JWT + DB) |
| `.env.production` | Config produção |
| `WebPosto_API/.env` | 4 chaves WebPosto |

## Não alterados (sem credenciais)

- Snapshots operacionais (`filiaisSemToken` = metadado, não chave)
- Scripts F01 (`cfg.webposto_api_key` via config — correto)
- `src/` serviços oficiais

**Total arquivos tocados:** 33 (commit `cbd1d32`)
