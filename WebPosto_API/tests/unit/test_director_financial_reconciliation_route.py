from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.interfaces.http.routes import director_financial_reconciliation as route


class FakeSnapshot:
    async def get_or_collect(self, start, end, company):
        if company == 5333:
            raise ValueError("empresaCodigo fora das tres licencas autorizadas")
        return {
            "complete": False,
            "executiveSummary": [],
            "warnings": ["bloqueado"],
            "departmentalDre": [{"department": "combustiveis", "status": "BLOQUEADO"}],
            "publication": {"dreTotalsReleased": False},
            "coverage": [],
        }, False, True

    async def refresh(self, start, end, company):
        if company == 5333:
            raise ValueError("empresaCodigo fora das tres licencas autorizadas")
        return {"complete": True}


def test_route_exposes_auditable_payload(monkeypatch) -> None:
    monkeypatch.setattr(route, "_snapshot", FakeSnapshot())
    app = FastAPI()
    app.include_router(route.router)
    response = TestClient(app).get(
        "/api/v1/finance/director-reconciliation",
        params={"dataInicial": "2026-07-01", "dataFinal": "2026-07-01", "empresaCodigo": 11495},
    )
    assert response.status_code == 200
    assert response.json()["data"]["complete"] is False
    assert response.json()["snapshot"]["hit"] is True


def test_route_rejects_unlicensed_company(monkeypatch) -> None:
    monkeypatch.setattr(route, "_snapshot", FakeSnapshot())
    app = FastAPI()
    app.include_router(route.router)
    response = TestClient(app).get(
        "/api/v1/finance/director-reconciliation",
        params={"dataInicial": "2026-07-01", "dataFinal": "2026-07-01", "empresaCodigo": 5333},
    )
    assert response.status_code == 400


def test_refresh_route(monkeypatch) -> None:
    monkeypatch.setattr(route, "_snapshot", FakeSnapshot())
    app = FastAPI()
    app.include_router(route.router)
    response = TestClient(app).post(
        "/api/v1/finance/director-reconciliation/refresh",
        params={"dataInicial": "2026-07-01", "dataFinal": "2026-07-01", "empresaCodigo": 11495},
    )
    assert response.status_code == 200
    assert response.json()["data"]["complete"] is True


def test_departmental_dre_route_preserves_block_status(monkeypatch) -> None:
    monkeypatch.setattr(route, "_snapshot", FakeSnapshot())
    app = FastAPI()
    app.include_router(route.router)
    response = TestClient(app).get(
        "/api/v1/finance/director-reconciliation/dre",
        params={"dataInicial": "2026-07-01", "dataFinal": "2026-07-01", "empresaCodigo": 11495},
    )
    assert response.status_code == 200
    assert response.json()["data"]["lines"][0]["status"] == "BLOQUEADO"
    assert response.json()["data"]["publication"]["dreTotalsReleased"] is False
