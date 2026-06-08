#!/usr/bin/env python3
"""Validação Snapshot First — Finance Center MISS vs HIT (TTL 5min)."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:8040"
PERIOD = {"dataInicial": "2026-06-01", "dataFinal": "2026-06-07"}
OUT = ROOT / "scripts" / "f01_snapshot_miss_hit.json"


async def snapshot_get(client: httpx.AsyncClient) -> tuple[dict, float]:
    t0 = time.perf_counter()
    r = await client.get(f"{BASE}/api/v1/finance/center/snapshot", params=PERIOD, timeout=120)
    ms = round((time.perf_counter() - t0) * 1000, 1)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    return body.get("data") or {}, ms


async def snapshot_refresh(client: httpx.AsyncClient) -> None:
    await client.post(f"{BASE}/api/v1/finance/center/refresh", params=PERIOD, timeout=30)


async def main() -> int:
    result: dict = {"period": PERIOD, "miss": {}, "hit": {}, "pass": False}
    async with httpx.AsyncClient() as client:
        try:
            await client.get(f"{BASE}/health", timeout=5)
        except Exception as exc:
            print(f"Backend indisponível em {BASE}: {exc}")
            return 1

        # Garantir estado limpo: refresh e aguardar coleta
        await snapshot_refresh(client)
        await asyncio.sleep(8)

        data1, ms1 = await snapshot_get(client)
        hit1 = bool(data1.get("fromSnapshot"))
        result["first_after_refresh"] = {"fromSnapshot": hit1, "ms": ms1}

        if not hit1:
            await asyncio.sleep(12)
            data1, ms1 = await snapshot_get(client)
            hit1 = bool(data1.get("fromSnapshot"))

        # MISS simulado: chave diferente (empresa 11495) sem cache
        miss_params = {**PERIOD, "empresaCodigo": "11495"}
        t0 = time.perf_counter()
        miss_resp = await client.get(
            f"{BASE}/api/v1/finance/center/snapshot",
            params=miss_params,
            timeout=120,
        )
        miss_ms = round((time.perf_counter() - t0) * 1000, 1)
        miss_body = miss_resp.json().get("data") or {}
        result["miss"] = {
            "fromSnapshot": bool(miss_body.get("fromSnapshot")),
            "ms": miss_ms,
            "empresaCodigo": "11495",
        }

        await snapshot_refresh(client)
        hit_body = {}
        hit_ms = 0.0
        for _ in range(18):
            await asyncio.sleep(5)
            t0 = time.perf_counter()
            hit_resp = await client.get(
                f"{BASE}/api/v1/finance/center/snapshot",
                params=miss_params,
                timeout=120,
            )
            hit_ms = round((time.perf_counter() - t0) * 1000, 1)
            hit_body = hit_resp.json().get("data") or {}
            if hit_body.get("fromSnapshot"):
                break
        result["hit"] = {
            "fromSnapshot": bool(hit_body.get("fromSnapshot")),
            "ms": hit_ms,
            "empresaCodigo": "11495",
            "target_ms": 500,
            "within_target": hit_ms < 500,
        }

        # HIT rede (all)
        data_hit_all, ms_hit_all = await snapshot_get(client)
        result["hit_rede"] = {
            "fromSnapshot": bool(data_hit_all.get("fromSnapshot")),
            "ms": ms_hit_all,
            "within_target": ms_hit_all < 500,
        }

        result["pass"] = (
            result["miss"]["fromSnapshot"] is False
            and result["hit"]["fromSnapshot"] is True
            and result["hit_rede"]["fromSnapshot"] is True
        )

    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nGravado em {OUT}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
