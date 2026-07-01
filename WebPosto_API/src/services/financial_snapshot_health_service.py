"""F08.1 — Saúde, freshness, cobertura e confiança de snapshots financeiros (sem WebPosto live)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.services.financial_snapshot_service import FINANCIAL_DIR, SNAPSHOT_KINDS, FinancialSnapshotService

KIND_LABELS = {
    "financial_overview": "Receitas / Overview",
    "financial_expenses": "Despesas",
    "financial_receivables": "Contas a receber",
    "financial_payables": "Contas a pagar",
    "financial_sales": "Vendas",
}


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00").split("+")[0])
    except ValueError:
        return None


def _snapshot_age_hours(last_updated: str | None) -> float | None:
    ts = _parse_ts(last_updated)
    if not ts:
        return None
    return max(0.0, (datetime.now() - ts).total_seconds() / 3600.0)


def _freshness_status(age_hours: float | None) -> str:
    if age_hours is None:
        return "CRITICAL"
    if age_hours < 24:
        return "HEALTHY"
    if age_hours <= 72:
        return "WARNING"
    return "CRITICAL"


def _record_count(kind: str, data: Any) -> int:
    if not isinstance(data, dict):
        return 0
    if kind == "financial_overview":
        return len(data.get("postos") or [])
    rows = data.get("data")
    if isinstance(rows, list):
        return len(rows)
    return int(data.get("total") or 0)


def _lineage_metrics(kind: str, data: Any) -> tuple[bool, float]:
    if kind not in {"financial_expenses", "financial_payables", "financial_receivables"}:
        if kind == "financial_overview" and isinstance(data, dict) and data.get("postos"):
            return True, 70.0
        return False, 0.0
    rows = (data or {}).get("data") if isinstance(data, dict) else []
    if not isinstance(rows, list) or not rows:
        return False, 0.0
    traced = sum(1 for row in rows if row.get("lineagePath") or row.get("rastreabilidadeOk"))
    confidences = [float(row.get("lineageConfidence") or 0) for row in rows if row.get("lineageConfidence") is not None]
    avg_conf = sum(confidences) / len(confidences) if confidences else (100.0 if traced else 0.0)
    return traced > 0, avg_conf


def _health_score(*, age_hours: float | None, lineage_present: bool, lineage_conf: float, record_count: int, source: str | None) -> int:
    score = 0
    if age_hours is not None:
        if age_hours < 24:
            score += 40
        elif age_hours <= 72:
            score += 25
        else:
            score += 5
    if lineage_present:
        score += 20 + min(10, int(lineage_conf / 10))
    if record_count > 0:
        score += 20
    if source:
        score += 10
    return min(100, score)


def _health_classification(score: int, freshness: str) -> str:
    if freshness == "CRITICAL" or score < 50:
        return "CRITICAL"
    if freshness == "WARNING" or score < 80:
        return "WARNING"
    return "HEALTHY"


def _confidence_level(classification: str, lineage_present: bool, record_count: int, kind: str, covered: bool) -> str:
    if classification == "HEALTHY" and lineage_present and record_count > 0 and covered:
        return "ALTA"
    if classification == "CRITICAL" or (not lineage_present and kind == "financial_expenses"):
        return "BAIXA"
    return "MEDIA"


class FinancialSnapshotHealthService:
    def __init__(self, snapshots: FinancialSnapshotService | None = None) -> None:
        self._snapshots = snapshots or FinancialSnapshotService()

    def inventory(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        fin_dir = Path(FINANCIAL_DIR)
        if not fin_dir.is_dir():
            return items
        for path in sorted(fin_dir.glob("financial_*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            kind = str(payload.get("kind") or "")
            data = payload.get("data")
            size_bytes = path.stat().st_size
            age = _snapshot_age_hours(payload.get("lastUpdated"))
            lineage_present, lineage_conf = _lineage_metrics(kind, data)
            records = _record_count(kind, data)
            freshness = _freshness_status(age)
            score = _health_score(
                age_hours=age,
                lineage_present=lineage_present,
                lineage_conf=lineage_conf,
                record_count=records,
                source=payload.get("source"),
            )
            classification = _health_classification(score, freshness)
            items.append(
                {
                    "snapshotType": kind,
                    "label": KIND_LABELS.get(kind, kind),
                    "snapshotKey": payload.get("key"),
                    "exists": True,
                    "lastUpdated": payload.get("lastUpdated"),
                    "generatedAt": payload.get("lastUpdated"),
                    "sizeBytes": size_bytes,
                    "source": payload.get("source"),
                    "homologated": bool(payload.get("homologated")),
                    "recordCount": records,
                    "lineagePresent": lineage_present,
                    "lineageConfidence": round(lineage_conf, 1),
                    "snapshotAgeHours": round(age, 2) if age is not None else None,
                    "freshnessStatus": freshness,
                    "healthScore": score,
                    "healthStatus": classification,
                    "confidenceLevel": _confidence_level(classification, lineage_present, records, kind, records > 0 or kind in {"financial_receivables", "financial_payables"}),
                    "filePath": str(path.relative_to(fin_dir.parent.parent)) if path.is_relative_to(fin_dir.parent.parent) else str(path),
                }
            )
        return items

    def assess_key(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        key = self._snapshots.build_key(data_inicial, data_final, empresa_codigo)
        kinds: list[dict[str, Any]] = []
        for kind in SNAPSHOT_KINDS:
            payload = self._snapshots.load_kind(kind, key, allow_stale=True)
            if not payload:
                kinds.append(
                    {
                        "snapshotType": kind,
                        "label": KIND_LABELS.get(kind, kind),
                        "snapshotKey": key,
                        "exists": False,
                        "healthStatus": "CRITICAL",
                        "confidenceLevel": "BAIXA",
                        "healthScore": 0,
                        "recordCount": 0,
                        "lineagePresent": False,
                        "coverageGap": True,
                    }
                )
                continue
            data = payload.get("data")
            age = _snapshot_age_hours(payload.get("lastUpdated"))
            lineage_present, lineage_conf = _lineage_metrics(kind, data)
            records = _record_count(kind, data)
            freshness = _freshness_status(age)
            score = _health_score(
                age_hours=age,
                lineage_present=lineage_present,
                lineage_conf=lineage_conf,
                record_count=records,
                source=payload.get("source"),
            )
            classification = _health_classification(score, freshness)
            kinds.append(
                {
                    "snapshotType": kind,
                    "label": KIND_LABELS.get(kind, kind),
                    "snapshotKey": key,
                    "exists": True,
                    "lastUpdated": payload.get("lastUpdated"),
                    "source": payload.get("source"),
                    "recordCount": records,
                    "lineagePresent": lineage_present,
                    "lineageConfidence": round(lineage_conf, 1),
                    "snapshotAgeHours": round(age, 2) if age is not None else None,
                    "freshnessStatus": freshness,
                    "healthScore": score,
                    "healthStatus": classification,
                    "confidenceLevel": _confidence_level(classification, lineage_present, records, kind, records > 0),
                    "coverageGap": records == 0 and kind in {"financial_overview", "financial_expenses"},
                }
            )

        existing = [k for k in kinds if k.get("exists")]
        scores = [k["healthScore"] for k in existing] or [0]
        confidences = [k["confidenceLevel"] for k in existing] or ["BAIXA"]
        statuses = [k["healthStatus"] for k in existing] or ["CRITICAL"]
        ages = [k["snapshotAgeHours"] for k in existing if k.get("snapshotAgeHours") is not None]

        summary = {
            "snapshotKey": key,
            "period": {"dataInicial": data_inicial, "dataFinal": data_final},
            "totalSnapshots": len(existing),
            "expectedSnapshots": len(SNAPSHOT_KINDS),
            "healthy": sum(1 for k in kinds if k.get("healthStatus") == "HEALTHY"),
            "warning": sum(1 for k in kinds if k.get("healthStatus") == "WARNING"),
            "critical": sum(1 for k in kinds if k.get("healthStatus") == "CRITICAL"),
            "averageHealthScore": round(sum(scores) / len(scores), 1),
            "averageConfidence": confidences[0] if len(set(confidences)) == 1 else "MEDIA",
            "oldestAgeHours": max(ages) if ages else None,
            "newestAgeHours": min(ages) if ages else None,
            "coverageComplete": all(not k.get("coverageGap") for k in kinds if k.get("exists")),
            "coverageGaps": [k["label"] for k in kinds if k.get("coverageGap") or not k.get("exists")],
            "overallStatus": "CRITICAL" if "CRITICAL" in statuses else ("WARNING" if "WARNING" in statuses else "HEALTHY"),
        }
        return {"summary": summary, "snapshots": kinds}

    def assess_kind_payload(self, kind: str, payload: dict[str, Any] | None) -> dict[str, Any] | None:
        if not payload:
            return None
        data = payload.get("data")
        age = _snapshot_age_hours(payload.get("lastUpdated"))
        lineage_present, lineage_conf = _lineage_metrics(kind, data)
        records = _record_count(kind, data)
        freshness = _freshness_status(age)
        score = _health_score(
            age_hours=age,
            lineage_present=lineage_present,
            lineage_conf=lineage_conf,
            record_count=records,
            source=payload.get("source"),
        )
        classification = _health_classification(score, freshness)
        return {
            "snapshotType": kind,
            "source": payload.get("source"),
            "lastUpdated": payload.get("lastUpdated"),
            "snapshotAgeHours": round(age, 2) if age is not None else None,
            "freshnessStatus": freshness,
            "healthScore": score,
            "healthStatus": classification,
            "confidenceLevel": _confidence_level(classification, lineage_present, records, kind, records > 0),
            "lineagePresent": lineage_present,
            "recordCount": records,
        }

    def cockpit(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        assessment = self.assess_key(data_inicial, data_final, empresa_codigo)
        inventory = self.inventory()
        return {
            "assessment": assessment,
            "inventory": inventory,
            "inventoryTotal": len(inventory),
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
        }

    def dw_rows(self, data_inicial: str, data_final: str, empresa_codigo: str | int | None = None) -> list[dict[str, Any]]:
        assessment = self.assess_key(data_inicial, data_final, empresa_codigo)
        rows: list[dict[str, Any]] = []
        for item in assessment["snapshots"]:
            rows.append(
                {
                    "snapshot_key": item.get("snapshotKey"),
                    "snapshot_type": item.get("snapshotType"),
                    "period_start": data_inicial,
                    "period_end": data_final,
                    "source": item.get("source") or "unknown",
                    "generated_at": item.get("lastUpdated"),
                    "health_score": item.get("healthScore"),
                    "confidence_level": item.get("confidenceLevel"),
                    "age_hours": item.get("snapshotAgeHours"),
                    "health_status": item.get("healthStatus"),
                    "record_count": item.get("recordCount"),
                    "lineage_preserved": bool(item.get("lineagePresent")),
                }
            )
        return rows
