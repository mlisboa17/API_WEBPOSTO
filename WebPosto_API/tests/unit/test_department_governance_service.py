from decimal import Decimal

from src.services.department_governance_service import DepartmentGovernanceService


def test_unique_evidence_classifies_department() -> None:
    decision = DepartmentGovernanceService().classify({"centroCusto": "PISTA"})
    assert decision.department == "combustiveis"
    assert decision.confidence == Decimal("0.90")
    assert decision.requires_review is False


def test_conflicting_evidence_goes_to_review() -> None:
    decision = DepartmentGovernanceService().classify({"descricaoDocumento": "PISTA LOJA"})
    assert decision.department is None
    assert decision.method == "CONFLICTING_EVIDENCE"
    assert decision.requires_review is True


def test_missing_evidence_is_not_guessed() -> None:
    decision = DepartmentGovernanceService().classify({"descricaoDocumento": "ENERGIA"})
    assert decision.department is None
    assert decision.method == "NO_EVIDENCE"
