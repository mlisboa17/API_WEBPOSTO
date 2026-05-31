#!/usr/bin/env python3
"""
Prewarm de KPIs Adelaide e cache de catálogo GET — uso local.

  python scripts/seed_real_data.py --prewarm
  python scripts/seed_real_data.py --station "Posto Casa Caiada" --impact HIGH --prewarm
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def run_prewarm(station: str, impact: str) -> None:
    from src.presentation.app import _load_dotenv, _resolve_chave, create_unified_app

    _load_dotenv()
    chave = _resolve_chave()
    if not chave:
        print("WEBPOSTO_API_KEY ausente no .env — prewarm ignorado.")
        return

    app = create_unified_app()
    # Reutiliza handler interno via TestClient pattern
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for periodo in ("hoje", "7d", "mensal"):
            r = await client.get(
                "/api/v1/adelaide/metrics",
                params={"periodo": periodo, "api_key": chave},
            )
            data = r.json()
            print(
                f"  [{periodo}] HTTP {r.status_code} · "
                f"galonagem={data.get('galonagem_total')} · status={data.get('status_api')}"
            )

    from src.infrastructure.cache.valkey_manager import get_cache

    stats = get_cache().stats()
    print(f"\nCache: {stats['backend']} · hit ratio {stats['hit_ratio_pct']}%")
    print(f"Estação: {station} · impacto: {impact}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed / prewarm WebPosto KPIs")
    parser.add_argument("--station", default="Posto Casa Caiada")
    parser.add_argument("--impact", default="HIGH", choices=("LOW", "MEDIUM", "HIGH"))
    parser.add_argument("--prewarm", action="store_true", help="Pré-aquece KPIs hoje/7d/30d")
    args = parser.parse_args()

    if not args.prewarm:
        print("Use --prewarm para aquecer o cache Adelaide.")
        return

    print("Prewarm Adelaide KPIs…")
    asyncio.run(run_prewarm(args.station, args.impact))
    print("Concluído.")


if __name__ == "__main__":
    main()
