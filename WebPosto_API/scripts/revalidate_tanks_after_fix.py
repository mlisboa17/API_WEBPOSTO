"""Revalidação rápida pós-fix de campos de tanque."""
from __future__ import annotations

import asyncio

import httpx

from src.services.webposto_integration_service import get_webposto_integration_service

FILIAIS = [(5555, "Casa Caiada"), (11495, "VIP"), (74014, "Real Doze")]
API = "http://127.0.0.1:8040"


async def main() -> None:
    svc = get_webposto_integration_service()
    print("=== REVALIDACAO POS-FIX (estoqueEscritural/resultados) ===")
    async with httpx.AsyncClient(timeout=90.0) as client:
        for code, name in FILIAIS:
            tanks = await svc.get_tank_levels(code)
            sales = await svc.get_realtime_sales(code)
            print(f"\n{name} ({code})")
            print(f"  TANQUE service: sucesso={tanks.sucesso} qtd={len(tanks.tanques)}")
            if tanks.tanques:
                t = tanks.tanques[0]
                print(
                    "  amostra tanque:",
                    t["tanque_codigo"],
                    "|",
                    t["produto_nome"],
                    f"| vol={t['volume_atual_litros']} / cap={t['capacidade_litros']} ({t['ocupacao_pct']}%)",
                )
            print(
                f"  VENDAS: litros={sales.litros_total} fat={sales.faturamento_rs} qtd={sales.qtd_abastecimentos}"
            )

            r1 = await client.get(f"{API}/api/v1/operational/realtime-bundle?empresaCodigo={code}")
            b1 = r1.json()
            itens = ((b1.get("data") or {}).get("tanques") or {}).get("itens") or []
            vol0 = itens[0].get("volume_atual_litros") if itens else None
            print(f"  realtime-bundle HTTP {r1.status_code} tanques={len(itens)} vol0={vol0}")

            r2 = await client.get(
                f"{API}/api/v1/operational/inventory-prediction?empresaCodigo={code}"
            )
            b2 = r2.json()
            preds = b2.get("predicoes") or []
            print(
                f"  inventory-prediction HTTP {r2.status_code} predicoes={len(preds)} obs={b2.get('observacoes')}"
            )
            if preds:
                p = preds[0]
                print(
                    "  amostra pred:",
                    p.get("produto_nome"),
                    f"estoque={p.get('estoque_atual_litros')}",
                    f"autonomia_h={p.get('autonomia_horas_restantes')}",
                    f"status={p.get('status_alerta')}",
                )


if __name__ == "__main__":
    asyncio.run(main())
