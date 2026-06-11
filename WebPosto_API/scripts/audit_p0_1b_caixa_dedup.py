#!/usr/bin/env python3
"""P0.1-B — auditoria raw caixa/apresentado para dedup."""
from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from src.core.config import load_core_config
from src.gateway.webposto_client import WebPostoClient
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService

EMPRESA = 5555
DATA = "2026-06-08"
SOURCES = {
    "CAIXA_APRESENTADO": "caixa_apresentado",
    "CAIXA_APRESENTADO_REDE": "caixa_apresentado_rede",
    "CAIXA_REDE": "caixa_rede",
    "CAIXA": "caixa",
}


def _shift_date(row: dict) -> str:
    return str(row.get("dataMovimento") or row.get("fechamento") or row.get("abertura") or "")[:10]


def _norm_row(row: dict, origem: str) -> dict:
    apur = row.get("despesaApurado")
    apres = row.get("despesaApresentado")
    diff = row.get("despesaDiferenca")
    return {
        "empresaCodigo": row.get("empresaCodigo"),
        "dataMovimento": _shift_date(row),
        "caixaCodigo": row.get("caixaCodigo"),
        "turnoCodigo": row.get("turnoCodigo"),
        "turno": row.get("turno"),
        "pdvCodigo": row.get("pdvCodigo"),
        "funcionarioCodigo": row.get("funcionarioCodigo"),
        "despesaApurado": float(apur) if apur not in (None, "") else None,
        "despesaApresentado": float(apres) if apres not in (None, "") else None,
        "despesaDiferenca": float(diff) if diff not in (None, "") else None,
        "codigo": row.get("codigo") or row.get("caixaCodigo"),
        "origem": origem,
    }


def _closure_key(r: dict) -> tuple:
    return (
        r.get("empresaCodigo"),
        r.get("dataMovimento"),
        r.get("caixaCodigo"),
        r.get("turnoCodigo"),
        r.get("pdvCodigo"),
    )


async def main() -> None:
    cfg = load_core_config()
    client = WebPostoClient(cfg)
    svc = NetworkFinancialOverviewService(client)
    filters = FinancialOverviewFilters(data_inicial=DATA, data_final=DATA, empresa_codigo=EMPRESA)

    raw_by_source: dict[str, list[dict]] = {}
    for label, key in SOURCES.items():
        rows = await svc._fetch_paginated_endpoint(key, filters)
        filtered = [r for r in rows if r.get("empresaCodigo") == EMPRESA and _shift_date(r) == DATA]
        raw_by_source[label] = [_norm_row(r, label) for r in filtered if _norm_row(r, label).get("despesaApurado") or _norm_row(r, label).get("despesaApresentado")]

    # merge like screen loader
    ap_map = {}
    for src in ("CAIXA_APRESENTADO", "CAIXA_APRESENTADO_REDE"):
        for r in raw_by_source.get(src, []):
            ap_map[(r["empresaCodigo"], r["caixaCodigo"])] = r

    caixa_rede = [{**r, "origem": "CAIXA_REDE"} for r in raw_by_source.get("CAIXA_REDE", [])]
    caixa = [{**r, "origem": "CAIXA"} for r in raw_by_source.get("CAIXA", [])]
    seen = {(r["empresaCodigo"], r["caixaCodigo"]) for r in caixa_rede}
    caixa_rows = caixa_rede + [r for r in caixa if (r["empresaCodigo"], r["caixaCodigo"]) not in seen]

    screen_lines = []
    for row in caixa_rows:
        ap = ap_map.get((row["empresaCodigo"], row["caixaCodigo"]), {})
        merged_apur = ap.get("despesaApurado") or row.get("despesaApurado")
        merged_apres = ap.get("despesaApresentado") or row.get("despesaApresentado")
        if merged_apres:
            screen_lines.append({**row, "screenOrigem": "caixa", "valor": merged_apres, "fonteValor": "apresentado"})
        if merged_apur:
            screen_lines.append({**row, "screenOrigem": "pdv", "valor": merged_apur, "fonteValor": "apurado"})

    # API screen
    from fastapi.testclient import TestClient
    from src.main import app

    with TestClient(app) as tc:
        api = tc.get(
            "/v1/financial/expenses",
            params={"empresaCodigo": EMPRESA, "dataInicial": DATA, "dataFinal": DATA, "page": 1, "limit": 500},
            timeout=300,
        ).json()["data"]

    dup_keys: dict[tuple, list] = defaultdict(list)
    for line in screen_lines:
        dup_keys[_closure_key(line)].append(line)

    duplicates = {k: v for k, v in dup_keys.items() if len(v) > 1}

    out = {
        "case": {"empresaCodigo": EMPRESA, "data": DATA},
        "rawBySource": raw_by_source,
        "mergedClosures": caixa_rows,
        "screenLinesBeforeFix": screen_lines,
        "duplicateClosureKeys": {str(k): v for k, v in duplicates.items()},
        "apiResumo": api.get("resumoPorOrigem"),
        "apiTotal": api.get("total"),
        "apiRows": [
            {
                "origem": r.get("origem"),
                "valor": r.get("valor"),
                "caixaCodigo": r.get("caixaCodigo"),
                "pdvCodigo": r.get("pdvCodigo"),
                "turno": r.get("funcionarioCodigo"),
                "descricao": r.get("descricao"),
            }
            for r in api.get("data", [])
        ],
    }
    path = ROOT / "scripts" / "p0_1b_caixa_dedup_audit.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
