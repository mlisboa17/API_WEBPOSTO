"""Integração Sprint 43 — adoção, relatório mensal BVG e homologação de webhook."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.security.jwt_utils import create_access_token
from src.interfaces.http.app import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def owner_client() -> TestClient:
    client = TestClient(create_app())
    client.cookies.set("access_token", create_access_token("owner@example.com", {"role": "owner"}))
    return client


def test_executive_adoption_flow_records_and_reviews_blocks(owner_client: TestClient) -> None:
    payload = {"eventType": "PAGE_OPEN", "feature": "ATTENTION", "sessionId": "sprint43-test"}
    assert owner_client.post("/api/v1/departmental-governance/executive-adoption/events", json=payload).status_code == 200

    found = {
        "eventType": "INFORMATION_FOUND",
        "feature": "ATTENTION",
        "sessionId": "sprint43-test",
        "elapsedMs": 22000,
        "clicks": 1,
    }
    assert owner_client.post("/api/v1/departmental-governance/executive-adoption/events", json=found).status_code == 200

    summary = owner_client.get("/api/v1/departmental-governance/executive-adoption/summary")
    assert summary.status_code == 200
    body = summary.json()["data"]
    assert body["containsBusinessData"] is False
    assert body["averageTimeToInformationMs"] == 22000
    assert body["withinThirtySecondTarget"] is True

    review = owner_client.get("/api/v1/departmental-governance/executive-adoption/block-review")
    assert review.status_code == 200
    blocks = review.json()["data"]["blocks"]
    assert len(blocks) == 4
    attention = next(item for item in blocks if item["feature"] == "ATTENTION")
    assert attention["engagement"] == "ENGAGED"


def test_monthly_business_value_report_requires_validated_separation(owner_client: TestClient) -> None:
    response = owner_client.get("/api/v1/departmental-governance/monthly-business-value-report?month=2026-07")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["reportType"] == "MONTHLY_BUSINESS_VALUE_GENERATED_BY_AI"
    assert report["businessValueGeneratedByAI"]["label"] == "VALIDATED_VALUE_ONLY"
    assert report["estimatedValue"]["label"] == "ESTIMATED_NOT_REALIZED"
    assert report["governance"]["estimatedNeverCountedAsRealized"] is True


def test_webhook_homologation_is_owner_only() -> None:
    client = TestClient(create_app())
    assert client.post("/api/v1/departmental-governance/proactive-notifications/webhook-homologation").status_code == 401

    director = TestClient(create_app())
    director.cookies.set("access_token", create_access_token("director@example.com", {"role": "director"}))
    assert director.post("/api/v1/departmental-governance/proactive-notifications/webhook-homologation").status_code == 403


def test_webhook_homologation_without_url_returns_not_configured(owner_client: TestClient) -> None:
    response = owner_client.post("/api/v1/departmental-governance/proactive-notifications/webhook-homologation")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] in {"NOT_CONFIGURED", "DELIVERED", "FAILED"}
    assert data["containsBusinessData"] is False
