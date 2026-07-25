from fastapi.testclient import TestClient

from src.infrastructure.security.jwt_utils import create_access_token
from src.interfaces.http.app import create_app


def client_with_role(role: str | None = None) -> TestClient:
    client = TestClient(create_app())
    if role:
        client.cookies.set("access_token", create_access_token("reviewer@example.com", {"role": role}))
    return client


def test_mutating_routes_require_authentication():
    client = client_with_role()
    assert client.post("/api/v1/departmental-facts/materialize?empresaCodigo=11495&data=2026-07-23").status_code == 401
    assert client.post("/api/v1/departmental-kpis/goals", json={}).status_code == 401
    assert client.post("/api/v1/departmental-governance/alerts/evaluate?data=2026-07-23").status_code == 401
    assert client.put("/api/v1/departmental-governance/schedule", json={}).status_code == 401
    assert client.post("/api/v1/departmental-governance/schedule/run-due").status_code == 401
    assert client.post("/api/v1/auditorias-periodicas/executar-vencidos").status_code == 401
    assert client.get("/api/v1/departmental-governance/proactive-radar").status_code == 401
    assert client.get("/api/v1/departmental-governance/proactive-notifications").status_code == 401
    assert client.get("/api/v1/departmental-governance/proactive-agents").status_code == 401
    assert client.get("/api/v1/departmental-governance/proactive-value").status_code == 401
    assert client.get("/api/v1/departmental-governance/executive-adoption/summary").status_code == 401
    assert client.get("/api/v1/departmental-governance/executive-adoption/block-review").status_code == 401
    assert client.get("/api/v1/departmental-governance/monthly-business-value-report?month=2026-07").status_code == 401
    assert client.post("/api/v1/departmental-governance/proactive-notifications/webhook-homologation").status_code == 401
    assert client.post(
        "/api/v1/departmental-governance/executive-adoption/events",
        json={"eventType": "PAGE_OPEN", "feature": "ATTENTION", "sessionId": "test"},
    ).status_code == 401
    assert client.post(
        "/api/v1/departmental-governance/proactive-value/example/transition",
        json={"action": "ACCEPTED", "evidence": "aprovado"},
    ).status_code == 401


def test_viewer_cannot_mutate_governed_resources():
    client = client_with_role("viewer")
    response = client.post("/api/v1/auditorias-periodicas/executar-vencidos")
    assert response.status_code == 403


def test_director_cannot_validate_ai_value_without_independent_profile():
    client = client_with_role("director")
    response = client.post(
        "/api/v1/departmental-governance/proactive-value/example/transition",
        json={
            "action": "VALIDATED",
            "evidence": "resultado conferido",
            "costAvoidedBRL": 100,
        },
    )
    assert response.status_code == 403


def test_read_routes_remain_available_to_dashboard():
    client = client_with_role()
    assert client.get("/api/v1/auditorias-periodicas/ciclos").status_code == 200
    assert client.get("/api/v1/departmental-governance/health?data=2026-07-23").status_code == 200
    assert client.get("/api/v1/departmental-governance/schedule").status_code == 200
    assert client.get("/api/v1/departmental-governance/schedule/history").status_code == 200
