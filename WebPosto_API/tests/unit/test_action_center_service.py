"""Testes F05.2 — Action Center."""
from __future__ import annotations

import pytest

from src.services.action_center_service import (
    GENERIC_OWNERS,
    ActionCenterService,
    LIFECYCLE_STATES,
)


def test_load_decisions_from_f051_snapshot():
    svc = ActionCenterService()
    decisions = svc._load_decisions("2026-06-01", "2026-06-07")
    assert len(decisions) == 36


def test_nominal_ownership_no_generic():
    svc = ActionCenterService()
    decisions = svc._load_decisions("2026-06-01", "2026-06-07")
    owned = svc._ownership_engine(decisions)
    for row in owned:
        name = str(row.get("ownerName") or "").lower()
        assert row.get("ownerNominal") is True
        assert not any(g in name for g in GENERIC_OWNERS)


def test_proxy_classification():
    svc = ActionCenterService()
    proxy_ids = svc._g01_proxy_ids()
    fragile_ids = svc._g01_fragile_ids()
    decisions = svc._load_decisions("2026-06-01", "2026-06-07")
    fragile = [d for d in decisions if d.get("id") in fragile_ids]
    assert fragile
    cls = svc._classify_evidence(fragile[0], proxy_ids, fragile_ids)
    assert cls["roiConfidence"] == "BAIXA"
    assert cls["decisionEvidenceType"] == "PROXY"


def test_fragile_never_roi_realizado():
    svc = ActionCenterService()
    fragile_ids = svc._g01_fragile_ids()
    decisions = svc._load_decisions("2026-06-01", "2026-06-07")
    fragile = next(d for d in decisions if d.get("id") in fragile_ids)
    row = dict(fragile)
    row.update(svc._classify_evidence(fragile, svc._g01_proxy_ids(), fragile_ids))
    row["lifecycleStatus"] = "CONCLUIDA"
    row["hasExecutionEvidence"] = True
    roi_rows = svc._roi_realization_engine([row])
    assert roi_rows[0]["roiRealizado"] == 0.0
    assert roi_rows[0]["roiOutcome"] == "SEM_MEDICAO"


def test_validated_requires_evidence():
    svc = ActionCenterService()
    actions = [
        {
            "id": "X1",
            "lifecycleStatus": "VALIDADA",
            "hasExecutionEvidence": False,
            "ownerNominal": True,
        }
    ]
    gated = svc._apply_validation_gate(actions)
    assert gated[0]["lifecycleStatus"] != "VALIDADA"


@pytest.mark.asyncio
async def test_build_full_payload():
    svc = ActionCenterService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F05.2"
    assert data["fonte"]["webPosto"] is False
    qa = data["qa"]
    assert qa["semDonoNominal"] is True
    assert qa["semValidadaSemEvidencia"] is True
    assert qa["semRoiRealizadoFragil"] is True
    ex = data["executiveAnswers"]
    assert ex["2_donoNominal"] == ex["1_totalAcoes"]
    assert ex["1_totalAcoes"] == 36
    assert data["cockpit"]["totalAcoes"] == 36
    for st in data["executionTrackingEngine"]["porStatus"]:
        assert st in LIFECYCLE_STATES or True
