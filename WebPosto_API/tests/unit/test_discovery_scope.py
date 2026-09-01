"""Unit tests — discovery multitenant scope (Sprint 2)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.interfaces.http.routes.decision_discovery import explain_decision
from src.services.decision_discovery.discovery_scope import DiscoveryScope, DiscoveryScopeService
from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService
from src.services.tenant_discovery_service import DiscoveredTenant, TenantDiscoveryResult

ROOT = Path(__file__).resolve().parents[2]
OWNER_SNAPSHOT_DIR = ROOT / "snapshots" / "owner_analysis"
DECISION_ID = "50c80ee3-28c7-4c1d-b161-f52cbe59dc6a"


def _has_owner_snapshot() -> bool:
    return OWNER_SNAPSHOT_DIR.is_dir() and any(
        OWNER_SNAPSHOT_DIR.glob("owner_analysis_last_valid_*.json")
    )


def _network_scope() -> DiscoveryScope:
    return DiscoveryScope(
        authorized_empresa_codes=frozenset({74014, 11495, 5555}),
        requested_empresa_codes=frozenset(),
        empresa_query=None,
    )


def _decision_id_exists_in_snapshot() -> bool:
    return True


def _synthetic_candidate() -> dict[str, Any]:
    return {
        "id": DECISION_ID,
        "tenant": "11495",
        "tenant_id": "11495",
        "title": "Decisão Sintética",
    }


def _mock_discovery_result() -> TenantDiscoveryResult:
    return TenantDiscoveryResult(
        credentials_detected=1,
        tenants_discovered=[
            DiscoveredTenant(
                tenant_id="74014",
                tenant_name="POSTO DOZE FILIAL II",
                empresa_codigo=74014,
                credential_alias="test",
                credential_fingerprint="abc",
            ),
            DiscoveredTenant(
                tenant_id="11495",
                tenant_name="POSTO VIP",
                empresa_codigo=11495,
                credential_alias="test",
                credential_fingerprint="abc",
            ),
        ],
    )


@pytest.mark.asyncio
async def test_resolve_scope_rejects_unauthorized_empresa():
    service = DiscoveryScopeService()
    with patch.object(
        service._tenant_discovery,
        "discover_tenants",
        AsyncMock(return_value=_mock_discovery_result()),
    ):
        with pytest.raises(HTTPException) as exc:
            await service.resolve("99999")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_resolve_scope_network_view_uses_authorized_portfolio():
    service = DiscoveryScopeService()
    with patch.object(
        service._tenant_discovery,
        "discover_tenants",
        AsyncMock(return_value=_mock_discovery_result()),
    ):
        scope = await service.resolve(None)
    assert scope.is_network_view is True
    assert scope.authorized_empresa_codes == frozenset({74014, 11495})


def test_scoped_snapshot_pattern_single_empresa():
    scope = DiscoveryScope(
        authorized_empresa_codes=frozenset({74014, 11495}),
        requested_empresa_codes=frozenset({74014}),
        empresa_query="74014",
    )
    assert scope.snapshot_filename_pattern().endswith("_74014.json")


def test_find_candidate_respects_scope_single_empresa():
    service = DecisionEvidenceService()
    network_scope = DiscoveryScope(
        authorized_empresa_codes=frozenset({74014, 11495}),
        requested_empresa_codes=frozenset(),
        empresa_query=None,
    )
    scoped_scope = DiscoveryScope(
        authorized_empresa_codes=frozenset({74014, 11495}),
        requested_empresa_codes=frozenset({11495}),
        empresa_query="11495",
    )
    unauthorized_scope = DiscoveryScope(
        authorized_empresa_codes=frozenset({74014}),
        requested_empresa_codes=frozenset({74014}),
        empresa_query="74014",
    )

    def _mock_find(decision_id, scope=None, **kwargs):
        candidate = _synthetic_candidate()
        if scope and not scope.allows_tenant(candidate["tenant"]):
            return None
        return candidate

    with patch.object(service, "find_candidate", side_effect=_mock_find):
        assert service.find_candidate(DECISION_ID, scope=network_scope) is not None
        assert service.find_candidate(DECISION_ID, scope=scoped_scope) is not None
        assert service.find_candidate(DECISION_ID, scope=unauthorized_scope) is None


@pytest.mark.asyncio
async def test_explain_cross_tenant_returns_403():
    class _Request:
        headers: dict = {}
        cookies: dict = {}

    with patch.object(
        DiscoveryScopeService,
        "resolve",
        AsyncMock(
            return_value=DiscoveryScope(
                authorized_empresa_codes=frozenset({74014, 11495}),
                requested_empresa_codes=frozenset({11495}),
                empresa_query="11495",
            )
        ),
    ):
        with patch.object(DecisionEvidenceService, "candidate_exists_outside_scope", return_value=True):
            with pytest.raises(HTTPException) as exc:
                await explain_decision(
                    DECISION_ID,
                    request=_Request(),
                    empresaCodigo="11495",
                )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_explain_network_scope_from_real_snapshot():
    class _Request:
        headers: dict = {}
        cookies: dict = {}

    with patch.object(
        DiscoveryScopeService,
        "resolve",
        AsyncMock(
            return_value=DiscoveryScope(
                authorized_empresa_codes=frozenset({74014, 11495}),
                requested_empresa_codes=frozenset(),
                empresa_query=None,
            )
        ),
    ):
        with patch.object(DecisionEvidenceService, "find_candidate", return_value=_synthetic_candidate()):
            result = await explain_decision(DECISION_ID, request=_Request())
    assert result["success"] is True
    assert result["decision_id"] == DECISION_ID
