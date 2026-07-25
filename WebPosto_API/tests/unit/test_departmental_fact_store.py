from decimal import Decimal

from src.services.departmental_fact_store import DepartmentalFactStore


def sample_result(company=11495, day="2026-07-23"):
    return {
        "materialized": True,
        "publishable": False,
        "companyCode": company,
        "day": day,
        "blockingReasons": ["QUARANTINE_ABOVE_TOLERANCE:expenses"],
        "pagination": {"produto": {"complete": True}},
        "catalogCoverage": {"products": 10, "productsWithGroup": 9},
        "classificationCoverage": {},
        "batches": {
            "sales": {
                "facts": [{"fact_id": "SALE:1"}],
                "quarantine": [],
                "rejected_unlicensed": 0,
                "duplicates_removed": 0,
                "identity_conflicts": 0,
                "source_total": Decimal("10.00"),
                "reconciled_total": Decimal("10.00"),
                "reconciliation_difference": Decimal("0.00"),
            }
        },
    }


def test_store_saves_atomically_and_returns_quality_summary(tmp_path):
    store = DepartmentalFactStore(tmp_path)
    target = store.save(sample_result())

    assert target.exists()
    assert not list(tmp_path.glob("*.tmp"))
    summary = store.quality_summary(11495, "2026-07-23")
    assert summary["materialized"] is True
    assert summary["publishable"] is False
    assert summary["batches"]["sales"]["classified"] == 1
    assert summary["batches"]["sales"]["reconciliationDifference"] == "0.00"


def test_store_isolates_company_and_day(tmp_path):
    store = DepartmentalFactStore(tmp_path)
    store.save(sample_result(11495, "2026-07-23"))
    store.save(sample_result(5555, "2026-07-24"))

    assert store.load(11495, "2026-07-24") is None
    assert store.load(5555, "2026-07-24")["data"]["companyCode"] == 5555


def test_corrupt_snapshot_is_not_treated_as_valid(tmp_path):
    store = DepartmentalFactStore(tmp_path)
    path = tmp_path / "departmental-facts_11495_2026-07-23.json"
    path.write_text("{incompleto", encoding="utf-8")

    assert store.load(11495, "2026-07-23") is None


def test_store_cache_is_invalidated_after_save(tmp_path):
    store = DepartmentalFactStore(tmp_path)
    first = sample_result()
    first["marker"] = "first"
    second = {**first, "marker": "second", "extra": "changes-file-size"}

    store.save(first)
    assert store.load(11495, "2026-07-23")["data"]["marker"] == "first"

    store.save(second)
    assert store.load(11495, "2026-07-23")["data"]["marker"] == "second"
