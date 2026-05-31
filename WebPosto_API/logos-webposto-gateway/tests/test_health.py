import os

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


API_PORT = int(os.getenv("API_PORT", "8050"))


@pytest.mark.asyncio
async def test_gateway_ready_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["port"] == API_PORT


@pytest.mark.asyncio
async def test_gateway_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"healthy", "degraded"}
    assert payload["port"] == API_PORT
