"""Validação pós-ajuste de credenciais e rotas operacionais."""
from __future__ import annotations

import asyncio

import httpx

from src.core.config import (
    OFFICIAL_COMPANY_CREDENTIAL_ALIASES,
    load_core_config,
    resolve_company_api_key,
)


async def main() -> None:
    cfg = load_core_config()
    print("=== CREDENCIAIS ===")
    print("base_url=", cfg.webposto_base_url)
    print(
        "company_keys=",
        {k: ("SET" if v else "EMPTY") for k, v in cfg.webposto_company_keys.items()},
    )
    for code, aliases in OFFICIAL_COMPANY_CREDENTIAL_ALIASES.items():
        k = resolve_company_api_key(code)
        status = f"SET({len(k)})" if k else "EMPTY"
        print(f"  {code} preferred={aliases[0]} resolved={status}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.get("http://127.0.0.1:8040/api/v1/operational/cockpit-live")
        data = r.json()
        print(f"\n=== COCKPIT-LIVE HTTP {r.status_code} ===")
        for f in data.get("filiais") or []:
            print(
                f"  {f['empresa_codigo']} {f['empresa_nome']}: "
                f"litros={f['total_litros']} fat={f['total_valor']} "
                f"qtd={f['total_transacoes']} status={f['status']}"
            )

        for code in (11495, 74014, 5555):
            r2 = await client.get(
                f"http://127.0.0.1:8040/api/v1/operational/inventory-prediction"
                f"?empresaCodigo={code}"
            )
            body = r2.json()
            alerts = [
                (p.get("produto_nome"), p.get("status_alerta"))
                for p in (body.get("predicoes") or [])
                if p.get("status_alerta") != "OK"
            ]
            print(
                f"\n=== INVENTORY {code} HTTP {r2.status_code} "
                f"pred={len(body.get('predicoes') or [])} ==="
            )
            print("  alerts=", alerts)


if __name__ == "__main__":
    asyncio.run(main())
