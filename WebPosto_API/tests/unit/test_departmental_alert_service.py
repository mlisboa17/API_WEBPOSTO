import pytest

from src.services.departmental_alert_service import DepartmentalAlertService, DepartmentalAlertStore


class FakeKpis:
    def __init__(self, *, missing=False, complete=True, negative=False):
        self.missing = missing
        self.complete = complete
        self.negative = negative

    def build_dre(self, company, day):
        if self.missing:
            return None
        return {
            "coverage": {
                "salesComplete": self.complete,
                "costsComplete": self.complete,
                "expensesComplete": False,
            },
            "lines": [
                {
                    "department": department,
                    "grossMarginValue": "-10" if self.negative else "10",
                    "lineage": {"endpoints": ["/INTEGRACAO/VENDA_ITEM"]},
                }
                for department in ("combustiveis", "conveniencia", "lubrificantes")
            ],
        }


def test_financial_alert_only_uses_complete_coverage(tmp_path):
    result = DepartmentalAlertService(
        FakeKpis(complete=False, negative=True),
        DepartmentalAlertStore(tmp_path / "alerts.json"),
    ).evaluate("2026-07-23")
    rules = {item["rule"] for item in result["alerts"]}
    assert "NEGATIVE_GROSS_MARGIN" not in rules
    assert rules == {"FINANCIAL_COVERAGE_INCOMPLETE", "EXPENSE_CLASSIFICATION_INCOMPLETE"}


def test_negative_margin_has_evidence_owner_and_impact(tmp_path):
    result = DepartmentalAlertService(
        FakeKpis(negative=True),
        DepartmentalAlertStore(tmp_path / "alerts.json"),
    ).evaluate("2026-07-23")
    alert = next(item for item in result["alerts"] if item["rule"] == "NEGATIVE_GROSS_MARGIN")
    assert alert["estimatedImpactBRL"] == 10.0
    assert alert["suggestedOwner"]
    assert alert["evidence"]["lineage"]


def test_closure_requires_justification_or_evidence_and_leaves_audit_event(tmp_path):
    store = DepartmentalAlertStore(tmp_path / "alerts.json")
    result = DepartmentalAlertService(FakeKpis(), store).evaluate("2026-07-23")
    alert_id = result["alerts"][0]["id"]
    with pytest.raises(ValueError):
        store.update(alert_id, "CLOSE", "auditor")
    closed = store.update(alert_id, "CLOSE", "auditor", evidence="ticket-123")
    assert closed["status"] == "CLOSED"
    assert store.load()["events"][-1]["actor"] == "auditor"


def test_read_does_not_evaluate_or_write(tmp_path):
    path = tmp_path / "alerts.json"
    service = DepartmentalAlertService(FakeKpis(), DepartmentalAlertStore(path))

    result = service.list("2026-07-23")

    assert result["alerts"] == []
    assert result["evaluationRequired"] is True
    assert not path.exists()
