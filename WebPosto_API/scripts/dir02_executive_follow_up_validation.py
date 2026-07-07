#!/usr/bin/env python3
"""DIR-02 — validação runtime Executive Follow-Up."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from src.interfaces.http.app import create_app

REQUEST_ID = "276f5e58-c568-4a2b-99ef-d73d9fbaf7b7"
DECISION_ID = "175da101-6f68-42f4-9d2b-9b42e6cedea2"


def main() -> int:
    client = TestClient(create_app())
    resp = client.get("/api/v1/executive/follow-ups")
    if resp.status_code != 200:
        print(json.dumps({"error": resp.text}, ensure_ascii=False))
        return 1

    data = resp.json()["data"]
    summary = data.get("summary") or {}
    items = data.get("items") or []
    item = next((i for i in items if i.get("request_id") == REQUEST_ID), items[0] if items else {})

    tenant_filter = client.get("/api/v1/executive/follow-ups", params={"tenant_id": "5555"})
    tenant_items = tenant_filter.json().get("data", {}).get("items") or []

    report = {
        "http_status": resp.status_code,
        "summary": summary,
        "runtime_item": item,
        "tenant_5555_count": len(tenant_items),
        "tenant_isolation_pass": all(i.get("tenant_id") != "74014" for i in tenant_items),
        "detail_http_status": client.get(f"/api/v1/executive/follow-ups/{item.get('request_id')}").status_code
        if item.get("request_id")
        else None,
    }

    out_json = ROOT / "docs" / "validation" / "DIR_02_EXECUTIVE_FOLLOW_UP_RUNTIME.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ROOT / "docs" / "validation" / "DIR_02_EXECUTIVE_FOLLOW_UP_RUNTIME.md"
    md.write_text(
        f"""# DIR-02 — Executive Follow-Up (runtime)

| Métrica | Valor |
|---------|-------|
| HTTP GET follow-ups | {resp.status_code} |
| active_count | {summary.get('active_count')} |
| total_amount_in_review | {summary.get('total_amount_in_review')} |
| awaiting_assignment_count | {summary.get('awaiting_assignment_count')} |
| request_id | `{item.get('request_id')}` |
| decision_id | `{item.get('decision_id')}` |
| tenant_name | {item.get('tenant_name')} |
| status | {item.get('status')} |
| status_label | {item.get('status_label')} |
| tenant filter 5555 isolation | {'PASS' if report['tenant_isolation_pass'] else 'FAIL'} |
""",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
