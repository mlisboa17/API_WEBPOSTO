# REPOSITORY CLEANUP REPORT — Release 2.0

**Data:** 2026-06-08 · 863 arquivos rastreados em `WebPosto_API/`

## Inventário por categoria

| Categoria | Arquivos | % |
|-----------|----------|---|
| `src/` | 240 | 27,8% |
| Relatórios `.md` | 202 | 23,4% |
| Outros (config, raiz, legado) | 211 | 24,4% |
| `scripts/` | 73 | 8,5% |
| `frontend/` | 45 | 5,2% |
| `tests/` | 35 | 4,1% |
| `snapshots/` | 28 | 3,2% |
| `dw/ddl/` | 21 | 2,4% |
| `e2e/` | 8 | 0,9% |

---

## Classificação

### ATIVO (produção Release 2.0) — **412 arquivos**

| Área | Arquivos | Notas |
|------|----------|-------|
| Entrypoint | `src/main.py`, `src/interfaces/http/app.py` | Porta **8040** oficial |
| Serviços F01 | 14 serviços financeiros + 8 operacionais | Ver ARCHITECTURE_BASELINE_2.1 |
| Rotas HTTP | `finance_center.py`, `cash_flow.py`, `financial_intelligence.py`, `analytics.py` | APIs oficiais |
| Frontend | `frontend/app.js`, `pages/financeCenter.js`, `cashFlow.js`, `services/api.js` | Dashboard oficial |
| DW DDL | 21 arquivos `dw/ddl/*.sql` | Prontos para A04 |
| Unit tests F01 | 8 suites (47 casos) | Gate QA |
| E2E Playwright | 7 specs + helpers | Gate UI |
| Config | `config/*.json`, `.env.example` | Sem segredos |
| Scripts validação F01 | `validate_f01_*.py`, `f01_*_validation_results.json` | Evidência sprint |

### DEPRECATED — **89 arquivos**

| Item | Motivo |
|------|--------|
| `API_PORT=8050` em `.env` legado | Entrypoint Adelaide 8050 — substituído por 8040 |
| `logos_expense_classifier.py` (V1) | Substituído por V2/V3 |
| `financial_health_score_service.py` (V1/V2) | Substituído por V3 |
| `financial_snapshot_service.py`, `financial_operational_snapshot_service.py` | Parcialmente absorvidos por snapshot unificado |
| Relatórios A03.6 / P0 / baseline 1.0 | Histórico; manter como arquivo morto documental |
| `pacote_integracao_gateway/`, `logos-webposto-gateway/` | Pacotes legados de integração |
| 7 testes unitários legados (`test_client`, `post_*`) | Erro de collection pytest |

### EXPERIMENTAL — **312 arquivos**

| Item | Motivo |
|------|--------|
| `scripts/audit_*.py` (A03, P0, supplier discovery) | Auditorias pontuais, não runtime |
| `scripts/webposto_network_probe.py`, `audit_p0_full.py` | Probes manuais |
| `snapshots/**/*.json` (28 arquivos) | Fixtures de desenvolvimento / cache local |
| `playwright-report/`, `test-results/` | Artefatos de execução (gitignored pós-checkpoint) |
| Relatórios F01.4* gerados (40+ MD) | Documentação de sprint, não código |
| `audit_*_results.json`, `*_audit.json` | Evidências de auditoria |

### REMOVER (candidatos) — **50 arquivos**

| Arquivo / padrão | Motivo | Prioridade |
|------------------|--------|------------|
| `WebPosto_API/.env` (do índice Git) | Credenciais expostas | **P0** |
| `RESULTADO_API.json` | URLs com CHAVE real | **P0** |
| `postman_webposto_network_collection.json` | Chave hardcoded | **P0** |
| `scripts/exemplo_alterar_produto.py` | API_KEY hardcoded | **P0** |
| `CONTINUACAO.md`, `EXEMPLO_ALTERAR_PRODUTO.md` | Bearer exposto | P1 |
| `TESTAR_WEBPOSTO*.ps1`, `LEIA-ME_DASHBOARD.txt` | Chaves em scripts legados | P1 |
| `fuel_network_audit.py`, `audit_token_scopes.py`, `audit_raw_fields.py` (raiz) | Duplicatas com fallback hardcoded | P1 |
| Snapshots datados em `snapshots/` | Reduzir repo; mover para S3/artefato CI | P2 |
| `node_modules/` se rastreado | Nunca versionar | P2 |

---

## Entrypoints validados

| Entry | Porta | Status |
|-------|-------|--------|
| `src/main.py` | 8040 | **OFICIAL** |
| Gateway legado | 8050 | DEPRECATED |
| Scripts `uvicorn` ad-hoc | variável | EXPERIMENTAL |

## Cliente WebPosto

| Cliente | Arquivo | Status |
|---------|---------|--------|
| Oficial | `src/gateway/webposto_client.py` | ATIVO |
| Config | `src/core/config.py` | ATIVO |
| Probes legados | `scripts/webposto_network_probe.py` | EXPERIMENTAL |

---

## Respostas obrigatórias

1. **Arquivos ativos:** **412**
2. **Deprecated:** **89**
3. **Experimentais:** **312**
4. **Candidatos à remoção:** **50**

**Recomendação:** executar limpeza P0 (segurança) antes do primeiro `git push logos`.
