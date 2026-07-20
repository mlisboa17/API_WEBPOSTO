#!/usr/bin/env python3
"""FIN-02 — validação runtime Financial Review Assignment."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
from fastapi.testclient import TestClient

from src.interfaces.http.app import create_app

REQUEST_ID = "d7ff3eae-b846-4bbb-8e7b-1b49841afbf1"
DECISION_ID = "175da101-6f68-42f4-9d2b-9b42e6cedea2"
RESPONSIBLE = "Marcio de Lima"


def _detail_seconds(client: TestClient, request_id: str) -> tuple[float, int]:
    t0 = time.perf_counter()
    resp = client.get(f"/api/v1/financial/review-inbox/{request_id}")
    elapsed = round(time.perf_counter() - t0, 2)
    pending = 0
    if resp.status_code == 200:
        pending = len(resp.json().get("data", {}).get("pending_evidence_items") or [])
    return elapsed, pending


def main() -> int:
    store_path = ROOT / "snapshots" / "executive_review_requests" / "store.json"
    before = json.loads(store_path.read_text(encoding="utf-8"))
    before_req = (before.get("requests") or {}).get(REQUEST_ID) or {}

    client = TestClient(create_app())
    detail_before_s, _ = _detail_seconds(client, REQUEST_ID)

    assign = client.post(
        f"/api/v1/financial/review-inbox/{REQUEST_ID}/assign",
        json={"responsible_name": RESPONSIBLE},
    )
    detail_after_s, detail_pending = _detail_seconds(client, REQUEST_ID)

    inbox = client.get("/api/v1/financial/review-inbox")
    detail = client.get(f"/api/v1/financial/review-inbox/{REQUEST_ID}")
    follow = client.get("/api/v1/executive/follow-ups")
    follow_detail = client.get(f"/api/v1/executive/follow-ups/{REQUEST_ID}")

    assign_body = assign.json() if assign.status_code in {200, 409} else {}
    assign_data = assign_body.get("data") or {}
    inbox_item = ((inbox.json().get("data") or {}).get("items") or [{}])[0]
    detail_data = detail.json().get("data") or {}
    follow_item = next(
        (i for i in (follow.json().get("data") or {}).get("items") or [] if i.get("request_id") == REQUEST_ID),
        {},
    )
    follow_detail_data = follow_detail.json().get("data") or {}

    after = json.loads(store_path.read_text(encoding="utf-8"))
    after_req = (after.get("requests") or {}).get(REQUEST_ID) or {}

    result = {
        "request_id": REQUEST_ID,
        "decision_id": DECISION_ID,
        "status_before": before_req.get("status"),
        "responsible_before": before_req.get("review_responsible"),
        "http_assign_status": assign.status_code,
        "assign_idempotent": assign_data.get("idempotent"),
        "status_after": after_req.get("status"),
        "responsible_after": after_req.get("review_responsible"),
        "assigned_at": after_req.get("assigned_at"),
        "financial_status_label": detail_data.get("financial_status_label"),
        "executive_status_label": follow_item.get("status_label"),
        "follow_up_responsible": follow_item.get("review_responsible"),
        "follow_up_detail_responsible": follow_detail_data.get("review_responsible"),
        "evidence_items_count": detail_data.get("evidence_items_count"),
        "amount_under_review": detail_data.get("amount_under_review"),
        "detail_pending_items": detail_pending,
        "tenant_id": after_req.get("tenant_id"),
        "same_store_source": str(store_path),
        "detail_seconds_before_assign": detail_before_s,
        "detail_seconds_after_assign": detail_after_s,
        "detail_fast_path": detail_after_s < 10,
        "pass": (
            assign.status_code in {200, 409}
            and after_req.get("status") == "ASSIGNED"
            and after_req.get("review_responsible") == RESPONSIBLE
            and after_req.get("decision_id") == DECISION_ID
            and after_req.get("tenant_id") == "74014"
            and detail_data.get("amount_under_review") == 7951.0
            and detail_data.get("evidence_items_count") == 13
            and detail_pending == 13
            and follow_item.get("review_responsible") == RESPONSIBLE
        ),
    }

    out_json = ROOT / "docs" / "validation" / "FIN_02_FINANCIAL_REVIEW_ASSIGNMENT_RUNTIME.json"
    out_md = ROOT / "docs" / "validation" / "FIN_02_FINANCIAL_REVIEW_ASSIGNMENT_RUNTIME.md"
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(
        "\n".join(
            [
                "# FIN-02 — Financial Review Assignment (runtime)",
                "",
                f"| Campo | Valor |",
                f"|-------|-------|",
                f"| POST assign | {assign.status_code} |",
                f"| status antes | {result['status_before']} |",
                f"| status depois | {result['status_after']} |",
                f"| responsável | {result['responsible_after']} |",
                f"| assigned_at | {result['assigned_at']} |",
                f"| Financeiro label | {result['financial_status_label']} |",
                f"| Diretoria label | {result['executive_status_label']} |",
                f"| detail pending | {result['detail_pending_items']} |",
                f"| detail antes (s) | {result['detail_seconds_before_assign']} |",
                f"| detail depois (s) | {result['detail_seconds_after_assign']} |",
                f"| PASS | {result['pass']} |",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
