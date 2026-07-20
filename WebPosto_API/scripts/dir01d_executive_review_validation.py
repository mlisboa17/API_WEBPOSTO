#!/usr/bin/env python3
"""DIR-01D — validação runtime ExecutiveReviewRequest."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from src.interfaces.http.app import create_app
from src.services.executive_review.service import ExecutiveReviewService
from src.services.executive_review.store import ExecutiveReviewStore

DECISION_ID = "175da101-6f68-42f4-9d2b-9b42e6cedea2"


async def main() -> int:
    store = ExecutiveReviewStore()
    store.clear_all()

    from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService

    svc = ExecutiveReviewService(DecisionEvidenceService(), store=store)
    evidence = await svc._evidence.get_evidence(DECISION_ID)
    if not evidence:
        print(json.dumps({"error": "decisão não encontrada"}, ensure_ascii=False))
        return 1

    summary = svc.pending_summary(evidence.evidence_items)
    req1, created1 = await svc.create_review_request(DECISION_ID)
    req2, created2 = await svc.create_review_request(DECISION_ID)

    client = TestClient(create_app())
    import src.interfaces.http.routes.decisions as route

    route._review_service = svc
    route._evidence_service = svc._evidence

    post1 = client.post(f"/api/v1/decisions/{DECISION_ID}/review-requests", json={})
    post2 = client.post(f"/api/v1/decisions/{DECISION_ID}/review-requests", json={})
    get_list = client.get(f"/api/v1/decisions/{DECISION_ID}/review-requests")
    get_one = client.get(f"/api/v1/review-requests/{req1.id}")

    report = {
        "decision_id": DECISION_ID,
        "evidence_items_total": summary["total_count"],
        "identified_count": summary["identified_count"],
        "identified_amount": summary["identified_amount"],
        "pending_review_count": summary["pending_count"],
        "pending_review_amount": summary["pending_amount"],
        "request_created": True,
        "request_id": req1.id,
        "status": req1.status.value,
        "review_responsible": req1.review_responsible,
        "service_second_post_duplicate": created2,
        "http_post1_status": post1.status_code,
        "http_post2_status": post2.status_code,
        "http_post2_already_exists": post2.json().get("data", {}).get("already_exists"),
        "http_get_list_status": get_list.status_code,
        "http_get_one_status": get_one.status_code,
        "idempotency_pass": created2 and post2.json().get("data", {}).get("already_exists") is True,
        "store_requests_count": len(store.list_by_decision(DECISION_ID)),
    }

    out = ROOT / "docs" / "validation" / "DIR_01D_EXECUTIVE_REVIEW_RUNTIME.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ROOT / "docs" / "validation" / "DIR_01D_EXECUTIVE_REVIEW_RUNTIME.md"
    md.write_text(
        f"""# DIR-01D — Executive Review Request (runtime)

**Decision ID:** `{DECISION_ID}`

| Métrica | Valor |
|---------|-------|
| Evidence items | {summary['total_count']} |
| Identificados | {summary['identified_count']} · R$ {summary['identified_amount']:,.2f} |
| Pendentes conferência | {summary['pending_count']} · R$ {summary['pending_amount']:,.2f} |
| Request ID | `{req1.id}` |
| Status | `{req1.status.value}` |
| review_responsible | `{req1.review_responsible}` |
| Idempotência (2º POST) | {'PASS' if report['idempotency_pass'] else 'FAIL'} |
| POST HTTP | {post1.status_code} / {post2.status_code} |
| GET HTTP | {get_list.status_code} / {get_one.status_code} |

Fronteira: **Diretoria solicita** (`ExecutiveReviewRequest`) · **Financeiro confere** (futuro).
""",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
