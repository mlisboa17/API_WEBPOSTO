# IA-2 — Gateway Core

**Arquivo:** `gateway/webposto_client.py`

## Interface implementada

```python
class WebPostoClient:
    def __init__(self, api_key=None, base_url=None, *, allow_live=False, ...)

    async def request(endpoint, params, empresa_codigo, timeout_s) -> WebPostoResponse

    async def get_venda / get_venda_item / get_nfce / get_abastecimento
    async def get_lmc_rede / get_produto / get_produto_empresa
    async def get_conta / get_plano_conta_gerencial

    async def paginate(endpoint_key, ...) -> AsyncIterator[WebPostoResponse]
```

## Helpers exportados

- `build_params()` — injeta CHAVE + empresaCodigo + datas
- `token_fingerprint()` — sha256[:12]
- `extract_rows()` — normaliza payload WebPosto
- `ENDPOINTS` — mapa dos 9 endpoints padronizados

## Dependências

- `httpx` (já existente no projeto)
- Sem novas dependências
