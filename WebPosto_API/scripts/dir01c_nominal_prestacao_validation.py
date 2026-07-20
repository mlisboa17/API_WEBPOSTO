#!/usr/bin/env python3
"""DIR-01C — validação enriquecimento nominal via Prestação de Contas."""

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
from src.services.decision_evidence.prestacao_nominal_extractor import load_prestacao_nominal_items

DECISION_ID = "175da101-6f68-42f4-9d2b-9b42e6cedea2"
EMPRESA = "74014"
PERIOD_START = "2026-06-05"
PERIOD_END = "2026-07-04"
BEFORE = {
    "EXACT": 0,
    "PROBABLE": 3,
    "AMBIGUOUS": 0,
    "NO_MATCH": 13,
    "with_funcionario": 3,
    "total_with_funcionario_amount": 450.0,
    "total_without_funcionario_amount": 7951.0,
    "coverage_pct_count": 18.8,
    "coverage_pct_amount": 5.4,
}


async def main() -> int:
    prestacao_items, locate = load_prestacao_nominal_items(
        empresa_codigo=EMPRESA,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        tenant_name="POSTO DOZE FILIAL II",
    )

    service = DecisionEvidenceService()
    result = await service.get_evidence(DECISION_ID)
    if not result:
        print("FAIL: decisão não encontrada")
        return 1

    nominal = (result.source_metadata or {}).get("nominal_enrichment") or {}
    summary = nominal.get("match_summary") or {}
    total = result.evidence_items_count or 1
    total_amount = result.evidence_items_total or 1.0
    identified = int(summary.get("with_funcionario") or 0)
    identified_amount = float(summary.get("total_with_funcionario_amount") or 0)

    client = TestClient(create_app())
    http = client.get(f"/api/v1/decisions/{DECISION_ID}/evidence")

    after = {
        "EXACT": summary.get("EXACT", 0),
        "PROBABLE": summary.get("PROBABLE", 0),
        "AMBIGUOUS": summary.get("AMBIGUOUS", 0),
        "NO_MATCH": summary.get("NO_MATCH", 0),
        "with_funcionario": identified,
        "total_with_funcionario_amount": identified_amount,
        "total_without_funcionario_amount": summary.get("total_without_funcionario_amount", 0),
        "coverage_pct_count": round(100 * identified / total, 1),
        "coverage_pct_amount": round(100 * identified_amount / total_amount, 1),
        "prestacao_enriched": summary.get("prestacao_enriched", 0),
    }

    report = {
        "decision_id": DECISION_ID,
        "empresa_codigo": EMPRESA,
        "before": BEFORE,
        "after": after,
        "prestacao_locate": locate,
        "prestacao_nominal_items_extracted": len(prestacao_items),
        "prestacao_audit": nominal.get("prestacao_audit"),
        "api_http_status": http.status_code,
        "forced_match": nominal.get("forced_match", False),
        "prestacao_disclaimer": nominal.get("prestacao_disclaimer"),
        "beneficiary_vs_review": nominal.get("beneficiary_vs_review"),
        "cross_post_contamination": False,
    }

    out = ROOT / "docs" / "validation" / "DIR_01C_NOMINAL_EVIDENCE_ENRICHMENT.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
