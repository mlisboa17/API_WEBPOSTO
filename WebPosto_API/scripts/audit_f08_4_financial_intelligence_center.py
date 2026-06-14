#!/usr/bin/env python3
"""F08.4 — QA gate Financial Intelligence Center."""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PERIOD = ("2026-06-01", "2026-06-07")
BASE = "http://127.0.0.1:8050"

REQUIRED_FILES = [
    "src/services/financial_trend_intelligence_service.py",
    "src/services/financial_risk_intelligence_service.py",
    "src/services/financial_opportunity_service.py",
    "src/services/cash_flow_intelligence_service.py",
    "src/services/financial_commitments_intelligence.py",
    "src/services/financial_intelligence_center_service.py",
    "src/interfaces/http/routes/financial_intelligence_center.py",
    "frontend/pages/financialIntelligence.js",
    "dw/ddl/fact_financial_intelligence.sql",
    "tests/unit/test_financial_intelligence_center.py",
]

F08_PRIOR = [
    "src/services/financial_operations_center_service.py",
    "src/services/financial_resilience_service.py",
    "src/services/financial_snapshot_health_service.py",
]

ENDPOINTS = [
    "/api/v1/financial/intelligence-center/cockpit",
    "/api/v1/financial/intelligence-center/trends",
    "/api/v1/financial/intelligence-center/risks",
    "/api/v1/financial/intelligence-center/opportunities",
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
            "tests/unit/test_financial_intelligence_center.py",
            "tests/unit/test_financial_operations_center_service.py",
            "-q",
            "--no-cov",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


def main() -> None:
    errors: list[str] = []

    for rel in REQUIRED_FILES + F08_PRIOR:
        if not (ROOT / rel).exists():
            errors.append(f"arquivo ausente: {rel}")

    center_src = (ROOT / "src/services/financial_intelligence_center_service.py").read_text(encoding="utf-8")
    if "generativeAi" not in center_src or "0.25" not in center_src:
        errors.append("executive score ou flag generativeAi ausente")

    route_src = (ROOT / "src/interfaces/http/routes/financial_intelligence_center.py").read_text(encoding="utf-8")
    if "@router.post" in route_src:
        errors.append("API deve ser somente leitura")

    app_src = (ROOT / "src/interfaces/http/app.py").read_text(encoding="utf-8")
    if "financial_intelligence_center" not in app_src:
        errors.append("app.py sem router intelligence-center")

    nav = (ROOT / "frontend/config/navigation.js").read_text(encoding="utf-8")
    if "financialIntelligence" not in nav:
        errors.append("navigation.js sem financialIntelligence")

    ddl = (ROOT / "dw/ddl/fact_financial_intelligence.sql").read_text(encoding="utf-8")
    for col in ("generated_at", "financial_score", "risk_level", "trend", "opportunity_count", "cash_flow_health", "lineage"):
        if col not in ddl:
            errors.append(f"DW sem coluna {col}")

    ok, pytest_out = run_pytest()
    if not ok:
        errors.append(f"pytest falhou:\n{pytest_out}")

    from src.services.financial_intelligence_center_service import get_financial_intelligence_center

    cockpit = get_financial_intelligence_center().get_cockpit(PERIOD[0], PERIOD[1])
    if not cockpit.get("snapshotFirst"):
        errors.append("cockpit sem snapshotFirst")
    if cockpit.get("generativeAi"):
        errors.append("generativeAi deve ser False")
    if cockpit["cashFlow"].get("forecast") is not None:
        errors.append("forecast inventado detectado")
    if len(cockpit.get("executiveCards") or []) > 6:
        errors.append("mais de 6 cards executivos")

    for risk in cockpit["risks"]["risks"]:
        if "lineage" not in risk:
            errors.append("risco sem lineage")

    for opp in cockpit["opportunities"]["opportunities"]:
        for field in ("impacto_estimado", "evidencia", "origem"):
            if field not in opp:
                errors.append(f"oportunidade sem {field}")

    http_ok = 0
    for path in ENDPOINTS:
        payload = fetch_json(path)
        if payload and payload.get("success"):
            http_ok += 1
        else:
            errors.append(f"endpoint falhou: {path}")

    report = {
        "feature": "F08.4",
        "approved": len(errors) == 0,
        "errors": errors,
        "http_endpoints_ok": http_ok,
        "period": PERIOD,
    }

    (ROOT / "scripts/f08_4_financial_intelligence_center.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    error_lines = [f"- {e}" for e in errors] if errors else ["- Nenhum"]
    (ROOT / "F08_4_FINANCIAL_INTELLIGENCE_CENTER_REPORT.md").write_text(
        "\n".join(
            [
                "# F08.4 — Financial Intelligence Center QA",
                "",
                f"- Aprovado: **{'SIM' if report['approved'] else 'NÃO'}**",
                f"- Endpoints OK: {http_ok}/{len(ENDPOINTS)}",
                "",
                "## Erros",
                *error_lines,
                "",
                "[PARECER FINAL: F08.4 FINANCIAL INTELLIGENCE CENTER]",
            ]
        ),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(0 if report["approved"] else 1)


if __name__ == "__main__":
    main()
