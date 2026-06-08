from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from src.interfaces.http.app import create_app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (os.environ.get("WEBPOSTO_API_KEY") or os.environ.get("WEBPOSTO_CHAVE")),
        reason="WEBPOSTO_API_KEY ausente para testes reais",
    ),
]


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def periodo() -> tuple[str, str]:
    base = date.today() - timedelta(days=1)
    iso = base.isoformat()
    return iso, iso


def _extract_rows(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("resultados"), list):
            return payload["resultados"]
        if isinstance(payload.get("data"), list):
            return payload["data"]
        if isinstance(payload.get("items"), list):
            return payload["items"]
    return []


def _assert_success_payload(body: dict) -> None:
    assert isinstance(body, dict)
    assert "success" in body
    assert "data" in body
    assert "error" in body
    assert body["success"] is True
    assert body["error"] is None


def test_abastecimento_real(client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = client.get("/v1/abastecimento", params={"dataInicial": data_inicial, "dataFinal": data_final})
    assert response.status_code == 200
    body = response.json()
    _assert_success_payload(body)
    rows = _extract_rows(body["data"])
    assert isinstance(rows, list)


def test_caixa_real(client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = client.get("/v1/caixa", params={"dataInicial": data_inicial, "dataFinal": data_final})
    assert response.status_code == 200
    body = response.json()
    _assert_success_payload(body)
    rows = _extract_rows(body["data"])
    assert isinstance(rows, list)


def test_caixa_apresentado_real(client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = client.get("/v1/caixa-apresentado", params={"dataInicial": data_inicial, "dataFinal": data_final})
    assert response.status_code == 200
    body = response.json()
    _assert_success_payload(body)
    rows = _extract_rows(body["data"])
    assert isinstance(rows, list)


def test_titulo_pagar_real(client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = client.get("/v1/financeiro", params={"dataInicial": data_inicial, "dataFinal": data_final})
    assert response.status_code == 200
    body = response.json()
    _assert_success_payload(body)
    rows = _extract_rows(body["data"])
    assert isinstance(rows, list)


def test_analise_vendas_combustivel_real(client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = client.get("/v1/vendas-combustivel", params={"dataInicial": data_inicial, "dataFinal": data_final})
    assert response.status_code == 200
    body = response.json()
    _assert_success_payload(body)

    data = body["data"]
    assert isinstance(data, dict)
    assert "items" in data
    assert "count" in data
    assert "synthetic" in data
    assert data["synthetic"] is False

    items = data["items"]
    assert isinstance(items, list)
    assert data["count"] == len(items)

    for item in items:
        assert item["synthetic"] is False
        assert item.get("data")
        assert item.get("posto")
        assert item.get("produto")
        assert item.get("valor") is not None


def test_consistencia_operacao_inteligente(client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = client.get(
        "/v1/operacao-inteligente",
        params={"dataInicial": data_inicial, "dataFinal": data_final},
        headers={"X-Posto-ID": "POSTO_VIP"},
    )
    assert response.status_code == 200
    body = response.json()
    _assert_success_payload(body)

    data = body["data"]
    correlacao = data["correlacao"]

    abastecimento = data["operacao"]["abastecimento"]
    vendas = data["operacao"]["analise_vendas_combustivel"]
    caixa = data["financeiro"]["caixa"]
    caixa_apresentado = data["financeiro"]["caixa_apresentado"]
    titulo_pagar = data["financeiro"]["titulo_pagar"]

    assert correlacao["synthetic"] is False
    assert correlacao["abastecimento_count"] == len(abastecimento)
    assert correlacao["vendas_combustivel_count"] == len(vendas)
    assert correlacao["caixa_count"] == len(caixa)
    assert correlacao["caixa_apresentado_count"] == len(caixa_apresentado)
    assert correlacao["titulo_pagar_count"] == len(titulo_pagar)
