"""Unit tests — Sprint 2 /discovery/explain com candidato real do snapshot."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from src.interfaces.http.routes.decision_discovery import explain_decision
from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService

ROOT = Path(__file__).resolve().parents[2]
OWNER_SNAPSHOT_DIR = ROOT / "snapshots" / "owner_analysis"
DECISION_ID = "175da101-6f68-42f4-9d2b-9b42e6cedea2"


def _has_owner_snapshot() -> bool:
    return OWNER_SNAPSHOT_DIR.is_dir() and any(
        OWNER_SNAPSHOT_DIR.glob("owner_analysis_last_valid_*.json")
    )


@pytest.mark.skipif(not _has_owner_snapshot(), reason="snapshot owner_analysis ausente")
@pytest.mark.asyncio
async def test_explain_decision_from_real_snapshot():
    result = await explain_decision(DECISION_ID)
    assert result["success"] is True
    assert result["source"] == "owner_analysis_snapshot"
    assert result["decision_id"] == DECISION_ID
    analysis = result["data"].get("analysis")
    assert analysis is not None
    assert analysis.get("most_probable_cause") or analysis.get("insufficient_data_message")


@pytest.mark.asyncio
async def test_explain_decision_not_found():
    with pytest.raises(HTTPException) as exc:
        await explain_decision("nonexistent-decision-id-00000000")
    assert exc.value.status_code == 404


def test_find_candidate_public_api():
    service = DecisionEvidenceService()
    if not _has_owner_snapshot():
        pytest.skip("snapshot owner_analysis ausente")
    candidate = service.find_candidate(DECISION_ID)
    assert candidate is not None
    assert str(candidate.get("id") or "") == DECISION_ID
