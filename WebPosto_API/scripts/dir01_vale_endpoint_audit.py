#!/usr/bin/env python3
"""DIR-01 FASE 1 — auditoria VALE_FUNCIONARIO_REDE (sem expor token)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx

from src.core.config import load_core_config
from src.gateway.webposto_client import WebPostoClient

ENDPOINTS = [
    ("VALE_FUNCIONARIO_REDE", "/INTEGRACAO/VALE_FUNCIONARIO_REDE"),
    ("CONSULTAR_VALE_FUNCIONARIO_REDE", "/INTEGRACAO/CONSULTAR_VALE_FUNCIONARIO_REDE"),
    ("DESPESA_FUNCIONARIO", "/INTEGRACAO/DESPESA_FUNCIONARIO"),
    ("CONSULTAR_DESPESA_FUNCIONARIO_REDE", "/INTEGRACAO/CONSULTAR_DESPESA_FUNCIONARIO_REDE"),
    ("FUNCIONARIO_MOVIMENTO", "/INTEGRACAO/FUNCIONARIO_MOVIMENTO"),
]
TENANTS = [5555, 11495, 74014]
PERIOD = ("2026-06-05", "2026-07-04")


def _rows(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data", "items"):
            chunk = payload.get(key)
            if isinstance(chunk, list):
                return [r for r in chunk if isinstance(r, dict)]
    return []


async def main() -> int:
    cfg = load_core_config()
    client = WebPostoClient(cfg)
    permissions = await client.discover_permissions(force=True)
    di, df = PERIOD
    api_key = cfg.webposto_api_key

    report: dict = {
        "base_url": cfg.webposto_base_url,
        "period": {"start": di, "end": df},
        "credential_tokens_configured": len(cfg.webposto_api_keys or [api_key]),
        "permission_cache": {},
        "http_probe": [],
    }

    for name, path in ENDPOINTS:
        report["permission_cache"][name] = {
            "path": path,
            "allowed_in_cache": permissions.get(name.lower().replace("_rede", "_rede"), None),
        }

    async with httpx.AsyncClient(base_url=cfg.webposto_base_url, timeout=45.0) as http:
        for name, path in ENDPOINTS:
            for empresa in [None, *TENANTS]:
                params: dict = {"dataInicial": di, "dataFinal": df, "CHAVE": api_key}
                if empresa is not None:
                    params["empresaCodigo"] = empresa
                try:
                    resp = await http.get(path, params=params)
                    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None
                    rows = _rows(body)
                    sample = rows[0] if rows else {}
                    report["http_probe"].append(
                        {
                            "endpoint": name,
                            "path": path,
                            "method": "GET",
                            "empresaCodigo": empresa,
                            "http_status": resp.status_code,
                            "row_count": len(rows),
                            "sample_fields": sorted(sample.keys())[:20] if sample else [],
                            "body_type": type(body).__name__,
                        }
                    )
                except Exception as exc:
                    report["http_probe"].append(
                        {
                            "endpoint": name,
                            "path": path,
                            "empresaCodigo": empresa,
                            "http_status": 0,
                            "error": str(exc)[:160],
                        }
                    )

    out = ROOT / "docs" / "validation" / "DIR_01_VALE_ENDPOINT_AUDIT.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
