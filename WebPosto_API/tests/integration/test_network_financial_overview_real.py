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
    base = date.today() - timedelta(days=5)
    return base.isoformat(), date.today().isoformat()


def _assert_success(response_json: dict) -> None:
    assert response_json["success"] is True
    assert response_json["error"] is None
    assert isinstance(response_json["data"], dict)
    assert response_json["data"]["synthetic"] is False


def test_network_financial_overview_single_company_real(client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = client.get(
        "/v1/network/financial-overview",
        params={
            "empresa": 11495,
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "tipoDespesa": "operacional",
            "valorMin": 0,
            "valorMax": 1000000,
        },
    )
    assert response.status_code == 200

    body = response.json()
    _assert_success(body)

    data = body["data"]
    assert isinstance(data["postos"], list)
    assert len(data["postos"]) >= 1

    posto = data["postos"][0]
    assert "empresaCodigo" in posto
    assert "nome" in posto
    assert "despesas" in posto
    assert "a_pagar" in posto
    assert "vendas_combustivel" in posto
    assert "vendas_produtos" in posto
    assert posto["synthetic"] is False

    detalhes = posto["despesas_detalhes"]
    assert isinstance(detalhes, list)
    for item in detalhes:
        assert item["synthetic"] is False
        valor = float(item["valor"])
        assert valor >= 0
        assert valor <= 1000000

    consolidado = data["consolidado"]
    assert "total_despesas" in consolidado
    assert "total_a_pagar" in consolidado
    assert "total_vendas_combustivel" in consolidado
    assert "total_vendas_produtos" in consolidado


def test_network_financial_overview_network_real(client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = client.get(
        "/v1/network/financial-overview",
        params={
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "origem": "financeiro",
            "status": "pendente",
        },
    )
    assert response.status_code == 200
    body = response.json()
    _assert_success(body)

    postos = body["data"]["postos"]
    assert isinstance(postos, list)

    consolidado = body["data"]["consolidado"]
    assert isinstance(consolidado, dict)

    for posto in postos:
        detalhes = posto.get("despesas_detalhes", [])
        for item in detalhes:
            status = str(item.get("status") or "").lower()
            origem = str(item.get("origem") or "").lower()
            assert "pend" in status or status == "aberto"
            assert "financeiro" in origem
