"""Classificação departamental conservadora e explicável."""

import re
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


DEPARTMENT_MARKERS: dict[str, tuple[str, ...]] = {
    "combustiveis": ("COMBUST", "PISTA", "ABASTEC"),
    "conveniencia": ("CONVEN", "LOJA", "RESTAURANTE", "LANCHONETE"),
    "lubrificantes": ("LUBR", "OLEO", "ADITIVO", "FILTRO", "PALHETA", "FLUIDO"),
}


class DepartmentDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    department: str | None
    method: str
    evidence: tuple[str, ...] = ()
    confidence: Decimal = Field(ge=0, le=1)
    requires_review: bool


class DepartmentGovernanceService:
    FIELDS = (
        "planoContaGerencialDescricao", "planoConta", "descricaoDocumento",
        "centroCustoDescricao", "centroCusto",
    )

    def classify(self, row: dict[str, Any]) -> DepartmentDecision:
        blob = re.sub(r"\s+", " ", " ".join(str(row.get(key) or "") for key in self.FIELDS)).upper()
        evidence = {
            department: tuple(marker for marker in markers if marker in blob)
            for department, markers in DEPARTMENT_MARKERS.items()
        }
        hits = {department: markers for department, markers in evidence.items() if markers}
        if len(hits) == 1:
            department, markers = next(iter(hits.items()))
            return DepartmentDecision(
                department=department,
                method="WEBPOSTO_TEXT_EVIDENCE",
                evidence=markers,
                confidence=Decimal("0.90"),
                requires_review=False,
            )
        if len(hits) > 1:
            return DepartmentDecision(
                department=None,
                method="CONFLICTING_EVIDENCE",
                evidence=tuple(f"{department}:{marker}" for department, markers in hits.items() for marker in markers),
                confidence=Decimal("0"),
                requires_review=True,
            )
        return DepartmentDecision(
            department=None,
            method="NO_EVIDENCE",
            confidence=Decimal("0"),
            requires_review=True,
        )
