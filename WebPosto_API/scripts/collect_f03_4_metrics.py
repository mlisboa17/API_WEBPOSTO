#!/usr/bin/env python3
"""Coleta métricas F03.4 — janela curta recomendada (7d) para evitar timeout."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    env = os.environ.copy()
    env.setdefault("F03_4_WINDOW", "7d")
    env.setdefault("F03_4_INCLUDE_WINDOWS", "0")
    cmd = [sys.executable, str(ROOT / "scripts" / "audit_f03_4_operator_performance.py")]
    print("Running:", " ".join(cmd), "F03_4_WINDOW=", env["F03_4_WINDOW"])
    subprocess.run(cmd, env=env, check=False)


if __name__ == "__main__":
    main()
