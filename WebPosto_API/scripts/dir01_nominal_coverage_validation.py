#!/usr/bin/env python3
"""DIR-01 nominal coverage — validação antes/depois + auditoria FASE 1-2."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from src.interfaces.http.app import create_app
from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService

DECISION_ID = "175da101-6f68-42f4-9d2b-9b42e6cedea2"
BEFORE = {
    "EXACT": 0,
    "PROBABLE": 3,
    "AMBIGUOUS": 0,
    "NO_MATCH": 13,
    "with_funcionario": 3,
    "with_caixa": 3,
    "with_turno": 3,
    "total_with_funcionario_amount": 450.0,
    "total_without_funcionario_amount": 7951.0,
    "evidence_items_count": 16,
    "evidence_items_total": 8401.0,
}


async def main() -> int:
    service = DecisionEvidenceService()
    result = await service.get_evidence(DECISION_ID)
    if not result:
        print("FAIL: decisão não encontrada")
        return 1

    nominal = (result.source_metadata or {}).get("nominal_enrichment") or {}
    summary = nominal.get("match_summary") or {}
    vale_audit = nominal.get("vale_endpoint_audit") or {}
    prestacao = nominal.get("prestacao_audit") or {}

    client = TestClient(create_app())
    http = client.get(f"/api/v1/decisions/{DECISION_ID}/evidence")

    report = {
        "decision_id": DECISION_ID,
        "before": BEFORE,
        "after": {
            "EXACT": summary.get("EXACT", 0),
            "PROBABLE": summary.get("PROBABLE", 0),
            "AMBIGUOUS": summary.get("AMBIGUOUS", 0),
            "NO_MATCH": summary.get("NO_MATCH", 0),
            "with_funcionario": summary.get("with_funcionario", 0),
            "with_caixa": summary.get("with_caixa", 0),
            "with_turno": summary.get("with_turno", 0),
            "total_with_funcionario_amount": summary.get("total_with_funcionario_amount", 0),
            "total_without_funcionario_amount": summary.get("total_without_funcionario_amount", 0),
            "evidence_items_count": result.evidence_items_count,
            "evidence_items_total": result.evidence_items_total,
        },
        "vale_endpoint_audit": vale_audit,
        "prestacao_audit": prestacao,
        "api_http_status": http.status_code,
        "beneficiary_vs_review": nominal.get("beneficiary_vs_review"),
        "forced_match": nominal.get("forced_match", False),
        "limitations": result.limitations,
    }

    out = ROOT / "docs" / "validation" / "DIR_01_NOMINAL_COVERAGE.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
