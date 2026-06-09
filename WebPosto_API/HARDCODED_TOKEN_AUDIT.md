# HARDCODED TOKEN AUDIT — Security P0

**Data:** 2026-06-08 · Pós-remediação commit `cbd1d32`

## Resumo

| Classificação | Antes | Depois |
|---------------|-------|--------|
| **SENSÍVEL / REMOVER** | 24 | **0** |
| **CONFIG_PLACEHOLDER** | 2 | **8** |
| **SEGURA** | 6 | 18+ |
| **Total ocorrências UUID (git grep)** | ~40 API | 18 (dados operacionais/teste) |

## Ocorrências remediadas (SENSÍVEL → sanitizado)

| Arquivo | Antes | Depois |
|---------|-------|--------|
| `postman_webposto_network_collection.json` | UUID real | `<WEBPOSTO_API_TOKEN>` |
| `scripts/exemplo_alterar_produto.py` | Hardcoded | `os.getenv("WEBPOSTO_API_KEY")` |
| `audit_raw_fields.py` | Fallback UUID | Fail se env vazio |
| `audit_token_scopes.py` | Fallback UUID | Fail se env vazio |
| `fuel_network_audit.py` | Fallback UUID | Fail se env vazio |
| `TESTAR_WEBPOSTO.ps1` | Hardcoded | `$env:WEBPOSTO_API_KEY` |
| `TESTAR_WEBPOSTO_V2.ps1` | Hardcoded | `$env:WEBPOSTO_API_KEY` |
| `CONTINUACAO.md` | UUID | `<WEBPOSTO_API_TOKEN>` |
| `EXEMPLO_ALTERAR_PRODUTO.md` | Bearer UUID | `<WEBPOSTO_API_TOKEN>` |
| `LEIA-ME_DASHBOARD.txt` | UUID | `<WEBPOSTO_API_TOKEN>` |
| `docs/filial_*.md`, `webposto_rede_endpoint_audit.md` | UUID | `<WEBPOSTO_API_TOKEN>` |
| `PROMPT_PARA_IA.txt` | Bearer UUID | `<WEBPOSTO_API_TOKEN>` |
| `OPERACOES_COMPLETAS_COM_TOKEN.md` | token parcial | `<REDACTED>` |
| `RESULTADO_API.json` | URLs com CHAVE | **Removido do Git** |
| `.env` / `WebPosto_API/.env` | Múltiplas chaves | **Removidos do Git** |

## UUIDs remanescentes (SEGURA — não são tokens API)

| Arquivo | Tipo |
|---------|------|
| `tests/conftest.py` | Fixtures de teste |
| `audit_*_results.json` | documento/vendaUuid operacional |
| `fuel_data_source_proof.md` | vendaUuid |
| `ARCHITECTURE.md` | Exemplo genérico cliente_id |
| `doc_*/customXml/*` | Metadado Office |

**Veredito:** Nenhum token WebPosto hardcoded no repositório.
