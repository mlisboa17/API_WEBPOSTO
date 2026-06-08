#!/usr/bin/env python3
"""Validação F01.4-A — V2 vs V3 + métricas OUTROS."""
from __future__ import annotations

import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import load_core_config
from src.services.logos_expense_classifier_v2 import classify_logos_expense_v2, map_v2_to_legacy
from src.services.logos_expense_classifier_v3 import classify_logos_expense_v3

PERIOD = {"dataInicial": "2026-06-01", "dataFinal": "2026-06-07"}
OUT = ROOT / "scripts" / "f01_4a_validation_results.json"


async def main() -> int:
    import httpx

    cfg = load_core_config()
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{cfg.webposto_base_url}/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
            params={**PERIOD, "CHAVE": cfg.webposto_api_key},
            timeout=120,
        )
        rows = r.json() if r.status_code == 200 else []
        if isinstance(rows, dict):
            rows = rows.get("resultados") or rows.get("data") or []

    total = Decimal("0")
    v2_outros = Decimal("0")
    v3_outros = Decimal("0")
    sources: dict[str, int] = {}
    max_conf = 0.0

    for row in rows:
        val = Decimal(str(row.get("valor") or 0))
        total += val
        desc = str(row.get("descricaoDocumento") or "")
        v2 = map_v2_to_legacy(classify_logos_expense_v2(desc).categoria_v2)
        v3r = classify_logos_expense_v3(desc, plano_conta_gerencial_codigo=row.get("planoContaGerencialCodigo"))
        if v2 == "OUTROS":
            v2_outros += val
        if v3r.categoria_v3 == "OUTROS":
            v3_outros += val
        sources[v3r.classification_source] = sources.get(v3r.classification_source, 0) + 1
        max_conf = max(max_conf, v3r.confidence_score)

    result = {
        "period": PERIOD,
        "totalRegistros": len(rows),
        "outrosV2Percent": round(float(v2_outros / total * 100), 2) if total else 0,
        "outrosV3Percent": round(float(v3_outros / total * 100), 2) if total else 0,
        "reductionPctPoints": round(float((v2_outros - v3_outros) / total * 100), 2) if total else 0,
        "classificationSources": sources,
        "maxConfidenceScore": max_conf,
        "confidenceValid": max_conf <= 1.0,
        "pass": max_conf <= 1.0 and float(v3_outros) <= float(v2_outros),
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
