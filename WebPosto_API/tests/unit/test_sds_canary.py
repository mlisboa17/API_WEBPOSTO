from src.core.config import CoreConfig
from src.gateway.webposto_client import WebPostoClient
from src.jobs.sds_canary import CANARY_DIA, validate_pair
from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse
from src.services.abastecimento_service import AbastecimentoService
from src.services.webposto.schemas import WEBPOSTO_WRITES


def _cfg() -> CoreConfig:
    return CoreConfig(
        webposto_base_url="https://example.invalid",
        webposto_api_key="vip",
        webposto_api_keys=("vip", "casa", "doze"),
        webposto_company_keys={11495: "vip", 5555: "casa", 74014: "doze"},
    )


def test_validate_pair_aceita_somente_pares_autorizaveis() -> None:
    assert validate_pair(11495, CANARY_DIA.isoformat()) is None
    assert validate_pair(74014, CANARY_DIA.isoformat()) is None
    assert validate_pair(5555, CANARY_DIA.isoformat()) is None
    assert validate_pair(6666, CANARY_DIA.isoformat()) is not None
    assert validate_pair(11495, "2026-08-14") is not None
    assert validate_pair(74014, "2026-08-12") is not None


def test_cli_bloqueia_unidade_e_data_invalidas() -> None:
    import pytest

    from src.jobs.sds_canary import main

    assert main(["--empresa", "6666", "--data", "2026-08-13"]) == 2
    assert main(["--empresa", "11495", "--data", "2026-08-14"]) == 2
    with pytest.raises(SystemExit):
        main(["--empresa", "11495,74014", "--data", "2026-08-13"])


def test_isolamento_11495_nao_carrega_outras_unidades() -> None:
    isolated = WebPostoClient.for_api_key("vip", _cfg())
    assert list(isolated.config.webposto_company_keys) == [11495]
    assert isolated._api_keys_for_params({"empresaCodigo": 11495}) == ("vip",)
    assert isolated._api_keys_for_params({"empresaCodigo": 5555}) == ()
    assert isolated._api_keys_for_params({"empresaCodigo": 74014}) == ()
    assert isolated._api_keys_for_params({"empresaCodigo": 6666}) == ()


def test_isolamento_74014_nao_carrega_outras_unidades() -> None:
    isolated = WebPostoClient.for_api_key("doze", _cfg())
    assert list(isolated.config.webposto_company_keys) == [74014]
    assert isolated._api_keys_for_params({"empresaCodigo": 74014}) == ("doze",)
    assert isolated._api_keys_for_params({"empresaCodigo": 5555}) == ()
    assert isolated._api_keys_for_params({"empresaCodigo": 11495}) == ()
    assert isolated._api_keys_for_params({"empresaCodigo": 6666}) == ()


def test_sem_fallback_para_chave_global() -> None:
    isolated = WebPostoClient.for_api_key("vip", _cfg())
    assert isolated._api_keys_for_params({"empresaCodigo": 999999}) == ()
    assert isolated.config.key_for_company(5555) is None


def test_writes_permanecem_desligados() -> None:
    assert WEBPOSTO_WRITES == 0


async def test_cursor_repetido_em_pagina_cheia_e_falha() -> None:
    class _Client:
        async def call_endpoint(self, endpoint_key, params=None):
            return WebPostoResponse.ok(
                {
                    "dados": [{"empresaCodigo": 5555, "codigo": 1, "quantidade": 1}] * 200,
                    "ultimoCodigo": 10,
                }
            )

    svc = AbastecimentoService(_Client())
    svc._client_for = lambda _empresa: _Client()
    resp = await svc.get_periodo("2026-08-14", "2026-08-14", empresa_codigo=5555)
    assert resp.success is False
    assert resp.error is not None
    assert resp.error.type == "PAGINATION_AMBIGUOUS"


async def test_pagina_posterior_falha_nao_devolve_parcial() -> None:
    class _Client:
        async def call_endpoint(self, endpoint_key, params=None):
            if not (params or {}).get("ultimoCodigo"):
                return WebPostoResponse.ok(
                    {
                        "dados": [{"empresaCodigo": 11495, "codigo": 1, "quantidade": 1}] * 200,
                        "ultimoCodigo": 99,
                    }
                )
            return WebPostoResponse.fail(
                WebPostoError(
                    endpoint="abastecimento",
                    status=500,
                    type="NETWORK_ERROR",
                    message="falha pagina 1",
                )
            )

    svc = AbastecimentoService(_Client())
    svc._client_for = lambda _empresa: _Client()
    resp = await svc.get_periodo("2026-08-13", "2026-08-13", empresa_codigo=11495)
    assert resp.success is False
    assert resp.data is None
