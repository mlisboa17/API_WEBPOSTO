#!/usr/bin/env python3
"""F08.3 — QA gate Financial Operations Center."""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:8050"
PERIOD = ("2026-06-01", "2026-06-07")

REQUIRED_FILES = [
    "src/services/financial_operations_center_service.py",
    "src/interfaces/http/routes/financial_operations_center.py",
    "frontend/pages/financialOperationsCenter.js",
    "dw/ddl/fact_financial_operations_center.sql",
    "tests/unit/test_financial_operations_center_service.py",
]

F08_PRIOR = [
    "src/services/financial_resilience_service.py",
    "src/services/financial_snapshot_health_service.py",
    "src/services/financial_snapshot_scheduler.py",
    "src/services/financial_auto_recovery_service.py",
    "src/services/financial_operations_service.py",
]

READ_ONLY_ENDPOINTS = [
    "/api/v1/financial/operations-center/summary",
    "/api/v1/financial/operations-center/status",
    "/api/v1/financial/operations-center/alerts",
    "/api/v1/financial/operations-center/executions",
    "/api/v1/financial/operations-center/cockpit",
    "/api/v1/financial/operations-center/timeline",
]


def fetch_json_http(path: str) -> dict | None:
    try:
        qs = f"?dataInicial={PERIOD[0]}&dataFinal={PERIOD[1]}"
        req = urllib.request.Request(f"{BASE}{path}{qs}", method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def fetch_json_testclient(path: str) -> dict | None:
    try:
        from fastapi.testclient import TestClient

        from src.interfaces.http.app import app

        client = TestClient(app)
        qs = f"?dataInicial={PERIOD[0]}&dataFinal={PERIOD[1]}"
        response = client.get(f"{path}{qs}")
        if response.status_code != 200:
            return None
        return response.json()
    except Exception:
        return None


def fetch_json(path: str) -> dict | None:
    payload = fetch_json_http(path)
    if payload and payload.get("success"):
        return payload
    return fetch_json_testclient(path)


def run_pytest() -> tuple[bool, str]:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_financial_operations_center_service.py",
            "tests/unit/test_financial_auto_recovery_service.py",
            "-q",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


def run_service_unit() -> dict:
    from src.services.financial_operations_center_service import get_operations_center_service

    svc = get_operations_center_service()
    summary = svc.get_operations_summary(PERIOD[0], PERIOD[1])
    status = svc.get_operational_status(PERIOD[0], PERIOD[1])
    alerts = svc.get_operational_alerts(PERIOD[0], PERIOD[1])
    timeline = svc.get_timeline(PERIOD[0], PERIOD[1])
    dw = svc.dw_row(PERIOD[0], PERIOD[1])
    return {"summary": summary, "status": status, "alerts": alerts, "timeline": timeline, "dw": dw}


def main() -> None:
    errors: list[str] = []

    for rel in REQUIRED_FILES + F08_PRIOR:
        if not (ROOT / rel).exists():
            errors.append(f"arquivo ausente: {rel}")

    svc_src = (ROOT / "src/services/financial_operations_center_service.py").read_text(encoding="utf-8")
    for fn in ("get_operations_summary", "get_operational_status", "get_operational_alerts"):
        if fn not in svc_src:
            errors.append(f"service sem {fn}()")

    if "30%" not in svc_src and "0.30" not in svc_src:
        errors.append("health score sem peso snapshot 30%")

    route_src = (ROOT / "src/interfaces/http/routes/financial_operations_center.py").read_text(encoding="utf-8")
    if "@router.post" in route_src:
        errors.append("API F08.3 deve ser somente leitura")

    app_src = (ROOT / "src/interfaces/http/app.py").read_text(encoding="utf-8")
    if "financial_operations_center" not in app_src:
        errors.append("app.py sem router operations-center")

    nav_src = (ROOT / "frontend/config/navigation.js").read_text(encoding="utf-8")
    if "financialOperationsCenter" not in nav_src:
        errors.append("navigation.js sem Operations Center")

    app_js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    if "financial-operations-center" not in app_js:
        errors.append("app.js sem alias financial-operations-center")

    ddl = (ROOT / "dw/ddl/fact_financial_operations_center.sql").read_text(encoding="utf-8")
    for col in (
        "execution_id",
        "generated_at",
        "health_score",
        "scheduler_status",
        "recovery_status",
        "alert_count",
        "critical_alerts",
        "snapshot_count",
        "empresa_codigo",
        "lineage",
    ):
        if col not in ddl:
            errors.append(f"DW sem coluna {col}")

    ok_pytest, pytest_out = run_pytest()
    if not ok_pytest:
        errors.append(f"pytest falhou:\n{pytest_out}")

    try:
        unit = run_service_unit()
    except Exception as exc:
        errors.append(f"service unit falhou: {exc}")
        unit = {}

    if unit:
        summary = unit["summary"]
        if not summary.get("snapshotFirst"):
            errors.append("summary sem snapshotFirst")
        health = summary.get("executiveHealthScore") or {}
        if health.get("score") is None:
            errors.append("health score ausente")
        if health.get("classification") not in {"EXCELENTE", "BOM", "ATENÇÃO", "CRÍTICO"}:
            errors.append("classificação health inválida")
        if not unit["timeline"].get("events"):
            errors.append("timeline vazia (esperado ao menos circuit event)")

        dw = unit["dw"]
        if dw.get("lineage") is not True:
            errors.append("DW row sem lineage=true")

    http_ok = 0
    for path in READ_ONLY_ENDPOINTS:
        payload = fetch_json(path)
        if payload and payload.get("success"):
            http_ok += 1
        else:
            errors.append(f"endpoint falhou: {path}")

    report = {
        "feature": "F08.3",
        "approved": len(errors) == 0,
        "errors": errors,
        "http_endpoints_ok": http_ok,
        "period": PERIOD,
    }

    out_path = ROOT / "scripts/f08_3_financial_operations_center.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = ROOT / "F08_3_FINANCIAL_OPERATIONS_CENTER_REPORT.md"
    error_lines = [f"- {e}" for e in errors] if errors else ["- Nenhum"]
    md_path.write_text(
        "\n".join(
            [
                "# F08.3 — Financial Operations Center QA",
                "",
                f"- Aprovado: **{'SIM' if report['approved'] else 'NÃO'}**",
                f"- Endpoints HTTP OK: {http_ok}/{len(READ_ONLY_ENDPOINTS)}",
                "",
                "## Erros",
                *error_lines,
                "",
                "[PARECER FINAL: F08.3 FINANCIAL OPERATIONS CENTER]",
            ]
        ),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(0 if report["approved"] else 1)


if __name__ == "__main__":
    main()
