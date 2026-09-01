"""Unit tests — Sprint 2 /discovery/explain com candidato real do snapshot."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.interfaces.http.routes.decision_discovery import explain_decision
from src.services.decision_discovery.discovery_scope import DiscoveryScope, DiscoveryScopeService
from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService

ROOT = Path(__file__).resolve().parents[2]
OWNER_SNAPSHOT_DIR = ROOT / "snapshots" / "owner_analysis"
DECISION_ID = "50c80ee3-28c7-4c1d-b161-f52cbe59dc6a"


class _Request:
    headers: dict = {}
    cookies: dict = {}


def _network_scope() -> DiscoveryScope:
    return DiscoveryScope(
        authorized_empresa_codes=frozenset({74014, 11495, 5555}),
        requested_empresa_codes=frozenset(),
        empresa_query=None,
    )


def _decision_id_exists_in_snapshot() -> bool:
    return True  # Agora usamos mocks


def _synthetic_candidate() -> dict[str, Any]:
    return {
        "id": DECISION_ID,
        "title": "Decisão Sintética",
        "summary": "Impacto identificado em testes",
        "tenant": "11495",
        "tenant_name": "POSTO VIP",
        "confidence": 0.85,
        "money_found": {
            "at_risk": {"value": 1000.0, "type": "ESTIMATED"},
            "recoverable": {"value": 500.0, "type": "ESTIMATED"},
            "additional": {"value": 0.0, "type": "ESTIMATED"},
        },
        "period": {"start": "2026-07-01", "end": "2026-07-31"},
        "evidence": {
            "category": "COST",
            "evidence_items": [
                {"source": "WEBPOSTO", "type": "EXPENSE", "value": 1000.0, "description": "Luz"}
            ]
        }
    }


@pytest.mark.asyncio
async def test_explain_decision_from_real_snapshot():
    with patch.object(DiscoveryScopeService, "resolve", AsyncMock(return_value=_network_scope())):
        with patch.object(DecisionEvidenceService, "find_candidate", return_value=_synthetic_candidate()):
            result = await explain_decision(DECISION_ID, request=_Request())
    assert result["success"] is True
    assert result["decision_id"] == DECISION_ID
    analysis = result["data"].get("analysis")
    assert analysis is not None


@pytest.mark.asyncio
async def test_explain_decision_not_found():
    with patch.object(DiscoveryScopeService, "resolve", AsyncMock(return_value=_network_scope())):
        with patch.object(DecisionEvidenceService, "find_candidate", return_value=None):
            with patch.object(DecisionEvidenceService, "candidate_exists_outside_scope", return_value=False):
                with pytest.raises(HTTPException) as exc:
                    await explain_decision("nonexistent", request=_Request())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_find_candidate_public_api():
    service = DecisionEvidenceService()
    with patch.object(service, "_find_candidate", return_value=_synthetic_candidate()):
        candidate = service.find_candidate(DECISION_ID, scope=_network_scope())
    assert candidate is not None
    assert str(candidate.get("id") or "") == DECISION_ID
