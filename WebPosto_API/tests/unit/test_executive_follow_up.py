"""Unit tests — DIR-02 Executive Follow-Up."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.interfaces.http.app import create_app
from src.services.executive_review.follow_up import ExecutiveFollowUpService
from src.services.executive_review.models import (
    ExecutiveReviewRequest,
    ReviewRequestStatus,
    ReviewRequestType,
)
from src.services.executive_review.status_labels import status_label
from src.services.executive_review.store import ExecutiveReviewStore

DECISION_ID = "175da101-6f68-42f4-9d2b-9b42e6cedea2"
REQUEST_ID = "276f5e58-c568-4a2b-99ef-d73d9fbaf7b7"
TENANT_74014 = "74014"


def _sample_request(
    *,
    request_id: str = REQUEST_ID,
    tenant_id: str = TENANT_74014,
    status: ReviewRequestStatus = ReviewRequestStatus.REQUESTED,
    amount: float = 7951.0,
) -> ExecutiveReviewRequest:
    return ExecutiveReviewRequest(
        id=request_id,
        decision_id=DECISION_ID,
        tenant_id=tenant_id,
        empresa_codigo=tenant_id,
        tenant_name="POSTO DOZE FILIAL II",
        request_type=ReviewRequestType.NOMINAL_IDENTIFICATION_REVIEW,
        title="Conferência nominal — 13 lançamento(s)",
        description="13 lançamento(s) requerem validação.",
        status=status,
        evidence_count=13,
        evidence_total_amount=amount,
        requested_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def temp_store(tmp_path: Path) -> ExecutiveReviewStore:
    store = ExecutiveReviewStore(store_path=tmp_path / "follow_up_store.json")
    store.save(_sample_request())
    store.save(
        _sample_request(
            request_id="completed-id",
            status=ReviewRequestStatus.COMPLETED,
            amount=100.0,
        )
    )
    store.save(
        _sample_request(
            request_id="cancelled-id",
            status=ReviewRequestStatus.CANCELLED,
            amount=50.0,
        )
    )
    return store


def test_status_label_mapping():
    assert status_label(ReviewRequestStatus.REQUESTED) == "Aguardando atribuição"
    assert status_label(ReviewRequestStatus.IN_REVIEW) == "Em conferência"


def test_requested_appears_in_follow_up(temp_store: ExecutiveReviewStore):
    svc = ExecutiveFollowUpService(store=temp_store)
    items, summary = svc.list_follow_ups()
    assert summary.active_count == 1
    assert summary.total_amount_in_review == 7951.0
    assert summary.awaiting_assignment_count == 1
    assert summary.in_review_count == 0
    assert items[0].request_id == REQUEST_ID
    assert items[0].status_label == "Aguardando atribuição"


def test_completed_and_cancelled_excluded_by_default(temp_store: ExecutiveReviewStore):
    svc = ExecutiveFollowUpService(store=temp_store)
    items, _ = svc.list_follow_ups()
    ids = {i.request_id for i in items}
    assert "completed-id" not in ids
    assert "cancelled-id" not in ids


def test_tenant_filter_isolation(temp_store: ExecutiveReviewStore):
    temp_store.save(
        _sample_request(request_id="5555-req", tenant_id="5555", amount=200.0),
    )
    svc = ExecutiveFollowUpService(store=temp_store)
    items, _ = svc.list_follow_ups(tenant_id="5555")
    assert len(items) == 1
    assert items[0].tenant_id == "5555"

    items_74014, _ = svc.list_follow_ups(tenant_id=TENANT_74014)
    assert all(i.tenant_id == TENANT_74014 for i in items_74014)
    assert "5555-req" not in {i.request_id for i in items_74014}


def test_follow_up_api_runtime_shape(temp_store: ExecutiveReviewStore):
    temp_store.save(_sample_request(request_id="5555-req", tenant_id="5555", amount=200.0))
    import src.interfaces.http.routes.executive_follow_up as route

    route._service = ExecutiveFollowUpService(store=temp_store)
    client = TestClient(create_app())
    resp = client.get("/api/v1/executive/follow-ups")
    assert resp.status_code == 200
    body = resp.json()
    summary = body["data"]["summary"]
    assert summary["active_count"] == 2
    assert summary["total_amount_in_review"] == 8151.0
    item = body["data"]["items"][0]
    assert item["decision_id"] == DECISION_ID
    assert item["review_responsible"] is None

    filtered = client.get("/api/v1/executive/follow-ups", params={"tenant_id": "5555"})
    assert len(filtered.json()["data"]["items"]) == 1
    assert filtered.json()["data"]["items"][0]["tenant_id"] == "5555"


def test_empty_store_summary(tmp_path: Path):
    store = ExecutiveReviewStore(store_path=tmp_path / "empty.json")
    svc = ExecutiveFollowUpService(store=store)
    items, summary = svc.list_follow_ups()
    assert items == []
    assert summary.active_count == 0
