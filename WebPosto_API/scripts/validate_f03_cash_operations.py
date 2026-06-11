#!/usr/bin/env python3
"""Sprint F03 — Validação QA de paridade Cash Operations."""
from __future__ import annotations

import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.cash_operations_service import CashOperationsService, W_HIST, W_OPERATOR, W_PDV, W_TURN
from src.services.cash_operations_snapshot_service import (
    CASH_OPERATIONS_SNAPSHOT_TTL_SECONDS,
    CashOperationsSnapshotService,
)

DATA_INI = "2026-06-01"
DATA_FIM = "2026-06-07"


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


async def main() -> int:
    failures: list[str] = []
    evidence: dict = {}

    if round(W_OPERATOR + W_PDV + W_TURN + W_HIST, 2) != 1.0:
        failures.append("Pesos risk score != 1.0")

    if CASH_OPERATIONS_SNAPSHOT_TTL_SECONDS != 300.0:
        failures.append(f"TTL snapshot incorreto: {CASH_OPERATIONS_SNAPSHOT_TTL_SECONDS}")

    svc = CashOperationsService()
    snap = CashOperationsSnapshotService(svc, output_dir="snapshots/cash_operations_qa")

    resp = await svc.build(DATA_INI, DATA_FIM)
    if not resp.success or not resp.data:
        failures.append(f"Build falhou: {resp.error}")
        print(json.dumps({"ok": False, "failures": failures}, indent=2, ensure_ascii=False))
        return 1

    base = resp.data
    master = await snap.collect(DATA_INI, DATA_FIM)
    cached = master.get("operations") or {}

    checks = [
        ("summary.diferencaTotalRede", base.get("summary", {}).get("diferencaTotalRede"), cached.get("summary", {}).get("diferencaTotalRede")),
        ("summary.cashRiskScore", base.get("summary", {}).get("cashRiskScore"), cached.get("summary", {}).get("cashRiskScore")),
        ("alerts.total", base.get("alerts", {}).get("total"), cached.get("alerts", {}).get("total")),
        ("riskScore.consolidado", base.get("riskScore", {}).get("consolidado"), cached.get("riskScore", {}).get("consolidado")),
    ]
    for label, a, b in checks:
        if _money(a) != _money(b):
            failures.append(f"Paridade snapshot {label}: base={a} cache={b}")

    slice_keys = ("summary", "alerts", "risk", "operators", "pdvs", "turns")
    for domain in slice_keys:
        key = snap.key(domain, DATA_INI, DATA_FIM, None)
        stored, _ = snap._store.load_stale(key)
        if not stored:
            failures.append(f"Snapshot slice ausente: {key}")

    import time as _time

    t0 = _time.perf_counter()
    snap.get_master(DATA_INI, DATA_FIM, None)
    snapshot_read_ms = round((_time.perf_counter() - t0) * 1000, 1)
    if snapshot_read_ms >= 2000:
        failures.append(f"Snapshot read acima de 2s: {snapshot_read_ms}ms")

    summary = base.get("summary", {})
    evidence = {
        "alertasAtivos": base.get("alerts", {}).get("total"),
        "operadoresCriticos": base.get("riskScore", {}).get("operadoresCriticos"),
        "pdvsCriticos": base.get("riskScore", {}).get("pdvsCriticos"),
        "cashRiskScore": base.get("riskScore", {}).get("consolidado"),
        "diferencaTotalRede": summary.get("diferencaTotalRede"),
        "potencialRecuperavel30pct": summary.get("potencialRecuperavel30pct"),
        "performanceMs": base.get("performanceMs"),
        "snapshotReadMs": snapshot_read_ms,
        "paridadeOk": len(failures) == 0,
    }

    out = ROOT / "scripts" / "f03_cash_operations_qa.json"
    out.write_text(json.dumps({"evidence": evidence, "failures": failures}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"ok": len(failures) == 0, "failures": failures, "evidence": evidence}, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
