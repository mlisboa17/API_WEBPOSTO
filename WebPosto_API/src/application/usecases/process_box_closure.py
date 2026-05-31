"""Caso de uso: fechamento de caixa (resumo do período)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict

from src.domain.gateways.posto_gateway import PostoGateway


class ProcessBoxClosureUseCase:
    def __init__(self, gateway: PostoGateway) -> None:
        self._gateway = gateway

    async def execute(self, dia: date | None = None) -> Dict[str, Any]:
        ref = dia or date.today()
        movimentos = await self._gateway.get_caixa_periodo(ref, ref)
        total = Decimal("0")
        for m in movimentos:
            v = m.get("valor") or m.get("valorTotal") or 0
            try:
                total += Decimal(str(v))
            except Exception:
                pass
        return {
            "data": ref.isoformat(),
            "movimentos": len(movimentos),
            "valor_total": float(total),
        }
