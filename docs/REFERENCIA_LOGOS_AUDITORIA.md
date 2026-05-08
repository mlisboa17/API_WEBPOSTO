# Logos Auditoria — referência rápida

**Versão:** 1.1 · **Status:** alinhado ao código em `servicos_auditoria` + `webposto_client` (sem MOCK de negócio)

## Árvore principal

```
Api_WebPosto/
├── index.html                 # Dashboard (React via CDN)
├── docker-compose.yml
├── Dockerfile.webposto        # Imagem da API unificada (WebPosto_API + legacy)
├── Dockerfile                 # Só stack Logos auditoria (raiz)
├── config.py
├── webposto_client.py
├── models_auditoria.py
├── servicos_auditoria.py      # FastAPI exposta em modo “só raiz”
├── test_auditoria.py
├── .env                       # Criar a partir de .env.example (não versionar segredos)
├── WebPosto_API/              # App integrada (DDD)
│   └── src/ ...
└── docs/
    ├── README.md
    └── REFERENCIA_LOGOS_AUDITORIA.md
```

> Os arquivos `PLANO_INTEGRACAO.md`, `INTEGRACAO_COMPLETA.md`, `CHECKLIST_FINAL.md` permanecem na **raiz** do repo; use esta pasta `docs/` como índice.

## Endpoints — API raiz (`servicos_auditoria`)

`unidade_id` é **inteiro** (ex.: `1`, `2`, `3`).

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/auditoria/health` | Saúde do serviço Logos |
| GET | `/auditoria/despesas/{unidade_id}` | Lista despesas (`?data=YYYY-MM-DD` opcional). Vazio → `200` + `[]` |
| GET | `/auditoria/fechamentos/{unidade_id}` | Lista + resumo (`?data=` opcional). Vazio → `200` + listas vazias |
| GET | `/auditoria/resumo/{unidade_id}` | KPIs (`?data=` opcional) |
| GET | `/auditoria/despesas-por-categoria/{unidade_id}` | Agregado por categoria |
| POST | `/auditoria/registrar-despesa` | Envia ao WebPosto upstream |

Cliente HTTP usa paths **`/v1/...`** no WebPosto (sobrescreva com `WEBPOSTO_V1_*` no `.env` se necessário).

## `.env` (obrigatório para produção)

- `WEBPOSTO_BASE_URL`, `WEBPOSTO_BEARER_TOKEN`
- `WEBPOSTO_STRICT_STARTUP=true` (padrão): **não sobe** sem config válida + health do WebPosto. Dev local sem upstream: `false`.
- Mongo Logos: `LOGOS_SPACE_DB` (URI), não `LOGOS_SPACE_URL`.

## Testes

```bash
cd /path/to/Api_WebPosto
pytest test_auditoria.py -v
pytest test_auditoria.py::TestDespesaCaixa::test_despesa_valor_negativo -v
pytest test_auditoria.py --cov=. --cov-report=term-missing
```

> `AsyncMock` nos testes isola o cliente HTTP; **não** é dados fictícios na API.

## Padrões (Logos Mode)

- Validação: Pydantic + enums (`models_auditoria`).
- Async: `httpx` + FastAPI.
- Integração: log + exceção ou `HTTPException` mapeada (sem fallback MOCK).
- `unidade_id`: **`int`** em modelos e rotas.

Exemplo de assinatura correta:

```python
async def get_despesas(self, unidade_id: int, data_inicio: str | None) -> list[DespesaCaixa]:
    ...
```

## Stack Docker (6 serviços)

`api`, `mongo`, `redis`, `nginx`, `prometheus`, `grafana` — ver `docker-compose.yml`.

## Um fluxo que funciona (recomendado)

API **só Logos** (`servicos_auditoria`), sem Mongo/nginx:

```bash
cd /path/to/Api_WebPosto
# Windows PowerShell:
./run.ps1
# Linux/macOS:
chmod +x run.sh && ./run.sh
# Ou manual:
docker compose -f docker-compose.logos.yml up --build -d
curl -s http://localhost:8000/auditoria/health
```

Crie `.env` na raiz com `WEBPOSTO_BASE_URL` e `WEBPOSTO_BEARER_TOKEN` reais.  
O compose mínimo usa `WEBPOSTO_STRICT_STARTUP=false` por defeito para a imagem subir mesmo sem WebPosto; integrações reais falham até credenciais/DNS estarem certos.

**Stack completa** (6 serviços):

```bash
docker compose up -d --build
curl -s http://localhost:8000/auditoria/health
```

**Dashboard:** nginx na porta **80** quando usar o `docker-compose.yml` completo.

## Troubleshooting

| Sintoma | Ação |
|---------|------|
| Porta em uso | Altere portas no `docker-compose.yml` ou pare o processo. |
| Mongo recusado | `docker compose restart mongo` |
| WebPosto 401 | `WEBPOSTO_BEARER_TOKEN` / URL |
| API não sobe | `WEBPOSTO_STRICT_STARTUP=true` + health falhou → corrigir upstream ou `false` só em dev |
| Dashboard vazio | CORS / `window.LOGOS_API_BASE` / API no ar |
| Testes | `pytest test_auditoria.py -v` |

## Próximos passos sugeridos

1. `docker compose up -d` sem erros  
2. Seis containers `Up`  
3. `GET /auditoria/health`  
4. Dashboard no browser  
5. `pytest test_auditoria.py -v`  
