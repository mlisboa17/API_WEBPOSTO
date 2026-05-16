"""
Suíte de correção — executa testes unitários críticos e reporta status.
Uso: python -m tests.fix_suite
"""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/test_client.py",
        "tests/unit/test_get_cobertura_total.py",
        "tests/unit/application/test_cliente_service.py",
        "-q",
        "--tb=line",
    ]
    print("Executando:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=None)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
