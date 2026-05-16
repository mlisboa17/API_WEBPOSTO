# Retomada do projeto — WebPosto API

**Última atualização:** 16/05/2026  
**Branch:** `fix/pydantic-validators`

## Subir o ambiente

```bash
cd WebPosto_API
# .env já existe localmente (não versionado) — copie de env.example se precisar
python src/presentation/app.py
```

| URL | Uso |
|-----|-----|
| http://localhost:8000/ | Dashboard operacional (`dashboard_vendas.html`) |
| http://localhost:8000/dashboard | Cockpit Adelaide (`static/dashboard_logos.html`) |
| http://localhost:8000/health | Health + validação da chave (EMPRESAS) |

**`.env` local (não commitar):**
```env
WEBPOSTO_API_KEY=<WEBPOSTO_API_TOKEN>
WEBPOSTO_BASE_URL=https://web.qualityautomacao.com.br
API_PORT=8000
```

## O que foi feito nesta sessão

1. **Gateway unificado** — `src/presentation/app.py` (proxy, Adelaide, CORS, porta 8000).
2. **Painel executivo com galonagem** — `dashboard_vendas.html` busca `ABASTECIMENTO` no período e exibe KPI + tabela por combustível.
3. **Correções de chave** — placeholders `__from_env__` ignorados; health usa `EMPRESAS` (não `FILIAL`).
4. **Domínio Adelaide** — `src/domain/adelaide/`, `fetch_executive_kpis.py`.
5. **Tema/proxy frontend** — `theme/executive.js`.
6. **Script auditoria produtos** — `scripts/check_produto_crud.py`.

## Chave API — permissões conhecidas

| Recurso | Status |
|---------|--------|
| EMPRESAS, ABASTECIMENTO, VENDA, CAIXA, TITULO_* | OK (200) |
| GET PRODUTO (listar) | OK |
| POST PRODUTO (criar) | 404 — módulo não habilitado no contrato |
| PUT ALTERAR_PRODUTO | Escrita permitida (body completo obrigatório) |
| FILIAL | 401 — sem permissão (não usar no health) |
| LISTA_DE_ITENS, AJUSTE_ESTOQUE | 401/404 |

Reexecutar teste: `python scripts/check_produto_crud.py`

## Pendências para próxima sessão

- [ ] Pedir à Quality habilitar `POST /INTEGRACAO/PRODUTO` e `ajusteEstoqueProduto` se precisar CRUD completo.
- [ ] Alinhar `API_PORT` no `.env` (estava 5000; `env.example` usa 8000).
- [ ] Rota `metrics` — depende de `redis_adapter` (pode 500).
- [ ] Cache Valkey / hit ratio / testes 100% (plano multi-IA em `multi-ai-tasks/README.md`).
- [ ] Exemplo de `PUT /ALTERAR_PRODUTO/{id}` com payload completo a partir de um GET real.

## Arquivos principais

| Arquivo | Papel |
|---------|--------|
| `src/presentation/app.py` | Entrypoint FastAPI |
| `dashboard_vendas.html` | UI Lionda + painel executivo + galonagem |
| `theme/executive.js` | Proxy `/api/webposto/proxy` |
| `static/dashboard_logos.html` | Cockpit Adelaide |
| `env.example` | Variáveis de ambiente modelo |
| `scripts/check_produto_crud.py` | Teste permissões produto |

## Git

Alterações desta sessão commitadas na branch `fix/pydantic-validators`.  
**Não commitar:** `.env`, `.coverage`, `__pycache__/`.
