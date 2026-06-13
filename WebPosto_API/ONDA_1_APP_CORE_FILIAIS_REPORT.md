# Onda 1 — app_core Filiais Registry

Branch: `feature/app-core-filiais-registry`

## Respostas executivas 1–20

1. **Filiais oficiais:** 12
2. **Filiais ativas (registry):** 10
3. **Filiais em snapshot:** 10
4. **Com CNPJ:** 12
5. **Com Nome Fantasia:** 12
6. **Código duplicado:** Não
7. **Filial sem evidência:** AUTO POSTO GLOBO
8. **Divergência frontend/backend:** Resolvida via manifest único
9. **Manifest gerado:** Sim (`frontend/data/filiais.json`)
10. **Paridade JS ↔ Python:** Aprovada (6/6)
11. **Fallback frontend:** Sim (`FALLBACK_FILIAIS` em `frontend/filiais.js`)
12. **Motores F03–F07 alterados:** Não
13. **WebPosto live consultado:** Não
14. **Registry pronto para N filiais:** Sim
15. **empresaCodigo preservado:** Sim
16. **codWeb preservado:** Sim
17. **Documentação criada:** Sim
18. **QA aprovado:** Sim
19. **Onda 1 aprovada:** Sim
20. **Próxima onda:** Onda 2 — unificação do cliente WebPosto (facade sobre `gateway/webposto_client.py`)

## Entregáveis

- `app_core/filial_registry.py`
- `scripts/sync_filiais_manifest.py`
- `scripts/audit_app_core_filiais.py`
- `frontend/data/filiais.json`
- `frontend/filiais.js`
- `frontend/components/filiais.js` (adapter)
- `tests/unit/test_filial_registry_parity.py`
- Relatórios IA-1 a IA-7 + `APP_CORE_FILIAIS.md`

[PARECER FINAL: ONDA 1 APP_CORE FILIAIS APROVADA]
