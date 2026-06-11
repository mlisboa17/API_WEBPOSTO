#!/usr/bin/env python3
"""F03.3 quick audit — apenas janela 90d + QA + snapshot."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("audit_f03_3", ROOT / "scripts" / "audit_f03_3_employee_ledger.py")
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)

WINDOWS_90 = {"90d": ("2026-03-09", "2026-06-07")}


async def main() -> None:
    mod.WINDOWS = WINDOWS_90
    await mod.main()


if __name__ == "__main__":
    asyncio.run(main())
