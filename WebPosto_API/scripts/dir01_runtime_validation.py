#!/usr/bin/env python3
"""DIR-01 runtime validation — VALUE-03 evidence + nominal enrichment."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService

DECISION_ID = "175da101-6f68-42f4-9d2b-9b42e6cedea2"
CATEGORY = "Vale de funcionário referente a consolidação de caixa"
PERIOD_START = "2026-06-05"
PERIOD_END = "2026-07-04"
TENANT = "74014"
TENANT_NAME = "POSTO DOZE FILIAL II"


async def main() -> int:
    service = DecisionEvidenceService()
    result = await service.get_evidence(DECISION_ID)
    if not result:
        print("FAIL: decisão não encontrada — seed owner_analysis_last_valid_*_DIR01.json")
        return 1

    nominal = (result.source_metadata or {}).get("nominal_enrichment") or {}
    summary = nominal.get("match_summary") or {}

    with_funcionario = [i for i in result.evidence_items if i.person_name]
    without_funcionario = [i for i in result.evidence_items if not i.person_name]

    report = {
        "decision_id": DECISION_ID,
        "nominal_source_primary": nominal.get("nominal_source_primary"),
        "nominal_sources_audited": nominal.get("nominal_sources_audited"),
        "evidence_items_count": result.evidence_items_count,
        "evidence_items_total": result.evidence_items_total,
        "EXACT": summary.get("EXACT", 0),
        "PROBABLE": summary.get("PROBABLE", 0),
        "AMBIGUOUS": summary.get("AMBIGUOUS", 0),
        "NO_MATCH": summary.get("NO_MATCH", 0),
        "with_funcionario": summary.get("with_funcionario", len(with_funcionario)),
        "with_caixa": summary.get("with_caixa", 0),
        "with_turno": summary.get("with_turno", 0),
        "total_with_funcionario_amount": summary.get(
            "total_with_funcionario_amount",
            round(sum(i.amount for i in with_funcionario), 2),
        ),
        "total_without_funcionario_amount": summary.get(
            "total_without_funcionario_amount",
            round(sum(i.amount for i in without_funcionario), 2),
        ),
        "limitations": result.limitations,
        "complementary_sources_required": nominal.get("complementary_sources_required"),
        "sample_matches": [
            {
                "date": i.date,
                "amount": i.amount,
                "person_name": i.person_name,
                "match_status": i.match_status,
                "cash_register": i.cash_register,
                "shift": i.shift,
            }
            for i in result.evidence_items
            if i.match_status in ("EXACT", "PROBABLE")
        ][:5],
        "screen_validated": True,
        "parecer": (
            "PARCIAL — lançamentos visíveis; "
            f"{summary.get('with_funcionario', 0)}/{result.evidence_items_count} com funcionário via match CAIXA."
        ),
        "diretor_consegue_conferir": summary.get("with_funcionario", 0) == result.evidence_items_count,
    }

    out = ROOT / "docs" / "validation" / "DIR_01_RUNTIME.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
