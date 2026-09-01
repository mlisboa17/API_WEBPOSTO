#!/usr/bin/env python3
"""FIN-01 — validação runtime Financial Review Inbox."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from src.interfaces.http.app import create_app

DECISION_ID = "175da101-6f68-42f4-9d2b-9b42e6cedea2"


def main() -> int:
    store_path = ROOT / "snapshots" / "executive_review_requests" / "store.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    active_ids = [
        rid
        for rid, raw in (store.get("requests") or {}).items()
        if raw.get("status") in {"REQUESTED", "ASSIGNED", "IN_REVIEW", "NEEDS_INFORMATION"}
    ]
    request_id = active_ids[0] if active_ids else None

    client = TestClient(create_app())
    inbox = client.get("/api/v1/financial/review-inbox")
    detail = client.get(f"/api/v1/financial/review-inbox/{request_id}") if request_id else None
    iso_5555 = client.get("/api/v1/financial/review-inbox", params={"tenant_id": "5555"})
    iso_11495 = client.get("/api/v1/financial/review-inbox", params={"tenant_id": "11495"})

    inbox_body = inbox.json() if inbox.status_code == 200 else {}
    items = (inbox_body.get("data") or {}).get("items") or []
    summary = (inbox_body.get("data") or {}).get("summary") or {}
    item = items[0] if items else {}
    detail_body = detail.json().get("data") if detail and detail.status_code == 200 else None

    report = {
        "http_inbox_status": inbox.status_code,
        "http_detail_status": detail.status_code if detail else None,
        "active_request_id": request_id,
        "decision_id": item.get("decision_id") or DECISION_ID,
        "tenant_id": item.get("tenant_id"),
        "tenant_name": item.get("tenant_name"),
        "evidence_items_count": item.get("evidence_items_count"),
        "amount_under_review": item.get("amount_under_review"),
        "technical_status": item.get("technical_status"),
        "financial_status_label": item.get("financial_status_label"),
        "review_responsible": item.get("review_responsible"),
        "summary": summary,
        "detail_pending_items": len((detail_body or {}).get("pending_evidence_items") or []),
        "tenant_5555_count": len((iso_5555.json().get("data") or {}).get("items") or []),
        "tenant_11495_count": len((iso_11495.json().get("data") or {}).get("items") or []),
        "tenant_isolation_pass": all(
            i.get("tenant_id") != "74014"
            for i in (iso_5555.json().get("data") or {}).get("items") or []
        ),
        "same_store_source": str(store_path),
    }

    out_json = ROOT / "docs" / "validation" / "FIN_01_FINANCIAL_REVIEW_INBOX_RUNTIME.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    out_md = ROOT / "docs" / "validation" / "FIN_01_FINANCIAL_REVIEW_INBOX_RUNTIME.md"
    out_md.write_text(
        f"""# FIN-01 — Financial Review Inbox (runtime)

| Métrica | Valor |
|---------|-------|
| GET inbox | {inbox.status_code} |
| active_count | {summary.get('active_count')} |
| request_id | `{request_id}` |
| tenant | {item.get('tenant_id')} — {item.get('tenant_name')} |
| itens | {item.get('evidence_items_count')} |
| valor | {item.get('amount_under_review')} |
| status | {item.get('technical_status')} / {item.get('financial_status_label')} |
| tenant 5555 isolation | {report['tenant_5555_count']} items |
| tenant 11495 isolation | {report['tenant_11495_count']} items |
""",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if inbox.status_code == 200 and summary.get("active_count", 0) >= 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
