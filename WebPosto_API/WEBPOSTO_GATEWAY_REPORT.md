# Onda 2 — WebPosto Unified Gateway

Branch: `feature/webposto-unified-gateway`  
Base: `feature/app-core-filiais-registry`

## Entregáveis

```text
gateway/webposto_client.py
gateway/webposto_types.py
gateway/webposto_errors.py
gateway/__init__.py
scripts/audit_webposto_gateway.py
tests/unit/test_webposto_gateway.py
WEBPOSTO_INTEGRATION_INVENTORY_REPORT.md
WEBPOSTO_GATEWAY_CORE_REPORT.md
WEBPOSTO_AUTH_TOKEN_POLICY_REPORT.md
WEBPOSTO_ENDPOINT_WRAPPERS_REPORT.md
WEBPOSTO_PAGINATION_RETRY_REPORT.md
WEBPOSTO_OBSERVABILITY_REPORT.md
WEBPOSTO_SNAPSHOT_FIRST_GUARD_REPORT.md
WEBPOSTO_GATEWAY_TEST_REPORT.md
WEBPOSTO_GATEWAY_QA_REPORT.md
```

## Respostas executivas 1–20

1. **Integrações WebPosto existentes:** 6 clientes + dezenas de scripts/services
2. **Wrappers duplicados:** 6 implementações paralelas
3. **Endpoints padronizados:** 9 (VENDA, VENDA_ITEM, NFCE, ABASTECIMENTO, LMC_REDE, PRODUTO, PRODUTO_EMPRESA, CONTA, PLANO_CONTA_GERENCIAL)
4. **Token centralizado:** Sim — `resolve_api_key()` + env keys
5. **Token completo em log:** Não
6. **empresaCodigo suportado:** Sim — injetado em todo request
7. **Gateway assume token=filial:** Não — documentado e implementado
8. **Retry:** Sim — backoff exponencial, max 3
9. **Timeout:** Sim — default 30s configurável
10. **Paginação preparada:** Sim — `paginate()` + `PaginationState`
11. **401 tratado:** Sim → `WebPostoAuthError`
12. **500 tratado:** Sim → `WebPostoServerError`
13. **Observabilidade padronizada:** Sim — JSON structured log
14. **Snapshot-first preservado:** Sim — `allow_live=False` default
15. **F03–F07 alterados:** Não
16. **Testes unitários:** 10/10 PASS
17. **Pronto para N filiais:** Sim — via `empresa_codigo` + Onda 1 registry
18. **Pronto para migração incremental:** Sim — facade paralela a `src/gateway/`
19. **QA aprovado:** Sim
20. **Próxima onda:** Onda 3 — migrar motores F07+ incrementalmente para `gateway.webposto_client`

## Validação

```bash
python -m pytest tests/unit/test_webposto_gateway.py -q --no-cov
python scripts/audit_webposto_gateway.py
```

```text
[PARECER FINAL: ONDA 2 WEBPOSTO GATEWAY APROVADA]
```
