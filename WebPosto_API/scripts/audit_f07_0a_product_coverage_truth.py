#!/usr/bin/env python3
"""F07.0A — Product Coverage Truth Audit (READ ONLY)."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from src.services.product_coverage_truth_audit_service import ProductCoverageTruthAuditService

WINDOWS = {"7d": ("2026-06-01", "2026-06-07")}


async def audit_window(svc: ProductCoverageTruthAuditService, label: str, di: str, df: str) -> dict:
    t0 = time.perf_counter()
    resp = await svc.build(di, df)
    build_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not resp.success or not resp.data:
        return {"window": label, "error": str(resp.error), "buildMs": build_ms}
    data = resp.data
    return {
        "window": label,
        "buildMs": build_ms,
        "fonteDados": data.get("fonteDados"),
        "liveFetch": data.get("liveFetch"),
        "executiveAnswers": data.get("executiveAnswers"),
        "productCatalogAudit": data.get("productCatalogAudit"),
        "categoryDiscovery": data.get("categoryDiscovery"),
        "productCoverageAudit": data.get("productCoverageAudit"),
        "missingProductDetection": data.get("missingProductDetection"),
        "revenueCoverageAudit": data.get("revenueCoverageAudit"),
        "storeSalesDiscovery": data.get("storeSalesDiscovery"),
        "executiveChallenge": data.get("executiveChallenge"),
        "dwCoverage": data.get("dwCoverage"),
        "qa": data.get("qa"),
        "parecerFinal": data.get("parecerFinal"),
    }


async def main() -> None:
    svc = ProductCoverageTruthAuditService()
    results = {"sprint": "F07.0A", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"F07.0A audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, label, di, df)
    ref = results["windows"]["7d"]
    results["executiveAnswers"] = ref.get("executiveAnswers")
    results["parecerFinal"] = ref.get("parecerFinal")
    out = ROOT / "scripts" / "f07_0a_product_coverage_truth_audit.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    ex = ref.get("executiveAnswers") or {}
    rev = ref.get("revenueCoverageAudit") or {}
    ch = ref.get("executiveChallenge") or {}
    print(f"  fonte={ref.get('fonteDados')} buildMs={ref.get('buildMs')}")
    print(f"  receita NF live: R$ {ex.get('4_receitaNaoCombustivelLive')}")
    print(f"  receita NF F07.0: R$ {ex.get('5_receitaNaoCombustivelF070')}")
    print(f"  gap: R$ {ex.get('6_gapReceita')}")
    print(f"  veredito receita: {rev.get('veredito')}")
    print(f"  challenge: {ch.get('veredito')}")
    print(f"  parecer: {ref.get('parecerFinal')}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
