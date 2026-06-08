from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from unittest.mock import AsyncMock

from src.interfaces.http.routes.analytics import router
from src.models.response_model import WebPostoResponse

def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

@pytest.mark.anyio
async def test_network_coverage_endpoint(monkeypatch):
    mock_companies = [
        {
            "codWeb": 11495,
            "empresaCodigo": 11495,
            "nome": "POSTO VIP",
            "status": "CONFIRMADA",
            "statusOperacional": "ATIVA",
            "statusDetalhado": "Dados operacionais",
            "possuiDadosOperacionais": True,
        },
        {
            "codWeb": 5256,
            "empresaCodigo": 5256,
            "nome": "POSTO BR SHOPPING",
            "status": "CONFIRMADA",
            "statusOperacional": "ATIVA",
            "statusDetalhado": "Token insuficiente",
            "possuiDadosOperacionais": False,
        },
        {
            "codWeb": None,
            "empresaCodigo": None,
            "nome": "AUTO POSTO GLOBO",
            "status": "PENDENTE_IDENTIFICACAO",
            "statusOperacional": "PENDENTE_IDENTIFICACAO",
            "statusDetalhado": "Pendente identificacao",
            "possuiDadosOperacionais": False,
        },
        {
            "codWeb": 5558,
            "empresaCodigo": 5558,
            "nome": "POSTO REAL",
            "status": "INATIVA",
            "statusOperacional": "INATIVA",
            "statusDetalhado": "Inativa",
            "possuiDadosOperacionais": False,
        }
    ]
    mock_get_companies = AsyncMock(return_value=WebPostoResponse.ok({
        "data": mock_companies,
        "total": len(mock_companies),
        "synthetic": False
    }))
    
    from src.interfaces.http.routes import analytics
    monkeypatch.setattr(analytics._overview, "get_companies", mock_get_companies)

    client = _build_client()
    response = client.get("/api/v1/network/coverage")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["filiaisTotais"] == 4
    assert data["filiaisConfirmadas"] == 2
    assert data["filiaisPendentesIdentificacao"] == 1
    assert data["filiaisAtivas"] == 2
    assert data["filiaisInativas"] == 1
    assert data["filiaisComDados"] == 1
    assert data["filiaisSemDados"] == 1
    assert data["coverageConfirmedPercent"] == 50.0
    assert data["coverageOperationalPercent"] == 50.0
    assert data["coveragePercent"] == 50.0
    assert data["networkHealth"] == 50.0
