from src.services.departmental_fact_store import DepartmentalFactStore
from src.services.departmental_history_service import DepartmentalHistoryService


class FakeKpis:
    def __init__(self, store, incomplete_day=None):
        self.store = store
        self.incomplete_day = incomplete_day

    def build_dre(self, company, day):
        stored = self.store.load(company, day)
        if not stored:
            return None
        value = stored["data"]["value"]
        return {
            "period": {"start": day, "end": day},
            "coverage": {
                "salesComplete": day != self.incomplete_day,
                "costsComplete": day != self.incomplete_day,
            },
            "lines": [
                {
                    "department": department,
                    "revenue": str(value),
                    "costOfRevenue": "40",
                    "grossMarginValue": str(value - 40),
                }
                for department in ("combustiveis", "conveniencia", "lubrificantes")
            ]
        }


def save_day(store, day, value):
    store.save({"companyCode": 11495, "day": day, "value": value, "batches": {}})


def test_history_only_compares_complete_equivalent_periods(tmp_path):
    store = DepartmentalFactStore(tmp_path)
    save_day(store, "2026-07-22", 100)
    save_day(store, "2026-07-23", 120)
    result = DepartmentalHistoryService(store, FakeKpis(store)).build(
        11495, "2026-07-23", "2026-07-23"
    )

    assert result["comparable"] is True
    revenue = result["departments"][0]["variances"]["revenue"]
    assert revenue == {"current": "120.00", "prior": "100.00", "absolute": "20.00", "percent": "20.00"}


def test_history_exposes_missing_days_and_does_not_invent_variance(tmp_path):
    store = DepartmentalFactStore(tmp_path)
    save_day(store, "2026-07-23", 120)
    result = DepartmentalHistoryService(store, FakeKpis(store)).build(
        11495, "2026-07-23", "2026-07-23"
    )

    assert result["comparable"] is False
    assert result["priorMissingDays"] == ["2026-07-22"]
    assert result["departments"][0]["variances"]["revenue"]["absolute"] is None


def test_store_lists_only_valid_company_materializations(tmp_path):
    store = DepartmentalFactStore(tmp_path)
    save_day(store, "2026-07-23", 120)
    (tmp_path / "departmental-facts_11495_invalid.json").write_text("{}", encoding="utf-8")
    assert store.list_days(11495) == ["2026-07-23"]


def test_present_but_non_equivalent_day_blocks_comparison(tmp_path):
    store = DepartmentalFactStore(tmp_path)
    save_day(store, "2026-07-22", 100)
    save_day(store, "2026-07-23", 120)
    result = DepartmentalHistoryService(store, FakeKpis(store, "2026-07-23")).build(
        11495, "2026-07-23", "2026-07-23"
    )
    assert result["comparable"] is False
    assert result["nonEquivalentDays"] == ["2026-07-23"]


def test_history_rejects_unbounded_period(tmp_path):
    service = DepartmentalHistoryService(DepartmentalFactStore(tmp_path), FakeKpis(DepartmentalFactStore(tmp_path)))
    try:
        service.build(11495, "2025-01-01", "2026-07-23")
    except ValueError as exc:
        assert str(exc) == "PERIOD_TOO_LARGE"
    else:
        raise AssertionError("Intervalo excessivo deveria ser rejeitado")
