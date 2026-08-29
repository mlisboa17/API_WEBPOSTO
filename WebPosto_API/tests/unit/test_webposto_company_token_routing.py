from src.core.config import CoreConfig, OFFICIAL_COMPANY_CREDENTIAL_ALIASES
from src.gateway.webposto_client import WebPostoClient


def client() -> WebPostoClient:
    return WebPostoClient(CoreConfig(
        webposto_base_url="https://example.invalid",
        webposto_api_key="vip",
        webposto_api_keys=("vip", "casa", "doze"),
        webposto_company_keys={11495: "vip", 5555: "casa", 74014: "doze"},
    ))


def test_routes_74014_to_posto_doze_token_only() -> None:
    assert client()._api_keys_for_params({"empresaCodigo": 74014}) == ("doze",)


def test_routes_other_official_companies_to_their_own_tokens() -> None:
    gateway = client()
    assert gateway._api_keys_for_params({"empresaCodigo": 11495}) == ("vip",)
    assert gateway._api_keys_for_params({"empresaCodigo": "5555"}) == ("casa",)


def test_network_call_without_company_keeps_three_tokens() -> None:
    assert client()._api_keys_for_params({"dataInicial": "2026-07-01"}) == (
        "vip", "casa", "doze"
    )


def test_unknown_company_does_not_fall_back_to_generic_token() -> None:
    assert client().config.key_for_company(999999) is None
    assert client()._api_keys_for_params({"empresaCodigo": 999999}) == ()


def test_118508_requires_an_explicit_company_profile() -> None:
    assert client()._api_keys_for_params({"empresaCodigo": 118508}) == ()


def test_isolated_client_keeps_matching_company_key() -> None:
    isolated = WebPostoClient.for_api_key("casa", client().config)
    assert isolated._api_keys_for_params({"empresaCodigo": 5555}) == ("casa",)
    assert isolated._api_keys_for_params({"empresaCodigo": 11495}) == ()
    assert isolated._api_keys_for_params({"empresaCodigo": 74014}) == ()
    assert isolated._api_keys_for_params({"empresaCodigo": 6666}) == ()


def test_118508_does_not_accept_real_doze_aliases() -> None:
    assert OFFICIAL_COMPANY_CREDENTIAL_ALIASES[118508] == (
        "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY",
        "WEBPOSTO_API_GERAL_CONVENIENCIA_KEY",
    )
