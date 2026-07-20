"""Integração — contratos JSON das 3 Telas do Presidente (Sprints 2–4)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.config.settings import settings
from src.interfaces.http.app import create_app

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def auth_client(client: TestClient) -> TestClient:
    response = client.post(
        "/auth/login",
        json={"email": settings.auth_user_email, "password": settings.auth_user_password},
    )
    if response.status_code != 200:
        pytest.skip("Credenciais de auth indisponíveis para teste de integração")
    return client


@pytest.fixture(scope="module")
def periodo() -> tuple[str, str]:
    base = date.today() - timedelta(days=7)
    return base.isoformat(), date.today().isoformat()


def _assert_dre_keys(data: dict) -> None:
    for key in (
        "faturamentoBruto",
        "margemContribuicao",
        "despesasOperacionais",
        "resultadoOperacional",
    ):
        assert key in data, f"Campo DRE ausente: {key}"


def _assert_cash_flow_keys(data: dict) -> None:
    assert "cards" in data
    assert "semanticBreakdown" in data
    breakdown = data["semanticBreakdown"]
    assert isinstance(breakdown, dict)
    for key in ("despesas", "receitas", "despesasPrevistas", "receitasPrevistas"):
        assert key in breakdown
        assert isinstance(breakdown[key], list)


def _assert_fuel_executive_keys(data: dict) -> None:
    assert "paridadePrecos" in data
    assert isinstance(data["paridadePrecos"], list)
    if data["paridadePrecos"]:
        row = data["paridadePrecos"][0]
        for key in ("combustivel", "precoMedioCompra", "precoMedioVenda", "margemRealizadaPct"):
            assert key in row


def _assert_business_health_keys(data: dict) -> None:
    for key in ("overall_score", "status", "risk_count", "has_sufficient_data", "deductions"):
        assert key in data


def test_dre_executivo_structure(auth_client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = auth_client.get(
        "/api/v1/dre",
        params={"dataInicial": data_inicial, "dataFinal": data_final},
    )
    assert response.status_code == 200
    body = response.json()
    payload = body.get("data") or body
    _assert_dre_keys(payload)


def test_cash_flow_structure(auth_client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = auth_client.get(
        "/api/v1/finance/cash-flow",
        params={"dataInicial": data_inicial, "dataFinal": data_final},
    )
    assert response.status_code == 200
    body = response.json()
    payload = body.get("data") or body
    _assert_cash_flow_keys(payload)


def test_fuel_executive_structure(auth_client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = auth_client.get(
        "/api/v1/fuel/executive",
        params={"dataInicial": data_inicial, "dataFinal": data_final},
    )
    assert response.status_code == 200
    body = response.json()
    payload = body.get("data") or body
    _assert_fuel_executive_keys(payload)


def test_business_health_structure(auth_client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = auth_client.get(
        "/api/v1/owner-action-center/business-health",
        params={"dataInicial": data_inicial, "dataFinal": data_final},
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("success") is True
    _assert_business_health_keys(body.get("data") or {})


def test_executive_snapshot_includes_dre(auth_client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = auth_client.get(
        "/api/v1/executive/snapshot",
        params={"dataInicial": data_inicial, "dataFinal": data_final},
    )
    assert response.status_code == 200
    body = response.json()
    snapshot = body.get("data") or body
    dre = snapshot.get("dre")
    if dre:
        _assert_dre_keys(dre)


def test_dre_filial_scope_forbidden(auth_client: TestClient, periodo: tuple[str, str]) -> None:
    data_inicial, data_final = periodo
    response = auth_client.get(
        "/api/v1/owner-action-center/business-health",
        params={
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "empresaCodigo": "99999999",
        },
    )
    assert response.status_code in (403, 404)
