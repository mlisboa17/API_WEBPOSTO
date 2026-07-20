from src.core.config import CoreConfig
from src.gateway.webposto_client import WebPostoClient


def client() -> WebPostoClient:
    return WebPostoClient(CoreConfig(
        webposto_base_url="https://example.invalid",
        webposto_api_key="vip",
        webposto_api_keys=("vip", "casa", "doze"),
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
