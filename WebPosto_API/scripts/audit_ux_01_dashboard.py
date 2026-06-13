#!/usr/bin/env python3
"""UX-01 — QA gate dashboard information architecture."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
APP_JS = FRONTEND / "app.js"
NAV_JS = FRONTEND / "config" / "navigation.js"
INDEX = FRONTEND / "index.html"

MOTOR_SERVICES = [
    "src/services/non_fuel_product_sales_service.py",
    "src/services/product_master_optimization_service.py",
    "src/services/commercial_execution_service.py",
    "src/services/fuel_governance_service.py",
    "src/services/nfce_intelligence_service.py",
]

REQUIRED_VIEWS = [
    "executive",
    "dashboard",
    "expenses",
    "accounts",
    "financeCenter",
    "cashFlow",
    "cashOperations",
    "benchmark",
    "executiveScorecard",
    "corporateHub",
    "executiveCopilot",
    "recommendations",
    "learning",
    "nfceIntelligence",
    "lmcIntelligence",
    "fiscalIntelligence",
    "fiscalReconciliation",
    "fuelGovernance",
    "nonFuelProducts",
    "commercialExecution",
    "commercialLearning",
    "commercialCopilot",
    "fuels",
    "sales",
    "stock",
]


def main() -> None:
    errors: list[str] = []

    if not NAV_JS.exists():
        errors.append("navigation.js ausente")
    else:
        nav_text = NAV_JS.read_text(encoding="utf-8")
        if nav_text.count('icon: "') != 6:
            errors.append("sidebar deve ter 6 macro áreas")
        if "Conveniência" in nav_text or "Conveniencia" in nav_text:
            errors.append('termo "Conveniência" encontrado')
        if "Produtos Vendidos" not in nav_text:
            errors.append("área Produtos Vendidos ausente")
        for view in REQUIRED_VIEWS:
            if f'"{view}"' not in nav_text:
                errors.append(f"view não mapeada na IA: {view}")

    if INDEX.exists():
        index_text = INDEX.read_text(encoding="utf-8")
        if 'data-view="nfceIntelligence"' in index_text:
            errors.append("motores ainda expostos como botões no index.html")
        if "sidebarNav" not in index_text:
            errors.append("sidebar UX-01 ausente no index.html")

    if APP_JS.exists():
        app_text = APP_JS.read_text(encoding="utf-8")
        if "renderCommercialCopilot" not in app_text:
            errors.append("renderCommercialCopilot ausente")
        if 'from "./pages/commercialCopilot.js"' not in app_text:
            errors.append("import renderCommercialCopilot ausente — bug IA-6")
        if "mountNavigationShell" not in app_text:
            errors.append("navigation shell não integrado")

    for rel in MOTOR_SERVICES:
        path = ROOT / rel
        if path.exists() and "navigation.js" in path.read_text(encoding="utf-8"):
            errors.append(f"motor alterado indevidamente: {rel}")

    print("UX-01 QA")
    print(f"  erros: {len(errors)}")
    for err in errors:
        print(f"  - {err}")

    if errors:
        raise SystemExit(1)

    print("[PARECER FINAL: UX-01 DASHBOARD INFORMATION ARCHITECTURE APROVADA]")


if __name__ == "__main__":
    main()
