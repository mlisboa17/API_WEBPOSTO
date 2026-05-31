"""Tests para presentation layer (endpoints)"""
import os

import pytest
from fastapi.testclient import TestClient
from src.main import app


API_PORT = int(os.getenv("API_PORT", "8050"))


client = TestClient(app)


class TestReadyEndpoint:
    """Testes para endpoint /ready"""
    
    def test_ready_returns_200(self):
        """Endpoint /ready deve retornar HTTP 200 imediatamente"""
        response = client.get("/ready")
        assert response.status_code == 200
    
    def test_ready_response_structure(self):
        """Endpoint /ready deve retornar JSON com status"""
        response = client.get("/ready")
        assert "status" in response.json()
        assert response.json()["status"] == "ready"


class TestHealthEndpoint:
    """Testes para endpoint /health"""
    
    @pytest.mark.asyncio
    async def test_health_returns_200_when_db_up(self):
        """Endpoint /health deve retornar 200 quando DB está OK"""
        response = client.get("/health")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_health_response_structure(self):
        """Endpoint /health deve conter status da DB"""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert data["port"] == API_PORT


class TestRootEndpoint:
    """Testes para endpoint raiz"""
    
    def test_root_returns_200(self):
        """Endpoint / deve retornar HTTP 200"""
        response = client.get("/v1/")
        assert response.status_code == 200
    
    def test_root_response_contains_endpoints(self):
        """Endpoint / deve listar endpoints disponíveis"""
        response = client.get("/v1/")
        data = response.json()
        assert "endpoints" in data
        assert "/ready" in data["endpoints"]
