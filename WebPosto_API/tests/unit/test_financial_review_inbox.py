"""Unit tests — FIN-01 Financial Review Inbox."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.interfaces.http.app import create_app
from src.services.decision_evidence.models import DecisionEvidenceItem, DecisionEvidenceResponse
from src.services.executive_review.financial_inbox import FinancialReviewInboxService
from src.services.executive_review.models import (
    ExecutiveReviewRequest,
    ReviewRequestStatus,
    ReviewRequestType,
)
from src.services.executive_review.status_labels import financial_status_label
from src.services.executive_review.store import ExecutiveReviewStore

DECISION_ID = "175da101-6f68-42f4-9d2b-9b42e6cedea2"
REQUEST_ID = "276f5e58-c568-4a2b-99ef-d73d9fbaf7b7"
TENANT_74014 = "74014"
EVIDENCE_IDS = [f"ev-{i}" for i in range(13)]


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
        evidence_item_ids=list(EVIDENCE_IDS),
        evidence_count=13,
        evidence_total_amount=amount,
        requested_at=datetime.now(timezone.utc),
    )


def _mock_evidence_service() -> MagicMock:
    mock = MagicMock()
    mock._find_candidate.return_value = {
        "title": "R$ 7,501 acima do baseline",
        "evidence": {"category": "Vale de funcionário referente a consolidação de caixa"},
    }
    return mock


def _mock_evidence_items() -> list[DecisionEvidenceItem]:
    return [
        DecisionEvidenceItem(
            id=eid,
            tenant_id=TENANT_74014,
            empresa_codigo=TENANT_74014,
            source="/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
            amount=100.0 + i,
            description="Vale de funcionário",
            origin="financeiro",
            match_status="NO_MATCH",
        )
        for i, eid in enumerate(EVIDENCE_IDS)
    ]


@pytest.fixture
def temp_store(tmp_path: Path) -> ExecutiveReviewStore:
    store = ExecutiveReviewStore(store_path=tmp_path / "fin_inbox_store.json")
    store.save(_sample_request())
    store.save(
        _sample_request(
            request_id="completed-id",
            status=ReviewRequestStatus.COMPLETED,
            amount=100.0,
        )
    )
    return store


def test_financial_status_label_mapping():
    assert financial_status_label(ReviewRequestStatus.REQUESTED) == "Aguardando análise"


def test_projection_to_inbox_item(temp_store: ExecutiveReviewStore):
    mock_evidence = MagicMock()
    mock_evidence._find_candidate.return_value = {
        "title": "R$ 7,501 acima do baseline",
        "evidence": {"category": "Vale de funcionário referente a consolidação de caixa"},
    }
    svc = FinancialReviewInboxService(store=temp_store, evidence_service=mock_evidence)
    item = svc.to_inbox_item(temp_store.get(REQUEST_ID))
    assert item.request_id == REQUEST_ID
    assert item.decision_id == DECISION_ID
    assert item.amount_under_review == 7951.0
    assert item.evidence_items_count == 13
    assert item.financial_status_label == "Aguardando análise"
    assert item.review_responsible is None


def test_requested_appears_in_inbox(temp_store: ExecutiveReviewStore):
    svc = FinancialReviewInboxService(store=temp_store, evidence_service=_mock_evidence_service())
    items, summary = svc.list_inbox()
    assert summary.active_count == 1
    assert summary.total_amount_under_review == 7951.0
    assert summary.awaiting_analysis_count == 1
    assert items[0].request_id == REQUEST_ID


def test_completed_excluded_by_default(temp_store: ExecutiveReviewStore):
    svc = FinancialReviewInboxService(store=temp_store, evidence_service=_mock_evidence_service())
    items, _ = svc.list_inbox()
    assert "completed-id" not in {i.request_id for i in items}


def test_tenant_isolation(temp_store: ExecutiveReviewStore):
    temp_store.save(_sample_request(request_id="5555-req", tenant_id="5555", amount=200.0))
    svc = FinancialReviewInboxService(store=temp_store, evidence_service=_mock_evidence_service())
    items_5555, _ = svc.list_inbox(tenant_id="5555")
    assert len(items_5555) == 1
    assert items_5555[0].tenant_id == "5555"

    items_74014, _ = svc.list_inbox(tenant_id=TENANT_74014)
    assert all(i.tenant_id == TENANT_74014 for i in items_74014)
    assert "5555-req" not in {i.request_id for i in items_74014}


def test_empty_inbox_honest(tmp_path: Path):
    store = ExecutiveReviewStore(store_path=tmp_path / "empty.json")
    svc = FinancialReviewInboxService(store=store, evidence_service=_mock_evidence_service())
    items, summary = svc.list_inbox()
    assert items == []
    assert summary.active_count == 0


@pytest.mark.asyncio
async def test_detail_preserves_decision_and_pending_evidence(temp_store: ExecutiveReviewStore):
    mock_evidence = MagicMock()
    mock_evidence._find_candidate.return_value = {
        "title": "Decisão teste",
        "evidence": {"category": "Vale"},
    }
    mock_evidence.get_evidence = AsyncMock(
        return_value=DecisionEvidenceResponse(
            decision_id=DECISION_ID,
            decision_summary="Resumo",
            evidence_items=_mock_evidence_items(),
            evidence_items_count=13,
            evidence_items_total=7951.0,
        )
    )
    svc = FinancialReviewInboxService(store=temp_store, evidence_service=mock_evidence)
    detail = await svc.get_inbox_detail(REQUEST_ID)
    assert detail is not None
    assert detail.decision_id == DECISION_ID
    assert len(detail.pending_evidence_items) == 13
    assert detail.origin_label == "Decisão da Diretoria"


def test_no_duplicate_requests_in_inbox(temp_store: ExecutiveReviewStore):
    svc = FinancialReviewInboxService(store=temp_store, evidence_service=_mock_evidence_service())
    items, _ = svc.list_inbox()
    ids = [i.request_id for i in items]
    assert len(ids) == len(set(ids))


def test_financial_inbox_api_runtime_shape(temp_store: ExecutiveReviewStore):
    import src.interfaces.http.routes.financial_review_inbox as route

    route._service = FinancialReviewInboxService(store=temp_store, evidence_service=_mock_evidence_service())
    client = TestClient(create_app())
    resp = client.get("/api/v1/financial/review-inbox")
    assert resp.status_code == 200
    body = resp.json()
    summary = body["data"]["summary"]
    assert summary["active_count"] == 1
    assert summary["total_amount_under_review"] == 7951.0
    item = body["data"]["items"][0]
    assert item["decision_id"] == DECISION_ID
    assert item["amount_under_review"] == 7951.0
    assert item["financial_status_label"] == "Aguardando análise"

    filtered = client.get("/api/v1/financial/review-inbox", params={"tenant_id": "5555"})
    assert filtered.json()["data"]["items"] == []
