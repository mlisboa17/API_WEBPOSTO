import pytest
from concurrent.futures import ThreadPoolExecutor

from src.services.departmental_goal_service import DepartmentalGoalService


def goal(**overrides):
    data = {
        "companyCode": 11495,
        "department": "combustiveis",
        "metric": "grossMarginPercent",
        "targetValue": "15",
        "periodStart": "2026-08-01",
        "periodEnd": "2026-08-31",
    }
    data.update(overrides)
    return data


def test_goal_stays_pending_without_named_approval(tmp_path):
    service = DepartmentalGoalService(tmp_path / "goals.json")
    assert service.save(goal())["status"] == "PENDING_APPROVAL"
    assert service.list()[0]["approvedBy"] is None


def test_goal_becomes_active_with_approval_and_invalid_scope_is_rejected(tmp_path):
    service = DepartmentalGoalService(tmp_path / "goals.json")
    assert service.save(goal(approvedBy="Diretoria"))["status"] == "ACTIVE"
    with pytest.raises(ValueError):
        service.save(goal(companyCode=999))


def test_goal_rejects_invalid_period(tmp_path):
    service = DepartmentalGoalService(tmp_path / "goals.json")
    with pytest.raises(ValueError, match="INVALID_PERIOD"):
        service.save(goal(periodStart="2026-09-01", periodEnd="2026-08-01"))


def test_concurrent_store_instances_do_not_lose_updates(tmp_path):
    path = tmp_path / "goals.json"

    def save(index: int) -> None:
        DepartmentalGoalService(path).save(
            goal(
                metric="revenue",
                periodStart=f"2026-08-{index + 1:02d}",
                periodEnd=f"2026-08-{index + 1:02d}",
            )
        )

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(save, range(6)))

    assert len(DepartmentalGoalService(path).list()) == 6
    assert not path.with_suffix(".json.lock").exists()
