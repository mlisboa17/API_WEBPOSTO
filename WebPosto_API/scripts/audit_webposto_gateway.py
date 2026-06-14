#!/usr/bin/env python3
"""Onda 2 — QA gate gateway WebPosto unificado."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GATEWAY_DIR = ROOT / "gateway"
FORBIDDEN_TOKEN_LOG = re.compile(r'logger\.(info|debug|warning|error)\([^)]*api_key|CHAVE["\']?\s*:\s*self\.api_key', re.I)
MOTOR_GLOB = [
    "src/services/non_fuel_product_sales_service.py",
    "src/services/product_master_optimization_service.py",
    "src/services/product_master_enrichment_service.py",
    "src/services/produtos_vendidos_performance_service.py",
    "src/services/product_opportunity_assortment_service.py",
    "src/services/commercial_action_center_service.py",
    "src/services/commercial_execution_service.py",
]


def main() -> None:
    errors: list[str] = []

    required = [
        GATEWAY_DIR / "webposto_client.py",
        GATEWAY_DIR / "webposto_types.py",
        GATEWAY_DIR / "webposto_errors.py",
        ROOT / "tests" / "unit" / "test_webposto_gateway.py",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"ausente: {path.relative_to(ROOT)}")

    client_src = (GATEWAY_DIR / "webposto_client.py").read_text(encoding="utf-8")
    if "allow_live: bool = False" not in client_src and "allow_live=False" not in client_src:
        errors.append("allow_live default False ausente")
    if "empresaCodigo" not in client_src:
        errors.append("empresaCodigo não suportado")
    if "token_fingerprint" not in client_src:
        errors.append("token fingerprint ausente")
    if FORBIDDEN_TOKEN_LOG.search(client_src):
        errors.append("possível log de token completo em webposto_client.py")

    for rel in MOTOR_GLOB:
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "from gateway.webposto_client import" in text or "import gateway.webposto_client" in text:
            errors.append(f"motor migrado para gateway root: {rel}")

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit/test_webposto_gateway.py", "-q", "--no-cov", "--tb=no"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        errors.append(f"testes falharam: {proc.stdout}\n{proc.stderr}")

    print("WEBPOSTO GATEWAY QA")
    print(f"  erros: {len(errors)}")
    for err in errors:
        print(f"  - {err}")

    if errors:
        raise SystemExit(1)

    print("[PARECER FINAL: ONDA 2 WEBPOSTO GATEWAY APROVADA]")


if __name__ == "__main__":
    main()
