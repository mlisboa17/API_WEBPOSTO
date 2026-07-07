"""Unit tests — DIR-01D ExecutiveReviewRequest."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.interfaces.http.app import create_app
from src.services.decision_evidence.models import DecisionEvidenceItem, DecisionEvidenceResponse
from src.services.executive_review.models import ReviewRequestStatus, ReviewRequestType
from src.services.executive_review.pending_evidence import item_needs_nominal_review, partition_evidence_items
from src.services.executive_review.service import ExecutiveReviewService, NoPendingEvidenceError
from src.services.executive_review.store import ExecutiveReviewStore

DECISION_ID = "175da101-6f68-42f4-9d2b-9b42e6cedea2"
TENANT = "74014"


def _item(
    item_id: str,
    amount: float,
    *,
    person_name: str | None = None,
    match_status: str = "NO_MATCH",
) -> DecisionEvidenceItem:
    return DecisionEvidenceItem(
        id=item_id,
        tenant_id=TENANT,
        empresa_codigo=TENANT,
        source="/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
        amount=amount,
        person_name=person_name,
        match_status=match_status,
    )


def _evidence_response(items: list[DecisionEvidenceItem]) -> DecisionEvidenceResponse:
    return DecisionEvidenceResponse(
        decision_id=DECISION_ID,
        decision_summary="Teste",
        evidence_items=items,
        evidence_items_count=len(items),
        evidence_items_total=round(sum(i.amount for i in items), 2),
        source_metadata={"tenant_id": TENANT, "tenant_name": "POSTO DOZE FILIAL II"},
    )


@pytest.fixture
def temp_store(tmp_path: Path) -> ExecutiveReviewStore:
    return ExecutiveReviewStore(store_path=tmp_path / "review_store.json")


@pytest.fixture
def review_service(temp_store: ExecutiveReviewStore) -> ExecutiveReviewService:
    mock_evidence = MagicMock()
    svc = ExecutiveReviewService(evidence_service=mock_evidence, store=temp_store)
    return svc


def test_pending_only_no_match_and_ambiguous():
    items = [
        _item("a", 150, person_name="DOUGLAS", match_status="PROBABLE"),
        _item("b", 1000, match_status="AMBIGUOUS"),
        _item("c", 40, match_status="NO_MATCH"),
        _item("d", 150, person_name="RYAN", match_status="EXACT"),
    ]
    identified, pending = partition_evidence_items(items)
    assert len(identified) == 2
    assert len(pending) == 2
    assert {p.id for p in pending} == {"b", "c"}


def test_identified_probable_with_name_excluded():
    item = _item("x", 150, person_name="DOUGLAS", match_status="PROBABLE")
    assert item_needs_nominal_review(item) is False


@pytest.mark.asyncio
async def test_create_review_request_counts(review_service: ExecutiveReviewService):
    items: list[DecisionEvidenceItem] = []
    for i in range(3):
        items.append(_item(f"id{i}", 150, person_name=f"Func {i}", match_status="PROBABLE"))
    for i in range(3):
        items.append(_item(f"amb{i}", 1000, match_status="AMBIGUOUS"))
    for amt, idx in [(1931, 0), (1150, 1), (1150, 2)]:
        items.append(_item(f"nm{idx}", amt, match_status="NO_MATCH"))
    for i in range(4):
        items.append(_item(f"nm150_{i}", 150, match_status="NO_MATCH"))
    for i in range(3):
        items.append(_item(f"nm40_{i}", 40, match_status="NO_MATCH"))

    review_service._evidence.get_evidence = AsyncMock(return_value=_evidence_response(items))

    request, created = await review_service.create_review_request(DECISION_ID)
    assert created is False
    assert request.status == ReviewRequestStatus.REQUESTED
    assert request.review_responsible is None
    assert request.evidence_count == 13
    assert request.evidence_total_amount == 7951.0
    assert request.identified_count == 3
    assert request.identified_amount == 450.0
    assert len(request.evidence_item_ids) == 13


@pytest.mark.asyncio
async def test_idempotent_double_post(review_service: ExecutiveReviewService):
    items = [_item("p1", 1000, match_status="AMBIGUOUS")]
    review_service._evidence.get_evidence = AsyncMock(return_value=_evidence_response(items))

    first, created1 = await review_service.create_review_request(DECISION_ID)
    second, created2 = await review_service.create_review_request(DECISION_ID)

    assert created1 is False
    assert created2 is True
    assert first.id == second.id
    assert review_service._store.list_by_decision(DECISION_ID).__len__() == 1


@pytest.mark.asyncio
async def test_no_pending_raises(review_service: ExecutiveReviewService):
    items = [_item("ok", 150, person_name="DOUGLAS", match_status="PROBABLE")]
    review_service._evidence.get_evidence = AsyncMock(return_value=_evidence_response(items))
    with pytest.raises(NoPendingEvidenceError):
        await review_service.create_review_request(DECISION_ID)


@pytest.mark.asyncio
async def test_list_and_get(review_service: ExecutiveReviewService):
    items = [_item("p1", 40, match_status="NO_MATCH")]
    review_service._evidence.get_evidence = AsyncMock(return_value=_evidence_response(items))
    created, _ = await review_service.create_review_request(DECISION_ID)
    listed = await review_service.list_for_decision(DECISION_ID)
    assert len(listed) == 1
    fetched = review_service.get_request(created.id)
    assert fetched is not None
    assert fetched.decision_id == DECISION_ID


def test_api_create_get_idempotent(tmp_path: Path):
    store_path = tmp_path / "api_store.json"
    store = ExecutiveReviewStore(store_path=store_path)

    from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService

    evidence_svc = DecisionEvidenceService()
    review_svc = ExecutiveReviewService(evidence_svc, store=store)

    app = create_app()
    app.dependency_overrides = {}
    client = TestClient(app)

    # Patch service on module
    import src.interfaces.http.routes.decisions as decisions_route

    decisions_route._review_service = review_svc
    decisions_route._evidence_service = evidence_svc

    items = [
        _item(f"n{i}", 40, match_status="NO_MATCH") for i in range(13)
    ] + [_item(f"id{i}", 150, person_name="X", match_status="PROBABLE") for i in range(3)]

    async def _get_evidence(decision_id: str):
        if decision_id == DECISION_ID:
            return _evidence_response(items)
        return None

    evidence_svc.get_evidence = AsyncMock(side_effect=_get_evidence)

    r1 = client.post(
        f"/api/v1/decisions/{DECISION_ID}/review-requests",
        json={"request_type": "NOMINAL_IDENTIFICATION_REVIEW"},
    )
    assert r1.status_code == 201
    body1 = r1.json()["data"]
    assert body1["status"] == "REQUESTED"
    assert body1["evidence_count"] == 13

    r2 = client.post(
        f"/api/v1/decisions/{DECISION_ID}/review-requests",
        json={"request_type": "NOMINAL_IDENTIFICATION_REVIEW"},
    )
    assert r2.status_code == 200
    body2 = r2.json()["data"]
    assert body2["already_exists"] is True
    assert body2["id"] == body1["id"]

    r404 = client.post("/api/v1/decisions/missing-id/review-requests", json={})
    assert r404.status_code == 404

    rget = client.get(f"/api/v1/decisions/{DECISION_ID}/review-requests")
    assert rget.status_code == 200
    assert len(rget.json()["data"]["requests"]) == 1

    rid = client.get(f"/api/v1/review-requests/{body1['id']}")
    assert rid.status_code == 200

    # persistência sobrevive reload store
    reloaded = ExecutiveReviewStore(store_path=store_path)
    assert reloaded.get(body1["id"]) is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_runtime_decision_review_request():
    """Integração real — decisão VALUE-03."""
    store = ExecutiveReviewStore()
    store.clear_all()
    from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService

    svc = ExecutiveReviewService(DecisionEvidenceService(), store=store)
    evidence = await svc._evidence.get_evidence(DECISION_ID)
    if not evidence:
        pytest.skip("snapshot owner_analysis DIR01 ausente")

    summary = svc.pending_summary(evidence.evidence_items)
    assert summary["total_count"] == 16
    assert summary["identified_count"] == 3
    assert summary["pending_count"] == 13
    assert summary["pending_amount"] == 7951.0

    req1, c1 = await svc.create_review_request(DECISION_ID)
    req2, c2 = await svc.create_review_request(DECISION_ID)
    assert c1 is False
    assert c2 is True
    assert req1.id == req2.id
    assert req1.review_responsible is None
