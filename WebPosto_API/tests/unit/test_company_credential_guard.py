"""Testes do guard de empresa para escrita no WebPosto (sem rede, sem escrita)."""

import pytest

from src.core.config import OFFICIAL_COMPANY_CREDENTIAL_ALIASES
from src.operational.product_registration.company_credentials import (
    COMPANY_SENTINELS,
    CompanyCredentialError,
    HttpProductReader,
    company_guard,
    fingerprint,
    require_company_guard,
    resolve_credential,
)

KEY_118508 = "key-conveniencia-118508"
KEY_11495 = "key-vip-11495"

ENV_118508 = {"WEBPOSTO_CONVENIENCIA_24_HORAS_KEY": KEY_118508}

SENTINEL_118508 = COMPANY_SENTINELS[118508]


def _catalog_item(produto_codigo: int, referencia: str, ean: str) -> dict:
    return {
        "produtoCodigo": produto_codigo,
        "nome": "BISCOITO BONO RECHEIO DOCE DE LEITE 90G",
        "referenciaCodigo": referencia,
        "grupoCodigo": 55446,
        "produtoCodigoBarra": [{"codigoBarra": ean}],
    }


class FakeReader:
    """Leitor injetavel: devolve catalogo e vinculos fixos."""

    def __init__(self, catalog: list[dict], links: list[dict]) -> None:
        self._catalog = catalog
        self._links = links
        self.calls: list[tuple[str, int, int]] = []

    def get_catalog(self, key, cursor, page_size):
        self.calls.append(("catalog", cursor, page_size))
        return self._catalog

    def get_company_links(self, key, cursor, page_size):
        self.calls.append(("links", cursor, page_size))
        return self._links


def _reader_linking_to(empresa_codigo: int) -> FakeReader:
    return FakeReader(
        catalog=[
            _catalog_item(
                SENTINEL_118508.produto_codigo,
                SENTINEL_118508.referencia,
                SENTINEL_118508.ean,
            )
        ],
        links=[
            {
                "produtoCodigo": SENTINEL_118508.produto_codigo,
                "empresaCodigo": empresa_codigo,
                "precoVenda": 5.0,
            }
        ],
    )


def test_aliases_of_118508_come_from_core_config():
    """O mapeamento empresa -> variavel nao deve ser duplicado neste modulo."""
    aliases = OFFICIAL_COMPANY_CREDENTIAL_ALIASES[118508]

    assert aliases[0] == "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY"
    assert "WEBPOSTO_API_KEY" not in aliases
    assert "WEBPOSTO_TOKEN" not in aliases


def test_resolve_credential_uses_declared_variable_for_118508():
    credential = resolve_credential(118508, env=ENV_118508)

    assert credential.empresa_codigo == 118508
    assert credential.variable_name == "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY"
    assert credential.key == KEY_118508


def test_resolve_credential_refuses_generic_fallback():
    """O incidente 2481344 nasceu de cair em WEBPOSTO_API_KEY."""
    env = {"WEBPOSTO_API_KEY": KEY_11495, "WEBPOSTO_TOKEN": KEY_11495}

    with pytest.raises(CompanyCredentialError, match="Nenhuma credencial declarada"):
        resolve_credential(118508, env=env)


def test_resolve_credential_refuses_company_without_aliases():
    with pytest.raises(CompanyCredentialError, match="nao possui aliases declarados"):
        resolve_credential(999999, env=ENV_118508)


def test_credential_repr_does_not_expose_key():
    credential = resolve_credential(118508, env=ENV_118508)

    assert KEY_118508 not in repr(credential)
    assert credential.fingerprint in repr(credential)
    assert credential.fingerprint == fingerprint(KEY_118508)


def test_guard_passes_when_sentinel_and_company_link_match():
    credential = resolve_credential(118508, env=ENV_118508)

    result = company_guard(credential, _reader_linking_to(118508))

    assert result.sentinel_found
    assert result.company_link_confirmed
    assert result.passed


def test_guard_fails_when_link_points_to_other_company():
    """Reproduz o incidente: a credencial responde pela filial 11495."""
    credential = resolve_credential(118508, env=ENV_118508)

    result = company_guard(credential, _reader_linking_to(11495))

    assert result.sentinel_found
    assert not result.company_link_confirmed
    assert not result.passed


def test_guard_fails_when_sentinel_reference_diverges():
    credential = resolve_credential(118508, env=ENV_118508)
    reader = FakeReader(
        catalog=[_catalog_item(SENTINEL_118508.produto_codigo, "999999", SENTINEL_118508.ean)],
        links=[{"produtoCodigo": SENTINEL_118508.produto_codigo, "empresaCodigo": 118508}],
    )

    result = company_guard(credential, reader)

    assert not result.sentinel_found
    assert not result.passed


def test_guard_fails_when_sentinel_absent_from_catalog():
    credential = resolve_credential(118508, env=ENV_118508)
    reader = FakeReader(catalog=[], links=[])

    result = company_guard(credential, reader)

    assert not result.sentinel_found
    assert not result.company_link_confirmed


def test_guard_queries_cursor_just_below_sentinel():
    credential = resolve_credential(118508, env=ENV_118508)
    reader = _reader_linking_to(118508)

    company_guard(credential, reader, page_size=25)

    assert reader.calls == [
        ("catalog", SENTINEL_118508.produto_codigo - 1, 25),
        ("links", SENTINEL_118508.produto_codigo - 1, 25),
    ]


def test_require_company_guard_blocks_write_on_mismatch():
    with pytest.raises(CompanyCredentialError, match="COMPANY_CREDENTIAL_MISMATCH"):
        require_company_guard(118508, _reader_linking_to(11495), env=ENV_118508)


def test_require_company_guard_returns_credential_when_confirmed():
    credential = require_company_guard(118508, _reader_linking_to(118508), env=ENV_118508)

    assert credential.empresa_codigo == 118508


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class RecordingClient:
    def __init__(self, payload):
        self._payload = payload
        self.last_params: dict | None = None
        self.last_url: str | None = None

    def get(self, url, params=None):
        self.last_url = url
        self.last_params = params
        return FakeResponse(self._payload)


def test_http_reader_reads_resultados_not_data_items():
    """A leitura por data.items devolvia vazio e mascarou o incidente."""
    payload = {"ultimoCodigo": 2481344, "resultados": [{"produtoCodigo": 2481160}]}
    client = RecordingClient(payload)
    reader = HttpProductReader(client)

    items = reader.get_catalog("chave", cursor=2481159, page_size=50)

    assert items == [{"produtoCodigo": 2481160}]
    assert client.last_params["ultimoCodigo"] == 2481159
    assert client.last_params["tamanhoPagina"] == 50
    assert client.last_url.endswith("/INTEGRACAO/PRODUTO")


def test_http_reader_returns_empty_for_payload_without_resultados():
    reader = HttpProductReader(RecordingClient({"data": {"items": [{"produtoCodigo": 1}]}}))

    assert reader.get_company_links("chave", cursor=1, page_size=10) == []


def test_http_reader_raises_on_non_200():
    class FailingClient:
        def get(self, url, params=None):
            return FakeResponse(None, status_code=401)

    reader = HttpProductReader(FailingClient())

    with pytest.raises(CompanyCredentialError, match="HTTP 401"):
        reader.get_catalog("chave", cursor=1, page_size=10)
