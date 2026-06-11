#!/usr/bin/env python3
"""Validação P0 — tela de despesas consolidada (AP CASA CAIADA 08/06/2026)."""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "scripts" / "p0_expenses_screen_validation.json"

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

CASE = {
    "empresaCodigo": 5555,
    "dataInicial": "2026-06-08",
    "dataFinal": "2026-06-08",
    "nome": "AP CASA CAIADA",
}


def _sum(rows: list[dict]) -> Decimal:
    total = Decimal("0")
    for row in rows:
        total += Decimal(str(row.get("valor") or 0))
    return total.quantize(Decimal("0.01"))


def main() -> int:
    if not (os.environ.get("WEBPOSTO_API_KEY") or os.environ.get("WEBPOSTO_CHAVE")):
        print("WEBPOSTO_API_KEY ausente — carregue .env ou exporte a chave.")
        return 2

    from fastapi.testclient import TestClient

    from src.main import app

    results: dict = {"case": CASE, "scenarios": []}
    scenarios = [
        {"label": "5555", "params": CASE},
        {"label": "11495", "params": {**CASE, "empresaCodigo": 11495}},
        {"label": "11495,5555", "params": {**CASE, "empresaCodigo": "11495,5555"}},
        {"label": "Todos", "params": {k: v for k, v in CASE.items() if k != "empresaCodigo"}},
    ]

    with TestClient(app) as client:
        for scenario in scenarios:
            response = client.get(
                "/v1/financial/expenses",
                params={**scenario["params"], "page": 1, "limit": 500},
                timeout=300.0,
            )
            response.raise_for_status()
            body = response.json()
            if not body.get("success"):
                raise RuntimeError(body.get("error"))
            payload = body["data"]
            rows = payload.get("data") or []
            by_origem: dict[str, int] = {}
            for row in rows:
                origem = str(row.get("origem") or "desconhecido")
                by_origem[origem] = by_origem.get(origem, 0) + 1
            bobina = [r for r in rows if "BOBINA" in str(r.get("descricao") or r.get("planoConta") or "").upper()]
            results["scenarios"].append(
                {
                    "label": scenario["label"],
                    "total": payload.get("total"),
                    "sumValor": str(_sum(rows)),
                    "resumoPorOrigem": payload.get("resumoPorOrigem"),
                    "byOrigem": by_origem,
                    "bobinaCount": len(bobina),
                }
            )

    case_5555 = next(s for s in results["scenarios"] if s["label"] == "5555")
    case_5555["pass"] = case_5555["total"] > 1
    results["parecer"] = "APROVADO" if case_5555["pass"] else "RETIDO"
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if case_5555["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
