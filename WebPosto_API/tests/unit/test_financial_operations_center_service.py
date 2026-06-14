"""Unit tests — F08.3 Financial Operations Center."""
from __future__ import annotations

from src.services.financial_operations_center_service import (
    FinancialOperationsCenterService,
    _classify_health_score,
    _compute_executive_health_score,
    _score_alerts,
    _score_circuits,
    _score_recovery,
    _score_scheduler,
    _timeline_from_sources,
)


def test_classify_health_score_bands():
    assert _classify_health_score(95) == "EXCELENTE"
    assert _classify_health_score(80) == "BOM"
    assert _classify_health_score(60) == "ATENÇÃO"
    assert _classify_health_score(30) == "CRÍTICO"


def test_executive_health_score_weights():
    result = _compute_executive_health_score(
        snapshot_health_score=100.0,
        scheduler={"status": "ENABLED"},
        recovery={"enabled": True, "pendingCount": 0},
        alert_counts={"INFO": 0, "WARNING": 0, "CRITICAL": 0},
        circuit={"status": "CLOSED"},
    )
    assert result["score"] == 100.0
    assert result["classification"] == "EXCELENTE"
    assert result["components"]["snapshotHealth"] == 30.0
    assert result["components"]["scheduler"] == 20.0


def test_score_scheduler_disabled():
    assert _score_scheduler({"status": "DISABLED"}) == 40.0


def test_score_recovery_pending():
    assert _score_recovery({"enabled": True, "pendingCount": 2, "recoveredCount": 0}) < 50


def test_score_alerts_critical():
    assert _score_alerts({"CRITICAL": 2, "WARNING": 0}) < 30


def test_score_circuits_open():
    assert _score_circuits({"status": "OPEN"}) == 20.0


def test_timeline_orders_recent_first():
    events = _timeline_from_sources(
        executions=[
            {"finished_at": "2026-06-01T10:00:00", "snapshot_type": "overview", "success": True},
            {"finished_at": "2026-06-03T10:00:00", "snapshot_type": "expenses", "success": True},
        ],
        recovery={"jobs": []},
        alerts=[],
        retention_removed=[],
        circuit={"status": "CLOSED"},
        scheduler={},
    )
    assert events[0]["timestamp"] >= events[-1]["timestamp"]


def test_operations_center_summary_snapshot_first(monkeypatch):
    svc = FinancialOperationsCenterService()

    monkeypatch.setattr(
        "src.services.financial_operations_center_service.get_financial_scheduler",
        lambda: type("S", (), {"get_scheduler_status": lambda self: {"status": "ENABLED"}})(),
    )
    monkeypatch.setattr(
        "src.services.financial_operations_center_service.get_financial_auto_recovery",
        lambda: type("R", (), {"get_recovery_status": lambda self: {"enabled": True, "pendingCount": 0, "jobs": []}})(),
    )
    monkeypatch.setattr(
        svc,
        "_health",
        type(
            "H",
            (),
            {
                "assess_key": lambda *a, **k: {
                    "summary": {
                        "averageHealthScore": 90,
                        "coverageComplete": True,
                        "totalSnapshots": 4,
                        "expectedSnapshots": 4,
                    }
                },
                "inventory": lambda self: [{}] * 4,
            },
        )(),
    )
    monkeypatch.setattr(
        "src.services.financial_operations_center_service.get_alert_service",
        lambda: type("A", (), {"generate": lambda *a: [], "active_count": lambda self, a: {"INFO": 0, "WARNING": 0, "CRITICAL": 0}})(),
    )
    monkeypatch.setattr(
        "src.services.financial_operations_center_service.get_execution_store",
        lambda: type("E", (), {"list_recent": lambda self, n: []})(),
    )
    monkeypatch.setattr(
        "src.services.financial_operations_center_service.get_retention_service",
        lambda: type(
            "Ret",
            (),
            {"list_removed_history": lambda self, n: [], "list_expired_snapshots": lambda self: []},
        )(),
    )
    monkeypatch.setattr(
        "src.services.financial_operations_center_service.get_webposto_client",
        lambda: type("C", (), {"get_circuit_status": lambda self: {"endpoints": {"despesas_financeiro_rede": "CLOSED"}, "summary": {"financial": {}}}})(),
    )

    summary = svc.get_operations_summary("2026-06-01", "2026-06-07")
    assert summary["snapshotFirst"] is True
    assert summary["liveOptional"] is True
    assert "executiveHealthScore" in summary
    assert summary["cards"]["circuitStatus"] == "CLOSED"
