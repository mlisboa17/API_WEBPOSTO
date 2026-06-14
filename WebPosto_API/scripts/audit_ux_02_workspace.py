#!/usr/bin/env python3
"""UX-02 — QA gate dashboard workspace optimization."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
APP_JS = FRONTEND / "app.js"
NAV_JS = FRONTEND / "config" / "navigation.js"
INDEX = FRONTEND / "index.html"
STYLES = FRONTEND / "styles.css"
WORKSPACE_PAGE = FRONTEND / "pages" / "executiveWorkspace.js"
WORKSPACE_ENGINE = FRONTEND / "services" / "workspaceEngine.js"

MOTOR_SERVICES = [
    "src/services/non_fuel_product_sales_service.py",
    "src/services/product_master_optimization_service.py",
    "src/services/commercial_execution_service.py",
    "src/services/fuel_governance_service.py",
    "src/services/nfce_intelligence_service.py",
    "src/services/executive_scorecard_service.py",
    "src/services/action_center_service.py",
    "src/services/benchmark_service.py",
]

FORBIDDEN_BACKEND_TOUCH = [
    "src/services/",
    "src/routes/",
    "src/snapshots/",
    "src/dw/",
    "src/lineage/",
]

REPORT_FILES = [
    "WORKSPACE_AUDIT_REPORT.md",
    "DASHBOARD_REDESIGN_REPORT.md",
    "EXECUTIVE_CARDS_REPORT.md",
    "ALERT_CENTER_REPORT.md",
    "OPPORTUNITY_CENTER_REPORT.md",
    "BRANCH_INTELLIGENCE_REPORT.md",
    "RESPONSIVE_LAYOUT_REPORT.md",
    "UX_METRICS_REPORT.md",
    "UX_02_QA_REPORT.md",
    "UX_02_DASHBOARD_WORKSPACE_OPTIMIZATION_REPORT.md",
]


def count_sidebar_tabs(nav_text: str) -> int:
    return len(re.findall(r"label:\s*\"", nav_text))


def count_ws_blocks(page_text: str) -> int:
    return page_text.count('class="ws-block')


def main() -> None:
    errors: list[str] = []
    metrics: dict[str, str | int | bool] = {}

    nav_text = NAV_JS.read_text(encoding="utf-8") if NAV_JS.exists() else ""
    app_text = APP_JS.read_text(encoding="utf-8") if APP_JS.exists() else ""
    index_text = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
    styles_text = STYLES.read_text(encoding="utf-8") if STYLES.exists() else ""
    page_text = WORKSPACE_PAGE.read_text(encoding="utf-8") if WORKSPACE_PAGE.exists() else ""
    engine_text = WORKSPACE_ENGINE.read_text(encoding="utf-8") if WORKSPACE_ENGINE.exists() else ""

    sidebar_tabs = count_sidebar_tabs(nav_text)
    metrics["sidebar_tabs"] = sidebar_tabs
    metrics["widgets_before"] = 33
    metrics["widgets_now"] = 6 + count_ws_blocks(page_text)
    metrics["buttons_removed"] = max(0, 33 - sidebar_tabs)

    if 'view: "executiveWorkspace"' not in nav_text:
        errors.append("aba Resumo deve apontar para executiveWorkspace")
    if "executiveWorkspaceView" not in index_text:
        errors.append("seção executiveWorkspaceView ausente no index.html")
    if "renderExecutiveWorkspace" not in app_text:
        errors.append("renderExecutiveWorkspace não integrado em app.js")
    if "loadExecutiveWorkspaceBundle" not in app_text:
        errors.append("loadExecutiveWorkspaceBundle ausente em app.js")
    if "buildExecutiveWorkspace" not in engine_text:
        errors.append("workspaceEngine ausente")
    if ".ws-summary-grid" not in styles_text:
        errors.append("estilos UX-02 (.ws-*) ausentes")
    if "Conveniência" in nav_text or "Conveniencia" in nav_text:
        errors.append('termo "Conveniência" encontrado')
    if "Produtos Vendidos" not in nav_text:
        errors.append("área Produtos Vendidos ausente")
    if 'data-view="nfceIntelligence"' in index_text:
        errors.append("motores ainda expostos como botões no index.html")

    alert_origins = ["Fiscal", "Combustível", "Comercial", "Financeiro"]
    for origin in alert_origins:
        if origin not in engine_text:
            errors.append(f"Alert Center sem origem {origin}")

    for severity in ["CRÍTICO", "ALTO", "MÉDIO", "BAIXO"]:
        if severity not in engine_text:
            errors.append(f"Alert Center sem severidade {severity}")

    branch_keys = ["top", "risk", "semLmc", "bestMix", "fuelDependency"]
    for key in branch_keys:
        if key not in engine_text:
            errors.append(f"Branch Intelligence incompleta: {key}")

    metrics["centralized_alerts"] = engine_text.count("alerts.push")
    metrics["centralized_opportunities"] = engine_text.count("opportunities.push")
    metrics["home_executiva"] = "Home Executiva" in page_text
    metrics["alert_center"] = "Alert Center" in page_text
    metrics["opportunity_center"] = "Opportunity Center" in page_text
    metrics["branch_intelligence"] = "Branch Intelligence" in page_text
    metrics["branch_ranking"] = "Top filiais" in page_text
    metrics["responsive_layout"] = ".ws-grid-2" in styles_text and "@media" in styles_text
    metrics["motors_preserved"] = all(
        f'"{view}"' in nav_text
        for view in [
            "commercialCopilot",
            "commercialExecution",
            "fuelGovernance",
            "nfceIntelligence",
            "nonFuelProducts",
        ]
    )
    metrics["produtos_vendidos"] = "Produtos Vendidos" in nav_text and engine_text.count("Produtos Vendidos") >= 1
    metrics["conveniencia_proibido"] = "Conveniência" not in nav_text and "Conveniencia" not in nav_text

    for rel in MOTOR_SERVICES:
        path = ROOT / rel
        if path.exists():
            body = path.read_text(encoding="utf-8")
            if "executiveWorkspace" in body or "workspaceEngine" in body:
                errors.append(f"motor alterado indevidamente: {rel}")

    for report in REPORT_FILES:
        if not (ROOT / report).exists():
            errors.append(f"relatório ausente: {report}")

    print("UX-02 QA")
    print(f"  erros: {len(errors)}")
    for err in errors:
        print(f"  - {err}")

    if errors:
        raise SystemExit(1)

    print("[PARECER FINAL: UX-02 DASHBOARD WORKSPACE OPTIMIZATION APROVADA]")


if __name__ == "__main__":
    main()
