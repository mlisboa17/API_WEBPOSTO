from src.services.departmental_fact_store import DepartmentalFactStore
from src.services.departmental_operations_service import DepartmentalOperationsService


class FakeAlerts:
    def list(self, day):
        return {
            "alerts": [{"severity": "CRITICAL"}, {"severity": "WARNING"}],
            "evaluationRequired": False,
            "lastEvaluationAt": "2026-07-23T12:00:00+00:00",
        }


def test_health_never_returns_secret_values_and_reports_missing_materialization(tmp_path):
    result = DepartmentalOperationsService(DepartmentalFactStore(tmp_path), FakeAlerts()).health("2026-07-23")
    assert result["status"] == "DEGRADED"
    assert result["credentials"]["valuesReturned"] is False
    assert result["credentials"]["secretsExposed"] is False
    assert all(item["blockingReasons"] == ["MATERIALIZATION_MISSING"] for item in result["companies"])


def test_daily_report_summarizes_alerts(tmp_path):
    result = DepartmentalOperationsService(DepartmentalFactStore(tmp_path), FakeAlerts()).daily_report("2026-07-23")
    assert result["alertSummary"] == {"total": 2, "critical": 1, "warning": 1}
    assert result["alertEvaluationRequired"] is False


def test_weekly_report_exposes_missing_days_instead_of_zero_fill(tmp_path):
    result = DepartmentalOperationsService(DepartmentalFactStore(tmp_path), FakeAlerts()).weekly_report("2026-07-23")
    assert result["complete"] is False
    assert result["comparisonPublished"] is False
    assert all(company["missingDays"] for company in result["companies"])
