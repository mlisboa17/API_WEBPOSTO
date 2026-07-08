"""Unit tests — FIN-02 Financial Review Assignment."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.interfaces.http.app import create_app
from src.services.executive_review.assignment import (
    AssignReviewBody,
    ExecutiveReviewAssignmentService,
    ReviewAssignmentConflictError,
    ReviewAssignmentNotAllowedError,
    ReviewRequestNotFoundError,
)
from src.services.executive_review.follow_up import ExecutiveFollowUpService
from src.services.executive_review.financial_inbox import FinancialReviewInboxService
from src.services.executive_review.models import (
    ExecutiveReviewRequest,
    ReviewRequestStatus,
    ReviewRequestType,
)
from src.services.executive_review.store import ExecutiveReviewStore

DECISION_ID = "175da101-6f68-42f4-9d2b-9b42e6cedea2"
REQUEST_ID = "fin02-request-id"
TENANT = "74014"
EVIDENCE_IDS = [f"ev-{i}" for i in range(13)]


def _sample_request(
    *,
    status: ReviewRequestStatus = ReviewRequestStatus.REQUESTED,
    responsible: str | None = None,
) -> ExecutiveReviewRequest:
    return ExecutiveReviewRequest(
        id=REQUEST_ID,
        decision_id=DECISION_ID,
        tenant_id=TENANT,
        empresa_codigo=TENANT,
        tenant_name="POSTO DOZE FILIAL II",
        request_type=ReviewRequestType.NOMINAL_IDENTIFICATION_REVIEW,
        title="Conferência nominal — 13 lançamento(s)",
        description="13 lançamento(s) requerem validação.",
        status=status,
        evidence_item_ids=list(EVIDENCE_IDS),
        evidence_count=13,
        evidence_total_amount=7951.0,
        review_responsible=responsible,
        requested_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def temp_store(tmp_path: Path) -> ExecutiveReviewStore:
    store = ExecutiveReviewStore(store_path=tmp_path / "assign_store.json")
    store.save(_sample_request())
    store.save(
        _sample_request(
            status=ReviewRequestStatus.COMPLETED,
        ).model_copy(update={"id": "completed-req"})
    )
    store.save(
        _sample_request(
            status=ReviewRequestStatus.CANCELLED,
        ).model_copy(update={"id": "cancelled-req"})
    )
    return store


def test_requested_to_assigned(temp_store: ExecutiveReviewStore):
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    request, idempotent = svc.assign(REQUEST_ID, AssignReviewBody(responsible_name="Ana Silva"))
    assert idempotent is False
    assert request.status == ReviewRequestStatus.ASSIGNED
    assert request.review_responsible == "Ana Silva"
    assert request.assigned_at is not None


def test_responsible_name_persisted(temp_store: ExecutiveReviewStore):
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    svc.assign(REQUEST_ID, AssignReviewBody(responsible_name="Marcio de Lima"))
    reloaded = temp_store.get(REQUEST_ID)
    assert reloaded is not None
    assert reloaded.review_responsible == "Marcio de Lima"


def test_assigned_at_persisted(temp_store: ExecutiveReviewStore):
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    request, _ = svc.assign(REQUEST_ID, AssignReviewBody(responsible_name="Ana"))
    reloaded = temp_store.get(REQUEST_ID)
    assert reloaded is not None
    assert reloaded.assigned_at == request.assigned_at


def test_decision_id_preserved(temp_store: ExecutiveReviewStore):
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    request, _ = svc.assign(REQUEST_ID, AssignReviewBody(responsible_name="Ana"))
    assert request.decision_id == DECISION_ID


def test_tenant_preserved(temp_store: ExecutiveReviewStore):
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    request, _ = svc.assign(REQUEST_ID, AssignReviewBody(responsible_name="Ana"))
    assert request.tenant_id == TENANT


def test_amount_preserved(temp_store: ExecutiveReviewStore):
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    request, _ = svc.assign(REQUEST_ID, AssignReviewBody(responsible_name="Ana"))
    assert request.evidence_total_amount == 7951.0


def test_pending_evidence_preserved(temp_store: ExecutiveReviewStore):
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    request, _ = svc.assign(REQUEST_ID, AssignReviewBody(responsible_name="Ana"))
    assert request.evidence_count == 13
    assert len(request.evidence_item_ids) == 13


def test_idempotent_same_responsible(temp_store: ExecutiveReviewStore):
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    svc.assign(REQUEST_ID, AssignReviewBody(responsible_name="Ana Silva"))
    request, idempotent = svc.assign(REQUEST_ID, AssignReviewBody(responsible_name="Ana Silva"))
    assert idempotent is True
    assert request.review_responsible == "Ana Silva"


def test_conflict_different_responsible(temp_store: ExecutiveReviewStore):
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    svc.assign(REQUEST_ID, AssignReviewBody(responsible_name="Ana Silva"))
    with pytest.raises(ReviewAssignmentConflictError):
        svc.assign(REQUEST_ID, AssignReviewBody(responsible_name="Carlos Souza"))


def test_completed_not_assignable(temp_store: ExecutiveReviewStore):
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    with pytest.raises(ReviewAssignmentNotAllowedError):
        svc.assign("completed-req", AssignReviewBody(responsible_name="Ana"))


def test_cancelled_not_assignable(temp_store: ExecutiveReviewStore):
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    with pytest.raises(ReviewAssignmentNotAllowedError):
        svc.assign("cancelled-req", AssignReviewBody(responsible_name="Ana"))


def test_not_found(temp_store: ExecutiveReviewStore):
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    with pytest.raises(ReviewRequestNotFoundError):
        svc.assign("missing-id", AssignReviewBody(responsible_name="Ana"))


def test_legacy_snapshot_without_assigned_at(tmp_path: Path):
    store = ExecutiveReviewStore(store_path=tmp_path / "legacy.json")
    raw = _sample_request().model_dump(mode="json")
    if "assigned_at" in raw:
        del raw["assigned_at"]
    store._write({"requests": {REQUEST_ID: raw}, "by_decision": {DECISION_ID: [REQUEST_ID]}})
    loaded = store.get(REQUEST_ID)
    assert loaded is not None
    assert loaded.assigned_at is None


def test_financeiro_reflects_assignment(temp_store: ExecutiveReviewStore):
    mock_evidence = MagicMock()
    mock_evidence._find_candidate.return_value = {"title": "Decisão", "evidence": {}}
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    svc.assign(REQUEST_ID, AssignReviewBody(responsible_name="Marcio de Lima"))
    inbox = FinancialReviewInboxService(store=temp_store, evidence_service=mock_evidence)
    item = inbox.get_inbox_item(REQUEST_ID)
    assert item is not None
    assert item.technical_status == ReviewRequestStatus.ASSIGNED.value
    assert item.financial_status_label == "Atribuído"
    assert item.review_responsible == "Marcio de Lima"


def test_diretoria_reflects_assignment(temp_store: ExecutiveReviewStore):
    mock_evidence = MagicMock()
    mock_evidence._find_candidate.return_value = {"title": "Decisão", "evidence": {}}
    svc = ExecutiveReviewAssignmentService(store=temp_store)
    svc.assign(REQUEST_ID, AssignReviewBody(responsible_name="Marcio de Lima"))
    follow = ExecutiveFollowUpService(store=temp_store, evidence_service=mock_evidence)
    item = follow.get_follow_up(REQUEST_ID)
    assert item is not None
    assert item.status == ReviewRequestStatus.ASSIGNED.value
    assert item.status_label == "Responsável definido"
    assert item.review_responsible == "Marcio de Lima"


def test_assign_api_endpoint(temp_store: ExecutiveReviewStore):
    import src.interfaces.http.routes.financial_review_inbox as route

    route._assignment = ExecutiveReviewAssignmentService(store=temp_store)
    route._service = FinancialReviewInboxService(
        store=temp_store,
        evidence_service=MagicMock(_find_candidate=lambda _d: {}),
    )
    client = TestClient(create_app())

    resp = client.post(
        f"/api/v1/financial/review-inbox/{REQUEST_ID}/assign",
        json={"responsible_name": "Marcio de Lima"},
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["status"] == "ASSIGNED"
    assert body["review_responsible"] == "Marcio de Lima"

    conflict = client.post(
        f"/api/v1/financial/review-inbox/{REQUEST_ID}/assign",
        json={"responsible_name": "Carlos Souza"},
    )
    assert conflict.status_code == 409

    idempotent = client.post(
        f"/api/v1/financial/review-inbox/{REQUEST_ID}/assign",
        json={"responsible_name": "Marcio de Lima"},
    )
    assert idempotent.status_code == 200
    assert idempotent.json()["data"]["idempotent"] is True
