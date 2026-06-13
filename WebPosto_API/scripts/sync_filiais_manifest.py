#!/usr/bin/env python3
"""Onda 1 — Gera manifest JSON de filiais a partir de app_core.filial_registry."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app_core.filial_registry import get_filiais_ativas, list_filiais

OUT = ROOT / "frontend" / "data" / "filiais.json"


def main() -> None:
    filiais = list_filiais()
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "app_core.filial_registry",
        "count": len(filiais),
        "activeCount": len(get_filiais_ativas()),
        "filiais": [filial.to_manifest_row() for filial in filiais],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({payload['count']} filiais, {payload['activeCount']} ativas)")


if __name__ == "__main__":
    main()
