"""Sprint 7 — alertas departamentais reproduzíveis e fluxo auditável."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.management_scope import LICENSED_COMPANIES
from src.services.departmental_kpi_service import DepartmentalKpiService
from src.services.json_file_lock import InterProcessFileLock


DEPARTMENT_OWNERS = {
    "combustiveis": "Diretoria Operacional",
    "conveniencia": "Diretoria Comercial",
    "lubrificantes": "Diretoria Comercial",
}


class DepartmentalAlertStore:
    def __init__(self, path: str | Path = ".runtime/departmental_alerts.json") -> None:
        self._path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"schemaVersion": 1, "alerts": {}, "events": []}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schemaVersion": 1, "alerts": {}, "events": []}
        return data if isinstance(data, dict) else {"schemaVersion": 1, "alerts": {}, "events": []}

    def lock(self) -> InterProcessFileLock:
        return InterProcessFileLock(self._path)

    def save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self._path.parent, delete=False) as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
                temp = Path(handle.name)
            os.replace(temp, self._path)
        finally:
            if temp and temp.exists():
                temp.unlink(missing_ok=True)

    def update(self, alert_id: str, action: str, actor: str, *, justification: str | None = None, evidence: str | None = None) -> dict[str, Any] | None:
        with InterProcessFileLock(self._path):
            data = self.load()
            alert = (data.get("alerts") or {}).get(alert_id)
            if not alert:
                return None
            if action == "CLOSE" and not (justification or evidence):
                raise ValueError("CLOSURE_REQUIRES_JUSTIFICATION_OR_EVIDENCE")
            status = {"ACKNOWLEDGE": "ACKNOWLEDGED", "CLOSE": "CLOSED"}[action]
            now = datetime.now(timezone.utc).isoformat()
            alert.update({"status": status, "updatedAt": now})
            event = {"alertId": alert_id, "action": action, "actor": actor, "at": now, "justification": justification, "evidence": evidence}
            data.setdefault("events", []).append(event)
            self.save(data)
            return alert


class DepartmentalAlertService:
    def __init__(self, kpis: DepartmentalKpiService | None = None, store: DepartmentalAlertStore | None = None) -> None:
        self._kpis = kpis or DepartmentalKpiService()
        self._store = store or DepartmentalAlertStore()

    @staticmethod
    def _id(company: int, day: str, department: str, rule: str) -> str:
        raw = f"{company}|{day}|{department}|{rule}".encode()
        return hashlib.sha256(raw).hexdigest()[:20]

    def evaluate(self, day: str) -> dict[str, Any]:
        generated: dict[str, dict[str, Any]] = {}
        for company in LICENSED_COMPANIES:
            statement = self._kpis.build_dre(company.empresa_codigo, day)
            if statement is None:
                alert_id = self._id(company.empresa_codigo, day, "todos", "MATERIALIZATION_MISSING")
                generated[alert_id] = self._alert(alert_id, company.empresa_codigo, "todos", day, "CRITICAL", "MATERIALIZATION_MISSING", "Materialização diária ausente.", "Operação de Dados", None, {"day": day})
                continue
            coverage = statement.get("coverage") or {}
            financially_complete = coverage.get("salesComplete") is True and coverage.get("costsComplete") is True
            for line in statement.get("lines") or []:
                department = line["department"]
                if not financially_complete:
                    rule = "FINANCIAL_COVERAGE_INCOMPLETE"
                    alert_id = self._id(company.empresa_codigo, day, department, rule)
                    generated[alert_id] = self._alert(alert_id, company.empresa_codigo, department, day, "CRITICAL", rule, "Cobertura de vendas ou custos incompleta; análise financeira bloqueada.", "Diretoria Financeira", None, {"coverage": coverage, "lineage": line.get("lineage")})
                elif float(line.get("grossMarginValue") or 0) < 0:
                    rule = "NEGATIVE_GROSS_MARGIN"
                    alert_id = self._id(company.empresa_codigo, day, department, rule)
                    generated[alert_id] = self._alert(alert_id, company.empresa_codigo, department, day, "CRITICAL", rule, "Margem bruta negativa com cobertura equivalente.", DEPARTMENT_OWNERS[department], abs(float(line["grossMarginValue"])), {"lineage": line.get("lineage"), "grossMarginValue": line["grossMarginValue"]})
                if coverage.get("expensesComplete") is not True:
                    rule = "EXPENSE_CLASSIFICATION_INCOMPLETE"
                    alert_id = self._id(company.empresa_codigo, day, department, rule)
                    generated[alert_id] = self._alert(alert_id, company.empresa_codigo, department, day, "WARNING", rule, "Despesas sem classificação departamental completa; lucro não publicado.", "Diretoria Financeira", None, {"coverage": coverage})
        with self._store.lock():
            stored = self._store.load()
            previous = stored.get("alerts") or {}
            now = datetime.now(timezone.utc).isoformat()
            for alert_id, alert in generated.items():
                old = previous.get(alert_id) or {}
                alert["status"] = old.get("status", "OPEN")
                alert["createdAt"] = old.get("createdAt", now)
                alert["updatedAt"] = now
            stored.update({"schemaVersion": 1, "alerts": generated, "lastEvaluationAt": now, "evaluationDay": day})
            self._store.save(stored)
            return {"day": day, "alerts": list(generated.values()), "events": stored.get("events") or [], "reviewRequired": True}

    def list(self, day: str) -> dict[str, Any]:
        stored = self._store.load()
        matches_day = stored.get("evaluationDay") == day
        alerts = list((stored.get("alerts") or {}).values()) if matches_day else []
        return {
            "day": day,
            "alerts": alerts,
            "events": stored.get("events") or [],
            "lastEvaluationAt": stored.get("lastEvaluationAt") if matches_day else None,
            "evaluationRequired": not matches_day,
            "reviewRequired": True,
        }

    @staticmethod
    def _alert(alert_id: str, company: int, department: str, day: str, severity: str, rule: str, message: str, owner: str, impact: float | None, evidence: dict[str, Any]) -> dict[str, Any]:
        return {"id": alert_id, "companyCode": company, "department": department, "period": {"start": day, "end": day}, "severity": severity, "rule": rule, "message": message, "estimatedImpactBRL": impact, "suggestedOwner": owner, "dueInDays": 1 if severity == "CRITICAL" else 3, "evidence": evidence, "controlAssessment": "REQUIRES_QUALIFIED_REVIEW"}
