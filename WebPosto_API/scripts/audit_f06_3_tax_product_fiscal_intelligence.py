#!/usr/bin/env python3
"""F06.3 — Tax & Product Fiscal Intelligence audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.tax_product_fiscal_intelligence_service import TaxProductFiscalIntelligenceService
from src.services.tax_product_fiscal_intelligence_snapshot_service import TaxProductFiscalIntelligenceSnapshotService

WINDOWS = {"7d": ("2026-06-01", "2026-06-07")}


async def audit_window(svc, snap, label, di, df) -> dict:
    t0 = time.perf_counter()
    resp = await svc.build(di, df, None)
    build_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not resp.success or not resp.data:
        return {"window": label, "error": str(resp.error), "buildMs": build_ms}
    data = resp.data
    await snap.collect(di, df, None, data)
    ex = data.get("executiveAnswers") or {}
    qa = data.get("qa") or {}
    return {
        "window": label,
        "buildMs": build_ms,
        "executiveAnswers": ex,
        "qa": qa,
        "parecerFinal": data.get("parecerFinal"),
        "cockpit": data.get("cockpit"),
        "productFiscalCatalogEngine": data.get("productFiscalCatalogEngine"),
        "ncmIntelligenceEngine": data.get("ncmIntelligenceEngine"),
        "taxClassificationEngine": data.get("taxClassificationEngine"),
        "financialClassificationEngine": data.get("financialClassificationEngine"),
        "fiscalRiskEngine": data.get("fiscalRiskEngine"),
        "executiveFiscalIntelligence": data.get("executiveFiscalIntelligence"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = TaxProductFiscalIntelligenceService()
    snap = TaxProductFiscalIntelligenceSnapshotService(svc)
    results = {"sprint": "F06.3", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"F06.3 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        ex = w.get("executiveAnswers") or {}
        print(
            f"  done produtos={ex.get('1_totalProdutos')} tributacao={ex.get('4_coberturaTributaria')} "
            f"parecer={w.get('parecerFinal')}",
            flush=True,
        )

    ref = results["windows"]["7d"]
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qa") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "fonteWebPostoLive": False,
        "semCrossTenant": bool(qa.get("semCrossTenant")),
        "semNcmInventado": bool(qa.get("semNcmInventado")),
        "semClassificacaoInventada": bool(qa.get("semClassificacaoInventada")),
        "semProdutoSemLineage": bool(qa.get("semProdutoSemLineage")),
        "semCalculoFiscalSemOrigem": bool(qa.get("semCalculoFiscalSemOrigem")),
        "motorAuditavel": bool(qa.get("motorAuditavel")),
        "lineageCompleto": bool(qa.get("lineageCompleto")),
        "fiscalIntelligenceMadura": bool(ex.get("19_fiscalIntelligenceMadura")),
        "aprovadoF064": bool(ex.get("20_aprovadoF064")),
    }

    out = ROOT / "scripts" / "f06_3_tax_product_fiscal_intelligence.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
