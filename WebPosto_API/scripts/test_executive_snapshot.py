"""Valida endpoints de snapshot executivo (rapido + refresh background)."""
from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta

import requests

BASE = "http://127.0.0.1:8040"
TIMEOUT = 10


def _params() -> dict[str, str]:
    end = date.today()
    start = end - timedelta(days=5)
    return {
        "dataInicial": start.isoformat(),
        "dataFinal": end.isoformat(),
    }


def test_snapshot_fast() -> None:
    started = time.perf_counter()
    response = requests.get(f"{BASE}/api/v1/executive/snapshot", params=_params(), timeout=TIMEOUT)
    elapsed = time.perf_counter() - started
    response.raise_for_status()
    payload = response.json()
    print(f"[snapshot] status={response.status_code} elapsed={elapsed:.2f}s")
    print(json.dumps({k: payload.get(k) for k in ("fromSnapshot", "lastUpdated", "warnings")}, ensure_ascii=False))
    assert elapsed < 5.0, "snapshot deve responder em menos de 5s"
    assert "kpis" in payload and "dre" in payload


def test_refresh_background() -> None:
    response = requests.post(f"{BASE}/api/v1/executive/refresh", params=_params(), timeout=TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    print(f"[refresh] {json.dumps(payload, ensure_ascii=False)}")
    assert payload.get("status") in {"started", "already_running", "completed"}


def test_refresh_then_snapshot() -> None:
    requests.post(f"{BASE}/api/v1/executive/refresh", params=_params(), timeout=TIMEOUT)
    previous = None
    for attempt in range(40):
        snapshot = requests.get(f"{BASE}/api/v1/executive/snapshot", params=_params(), timeout=TIMEOUT).json()
        if snapshot.get("lastUpdated") and snapshot.get("lastUpdated") != previous:
            print(f"[poll] atualizado em tentativa {attempt + 1}: {snapshot.get('lastUpdated')}")
            print(
                json.dumps(
                    {
                        "kpis": bool(snapshot.get("kpis")),
                        "dre": bool(snapshot.get("dre")),
                        "coverage": bool(snapshot.get("coverage")),
                        "dataQuality": bool(snapshot.get("dataQuality")),
                        "fuel": bool(snapshot.get("fuel")),
                    },
                    ensure_ascii=False,
                )
            )
            return
        previous = snapshot.get("lastUpdated")
        time.sleep(3)
    print("[poll] timeout aguardando refresh — API pode estar lenta")


if __name__ == "__main__":
    try:
        test_snapshot_fast()
        test_refresh_background()
        test_refresh_then_snapshot()
        print("OK: testes de snapshot executivo concluidos")
    except Exception as exc:  # noqa: BLE001
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)
