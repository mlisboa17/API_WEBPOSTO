from pathlib import Path
from uuid import uuid4

from src.services.department_review_store import DepartmentReviewStore


def review_path() -> Path:
    return Path("tests/runtime_tmp") / f"reviews-{uuid4().hex}.json"


def test_review_is_persisted_and_retrievable() -> None:
    store = DepartmentReviewStore(review_path())
    record = store.assign("expense:1", "combustiveis", "Diretor", "Centro de custo validado")
    assert store.get("expense:1") == record
    assert store.list_all()[0].department == "combustiveis"


def test_invalid_department_is_rejected() -> None:
    store = DepartmentReviewStore(review_path())
    try:
        store.assign("expense:1", "diversos", "Diretor", "Teste invalido")
        assert False
    except ValueError as exc:
        assert "invalido" in str(exc)


def test_account_rule_is_reused() -> None:
    store = DepartmentReviewStore(review_path())
    rule = store.assign_rule("42", "lubrificantes", "Diretor", "Plano validado")
    assert store.get_rule("42") == rule
    assert store.list_rules()[0].department == "lubrificantes"


def test_shared_allocation_must_sum_one_hundred() -> None:
    store = DepartmentReviewStore(review_path())
    rule = store.assign_allocation(
        "99", {"combustiveis": 50, "conveniencia": 30, "lubrificantes": 20},
        "Diretor", "Despesa compartilhada validada",
    )
    assert store.get_allocation("99") == rule
    assert sum(rule.percentages.values()) == 100


def test_invalid_shared_allocation_is_rejected() -> None:
    store = DepartmentReviewStore(review_path())
    try:
        store.assign_allocation("99", {"combustiveis": 60, "conveniencia": 20},
                                "Diretor", "Rateio incompleto")
        assert False
    except ValueError as exc:
        assert "100" in str(exc)
