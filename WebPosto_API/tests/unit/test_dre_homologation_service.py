from pathlib import Path
from uuid import uuid4

from src.services.dre_homologation_service import DreHomologationService


def payload(status="LIBERADO"):
    lines = []
    for company in (11495, 5555, 74014):
        for department in ("combustiveis", "conveniencia", "lubrificantes"):
            lines.append({
                "companyCode": company, "department": department, "status": status,
                "revenue": "100.00", "cost": "60.00", "grossMargin": "40.00",
                "expenses": "10.00", "operatingResult": "30.00",
            })
    return {"period": {"start": "2026-07-01", "end": "2026-07-31"},
            "lines": lines, "consolidatedGenericResult": False}


def service():
    return DreHomologationService(Path("tests/runtime_tmp") / f"dre-{uuid4().hex}.json")


def test_validates_nine_department_lines_and_math() -> None:
    result = service().validate(payload())
    assert result["valid"] is True
    assert result["linesValidated"] == 9


def test_blocks_approval_when_any_line_is_blocked() -> None:
    svc = service()
    data = payload("BLOQUEADO")
    assert svc.validate(data)["readyForApproval"] is False
    try:
        svc.approve(data, "Diretor", "Homologacao mensal")
        assert False
    except ValueError as exc:
        assert "bloqueios" in str(exc)


def test_approval_persists_hash_of_valid_payload() -> None:
    svc = service()
    data = payload()
    approval = svc.approve(data, "Diretor", "Valores conferidos")
    assert approval.payload_hash == svc.payload_hash(data)
