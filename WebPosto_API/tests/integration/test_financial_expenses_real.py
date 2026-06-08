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
    end = date.today()
    start = end - timedelta(days=5)
    return start.isoformat(), end.isoformat()


def test_financial_expenses_real_with_filters_and_pagination(client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo

    response = client.get(
        "/v1/financial/expenses",
        params={
            "empresaCodigo": 11495,
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "tipoDespesa": "operacional",
            "valorMin": 0,
            "valorMax": 1000000,
            "page": 1,
            "limit": 20,
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["error"] is None

    data = body["data"]
    assert data["page"] == 1
    assert data["limit"] == 20
    assert isinstance(data["total"], int)
    assert isinstance(data["data"], list)
    assert data["synthetic"] is False

    for row in data["data"]:
        assert row["empresaCodigo"] == 11495
        assert row["synthetic"] is False
        assert row["data"]
        assert row["valor"] is not None
        assert row["origem"] in ("caixa", "financeiro", "titulos_a_pagar")


def test_financial_expenses_consistency_with_network_overview(client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo

    expenses = client.get(
        "/v1/financial/expenses",
        params={
            "empresaCodigo": 11495,
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "page": 1,
            "limit": 200,
        },
    )
    overview = client.get(
        "/v1/network/financial-overview",
        params={
            "empresa": 11495,
            "dataInicial": data_inicial,
            "dataFinal": data_final,
        },
    )

    assert expenses.status_code == 200
    assert overview.status_code == 200

    exp_body = expenses.json()
    ov_body = overview.json()

    assert exp_body["success"] is True
    assert ov_body["success"] is True

    sum_expenses = sum(float(item["valor"]) for item in exp_body["data"]["data"])

    postos = ov_body["data"].get("postos", [])
    posto = next((p for p in postos if p.get("empresaCodigo") == 11495), None)
    assert posto is not None

    total_overview = float(posto["despesas"])

    assert sum_expenses <= total_overview
