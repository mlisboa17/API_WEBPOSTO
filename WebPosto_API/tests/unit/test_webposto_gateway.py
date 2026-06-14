"""Testes Onda 2 — gateway WebPosto unificado (sem WebPosto live)."""
from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from gateway.webposto_client import ENDPOINTS, WebPostoClient, build_params, token_fingerprint
from gateway.webposto_errors import (
    WebPostoAuthError,
    WebPostoServerError,
    WebPostoSnapshotGuardError,
)
from gateway.webposto_types import WebPostoResponse


@pytest.fixture
def api_key() -> str:
    return "4d6bbe21-92b2-4052-bcb5-a82c86858fd7"


@pytest.fixture
def client(api_key: str) -> WebPostoClient:
    return WebPostoClient(api_key=api_key, base_url="https://example.test", allow_live=True, max_retries=1)


def test_build_params_injects_empresa_codigo(api_key: str) -> None:
    params = build_params(
        api_key=api_key,
        empresa_codigo="11495",
        data_inicial="2026-06-01",
        data_final="2026-06-07",
        extra_params={"pagina": 0},
    )
    assert params["CHAVE"] == api_key
    assert params["empresaCodigo"] == "11495"
    assert params["dataInicial"] == "2026-06-01"
    assert params["pagina"] == 0


def test_token_fingerprint_is_short_hash(api_key: str) -> None:
    fp = token_fingerprint(api_key)
    assert len(fp) == 12
    assert api_key not in fp


def test_snapshot_guard_blocks_live_by_default(api_key: str) -> None:
    guarded = WebPostoClient(api_key=api_key, base_url="https://example.test", allow_live=False)
    with pytest.raises(WebPostoSnapshotGuardError):
        guarded._ensure_live_allowed("/INTEGRACAO/VENDA")


@pytest.mark.asyncio
async def test_snapshot_guard_blocks_request(api_key: str) -> None:
    guarded = WebPostoClient(api_key=api_key, base_url="https://example.test", allow_live=False)
    with pytest.raises(WebPostoSnapshotGuardError):
        await guarded.get_venda(empresa_codigo="11495", data_inicial="2026-06-01", data_final="2026-06-01")


@pytest.mark.asyncio
async def test_request_success_shape(client: WebPostoClient, api_key: str) -> None:
    payload = {"resultados": [{"vendaCodigo": 1}]}
    mock_response = httpx.Response(
        200,
        json=payload,
        request=httpx.Request("GET", f"{client.base_url}/INTEGRACAO/VENDA"),
    )

    with patch("gateway.webposto_client.httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.get = AsyncMock(return_value=mock_response)
        response = await client.get_venda(
            empresa_codigo="11495",
            data_inicial="2026-06-01",
            data_final="2026-06-01",
        )

    assert isinstance(response, WebPostoResponse)
    assert response.ok is True
    assert response.status == 200
    assert response.endpoint == ENDPOINTS["venda"]
    assert len(response.rows) == 1
    assert response.empresa_codigo == "11495"
    assert len(response.token_fingerprint) == 12
    assert api_key not in response.token_fingerprint


@pytest.mark.asyncio
async def test_request_raises_auth_error_on_401(client: WebPostoClient) -> None:
    mock_response = httpx.Response(
        401,
        text="Unauthorized",
        request=httpx.Request("GET", f"{client.base_url}/INTEGRACAO/PRODUTO"),
    )
    with patch("gateway.webposto_client.httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.get = AsyncMock(return_value=mock_response)
        with pytest.raises(WebPostoAuthError):
            await client.get_produto(empresa_codigo="5256")


@pytest.mark.asyncio
async def test_request_raises_server_error_on_500(client: WebPostoClient) -> None:
    mock_response = httpx.Response(
        500,
        text="fail",
        request=httpx.Request("GET", f"{client.base_url}/INTEGRACAO/NFCE"),
    )
    with patch("gateway.webposto_client.httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.get = AsyncMock(return_value=mock_response)
        with pytest.raises(WebPostoServerError):
            await client.get_nfce(empresa_codigo="5555")


@pytest.mark.asyncio
async def test_timeout_raises_server_error(client: WebPostoClient) -> None:
    fast = WebPostoClient(
        api_key=client.api_key,
        base_url=client.base_url,
        allow_live=True,
        max_retries=1,
        default_timeout_s=0.01,
    )
    with patch("gateway.webposto_client.httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.get = AsyncMock(side_effect=httpx.ReadTimeout("slow"))
        with pytest.raises(WebPostoServerError):
            await fast.get_conta(empresa_codigo="11495")


def test_logs_never_include_full_token(api_key: str, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="gateway.webposto_client")
    from gateway.webposto_types import WebPostoLogEvent

    client = WebPostoClient(api_key=api_key, base_url="https://example.test", allow_live=False)
    client._log_event(
        WebPostoLogEvent(
            endpoint="/INTEGRACAO/PRODUTO",
            status=200,
            latency_ms=10.5,
            has_data=True,
            empresa_codigo="11495",
            token_fingerprint=client.token_fingerprint,
        )
    )
    joined = " ".join(record.message for record in caplog.records)
    assert api_key not in joined
    assert client.token_fingerprint in joined


def test_wrappers_map_to_standard_endpoints(client: WebPostoClient) -> None:
    assert ENDPOINTS["venda_item"] == "/INTEGRACAO/VENDA_ITEM"
    assert ENDPOINTS["plano_conta_gerencial"] == "/INTEGRACAO/PLANO_CONTA_GERENCIAL"
    assert ENDPOINTS["lmc_rede"] == "/INTEGRACAO/CONSULTAR_LMC_REDE"
