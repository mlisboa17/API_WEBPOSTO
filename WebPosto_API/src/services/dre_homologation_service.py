"""Validação matemática e homologação formal da DRE departamental."""

from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DreApproval(BaseModel):
    model_config = ConfigDict(frozen=True)

    period_start: str
    period_end: str
    reviewer: str = Field(min_length=2)
    rationale: str = Field(min_length=3)
    payload_hash: str
    approved_at: str


class DreHomologationService:
    def __init__(self, path: str | Path = "snapshots/dre_approvals/store.json") -> None:
        self._path = Path(path)

    @staticmethod
    def _dec(value: Any) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"))

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        lines = payload.get("lines") or []
        blockers: list[str] = []
        if payload.get("consolidatedGenericResult") is not False:
            blockers.append("RESULTADO_GENERICO_PROIBIDO")
        if len(lines) != 9:
            blockers.append("NOVE_LINHAS_OBRIGATORIAS")
        math_errors: list[dict[str, Any]] = []
        for row in lines:
            if row.get("status") != "LIBERADO":
                blockers.append(f"LINHA_BLOQUEADA:{row.get('companyCode')}:{row.get('department')}")
                continue
            revenue = self._dec(row["revenue"])
            cost = self._dec(row["cost"])
            gross = self._dec(row["grossMargin"])
            expenses = self._dec(row["expenses"])
            result = self._dec(row["operatingResult"])
            if gross != revenue - cost or result != gross - expenses:
                math_errors.append({
                    "companyCode": row.get("companyCode"),
                    "department": row.get("department"),
                    "expectedGrossMargin": str(revenue - cost),
                    "expectedOperatingResult": str(gross - expenses),
                })
        if math_errors:
            blockers.append("DIVERGENCIA_MATEMATICA")
        return {
            "valid": not blockers,
            "readyForApproval": not blockers,
            "blockers": sorted(set(blockers)),
            "mathErrors": math_errors,
            "linesValidated": len(lines),
        }

    @staticmethod
    def payload_hash(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return sha256(canonical.encode("utf-8")).hexdigest()

    def approve(self, payload: dict[str, Any], reviewer: str, rationale: str) -> DreApproval:
        validation = self.validate(payload)
        if not validation["readyForApproval"]:
            raise ValueError("DRE possui bloqueios e nao pode ser homologada")
        period = payload.get("period") or {}
        approval = DreApproval(
            period_start=str(period.get("start") or ""),
            period_end=str(period.get("end") or ""),
            reviewer=reviewer,
            rationale=rationale,
            payload_hash=self.payload_hash(payload),
            approved_at=datetime.now(timezone.utc).isoformat(),
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        existing: list[dict[str, Any]] = []
        if self._path.exists():
            try:
                existing = json.loads(self._path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = []
        existing.append(approval.model_dump(mode="json"))
        self._path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        return approval
