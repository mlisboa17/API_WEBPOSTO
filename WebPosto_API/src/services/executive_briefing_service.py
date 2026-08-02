"""Briefing executivo automático (D-1) para o cockpit da diretoria."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Optional

from src.core.config import OFFICIAL_COMPANY_CODES
from src.services.logistics_freight_service import LogisticsFreightService
from src.services.sales_composition_service import SalesCompositionService

logger = logging.getLogger(__name__)

FILIAL = {5555: "Casa Caiada", 11495: "VIP", 74014: "Real Doze"}


class ExecutiveBriefingService:
    def __init__(self) -> None:
        self._composition = SalesCompositionService()
        self._logistics = LogisticsFreightService()

    async def build(
        self,
        data_referencia: Optional[str] = None,
        empresa_codigo: Optional[int] = None,
    ) -> dict[str, Any]:
        ref = data_referencia or (date.today() - timedelta(days=1)).isoformat()
        targets = (
            [int(empresa_codigo)]
            if empresa_codigo
            else list(OFFICIAL_COMPANY_CODES)
        )

        best_vol: dict[str, Any] | None = None
        best_margin: dict[str, Any] | None = None
        worst_margin: dict[str, Any] | None = None

        for code in targets:
            try:
                comp = await self._composition.build(ref, ref, code)
            except Exception as exc:
                logger.warning("briefing composition empresa=%s: %s", code, exc)
                continue
            fuels = getattr(comp, "combustiveis", None) or []
            if isinstance(comp, dict):
                fuels = comp.get("combustiveis") or []
            for item in fuels:
                if isinstance(item, dict):
                    cat = str(item.get("categoria") or item.get("nome") or "Combustível")
                    litros = float(item.get("litros") or 0)
                    fat = float(item.get("faturamento") or item.get("faturamento_rs") or 0)
                    margem = float(item.get("margem") or item.get("margem_rs") or 0)
                else:
                    cat = str(getattr(item, "categoria", None) or "Combustível")
                    litros = float(getattr(item, "litros", 0) or 0)
                    fat = float(getattr(item, "faturamento", 0) or 0)
                    margem = float(getattr(item, "margem", 0) or 0)
                margem_pct = (margem / fat * 100) if fat > 0 else None
                row = {
                    "filial": FILIAL.get(code, str(code)),
                    "empresaCodigo": code,
                    "produto": cat,
                    "litros": litros,
                    "faturamento": fat,
                    "margem": margem,
                    "margemPct": margem_pct,
                }
                if litros > 0 and (best_vol is None or litros > best_vol["litros"]):
                    best_vol = row
                # Ranking por margem absoluta (R$); % só como complemento
                if fat > 0 or margem != 0:
                    if best_margin is None or margem > (best_margin.get("margem") or -1e9):
                        best_margin = row
                    if worst_margin is None or margem < (worst_margin.get("margem") or 1e9):
                        worst_margin = row

        frete_medio = 0.0
        frete_fonte = ""
        try:
            log = await self._logistics.analyze(ref, ref, empresa_codigo)
            frete_medio = float(log.frete_medio_grupo_rs_litro or 0)
            frete_fonte = log.fonte or ""
        except Exception as exc:
            logger.warning("briefing logistics: %s", exc)

        destaques = [
            {
                "tipo": "volumetria",
                "titulo": "Destaque de Volumetria",
                "texto": self._text_volume(best_vol, ref),
            },
            {
                "tipo": "margem",
                "titulo": "Destaque de Margem",
                "texto": self._text_margin(best_margin, worst_margin, ref),
            },
            {
                "tipo": "logistica",
                "titulo": "Destaque Logístico",
                "texto": self._text_freight(frete_medio, frete_fonte, ref),
            },
        ]
        return {
            "dataReferencia": ref,
            "empresaCodigo": empresa_codigo,
            "destaques": destaques,
        }

    @staticmethod
    def _text_volume(row: dict[str, Any] | None, ref: str) -> str:
        if not row:
            return f"Ontem ({ref}): sem volume de combustível apurado para o recorte."
        litros = f"{row['litros']:,.0f}".replace(",", ".")
        return (
            f"Maior volumetria ontem: {row['produto']} em {row['filial']} "
            f"com {litros} L vendidos."
        )

    @staticmethod
    def _text_margin(
        best: dict[str, Any] | None,
        worst: dict[str, Any] | None,
        ref: str,
    ) -> str:
        if not best and not worst:
            return f"Ontem ({ref}): margem por produto ainda sem base suficiente."

        def _fmt(row: dict[str, Any]) -> str:
            if row.get("margemPct") is not None and abs(float(row["margemPct"] or 0)) > 0.05:
                return f"{row['margemPct']:.1f}%"
            return f"R$ {float(row.get('margem') or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        parts: list[str] = []
        if best:
            parts.append(
                f"Maior margem: {best['produto']} ({best['filial']}) com {_fmt(best)}."
            )
        if worst and (
            not best
            or worst["produto"] != best.get("produto")
            or worst["filial"] != best.get("filial")
        ):
            parts.append(
                f"Menor margem: {worst['produto']} ({worst['filial']}) com {_fmt(worst)}."
            )
        return " ".join(parts) if parts else f"Ontem ({ref}): margem estável no recorte."

    @staticmethod
    def _text_freight(frete: float, fonte: str, ref: str) -> str:
        if frete <= 0:
            return (
                f"Ontem ({ref}): sem frete destacado nas NFs de entrada "
                f"({fonte or 'webPosto'})."
            )
        return (
            f"Frete médio apurado via NF de entrada: R$ {frete:.4f}/L "
            f"({fonte or 'Dado Real - Fonte NF webPosto'})."
        )
