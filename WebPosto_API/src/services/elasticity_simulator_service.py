"""Simulador de elasticidade de preço — histórico local sales_daily_summary (90d)."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlmodel import col

from src.infrastructure.config.database import AsyncSessionLocal
from src.models.sales_daily_summary_model import SalesDailySummaryModel

logger = logging.getLogger(__name__)

FILIAL_NAMES = {
    5555: "AP Casa Caiada",
    11495: "Posto VIP",
    74014: "Posto Real / Doze",
}


class ElasticitySimulatorService:
    async def list_products(
        self, empresa_codigo: int | None = None, days: int = 90
    ) -> dict[str, Any]:
        end = date.today()
        start = end - timedelta(days=max(7, days) - 1)
        rows = await self._load_rows(start, end, empresa_codigo)
        products: dict[str, dict[str, Any]] = {}
        for r in rows:
            code = str(r.codigo_produto_webposto or "").strip()
            if not code:
                continue
            bucket = products.setdefault(
                code,
                {
                    "codigoProduto": code,
                    "nomeProduto": r.nome_produto or code,
                    "empresaCodigo": r.empresa_codigo,
                    "empresaNome": FILIAL_NAMES.get(r.empresa_codigo, str(r.empresa_codigo)),
                    "litros": 0.0,
                    "faturamento": 0.0,
                    "margem": 0.0,
                    "dias": 0,
                },
            )
            bucket["litros"] += float(r.litros_vendidos or 0)
            bucket["faturamento"] += float(r.faturamento_bruto or 0)
            bucket["margem"] += float(r.margem_bruta_real or 0)
            bucket["dias"] += 1
            if r.nome_produto and len(r.nome_produto) > len(bucket["nomeProduto"]):
                bucket["nomeProduto"] = r.nome_produto

        items = []
        for p in products.values():
            litros = p["litros"]
            fat = p["faturamento"]
            preco = fat / litros if litros > 0 else 0.0
            custo = (
                (fat - p["margem"]) / litros if litros > 0 else 0.0
            )
            epsilon = self._epsilon_for_series(
                [r for r in rows if str(r.codigo_produto_webposto) == p["codigoProduto"]]
            )
            items.append(
                {
                    **p,
                    "precoMedioRsLitro": round(preco, 4),
                    "custoMedioRsLitro": round(max(custo, 0), 4),
                    "coeficienteElasticidade": epsilon,
                    "label": f"{p['nomeProduto']} — {p['empresaNome']}",
                }
            )
        items.sort(key=lambda x: x["litros"], reverse=True)
        return {
            "periodo": {"inicio": start.isoformat(), "fim": end.isoformat()},
            "fonte": "sales_daily_summary",
            "produtos": items[:40],
            "success": True,
            "mensagem": None if items else "Sem histórico local — rode o backfill 90 dias",
        }

    async def simulate(
        self,
        empresa_codigo: int,
        codigo_produto: str,
        delta_preco_rs: float,
        days: int = 90,
    ) -> dict[str, Any]:
        catalog = await self.list_products(empresa_codigo, days)
        prod = next(
            (
                p
                for p in catalog["produtos"]
                if str(p["codigoProduto"]) == str(codigo_produto)
                and int(p["empresaCodigo"]) == int(empresa_codigo)
            ),
            None,
        )
        if not prod:
            # tenta sem filtro estrito de empresa no label
            prod = next(
                (
                    p
                    for p in catalog["produtos"]
                    if str(p["codigoProduto"]) == str(codigo_produto)
                ),
                None,
            )
        if not prod:
            return {
                "success": False,
                "mensagem": "Produto sem histórico no banco local",
                "projecao": None,
            }

        litros_base = float(prod["litros"])
        preco_base = float(prod["precoMedioRsLitro"])
        custo = float(prod["custoMedioRsLitro"])
        epsilon = float(prod["coeficienteElasticidade"] or -1.2)
        if preco_base <= 0 or litros_base <= 0:
            return {
                "success": False,
                "mensagem": "Base insuficiente para simular",
                "projecao": None,
            }

        delta_pct_preco = delta_preco_rs / preco_base
        delta_pct_vol = epsilon * delta_pct_preco
        litros_novo = max(0.0, litros_base * (1 + delta_pct_vol))
        preco_novo = max(0.01, preco_base + delta_preco_rs)
        fat_base = litros_base * preco_base
        fat_novo = litros_novo * preco_novo
        margem_base = litros_base * max(preco_base - custo, 0)
        margem_nova = litros_novo * max(preco_novo - custo, 0)

        return {
            "success": True,
            "produto": prod,
            "parametros": {
                "deltaPrecoRs": round(delta_preco_rs, 2),
                "deltaPctPreco": round(delta_pct_preco * 100, 2),
                "epsilon": epsilon,
            },
            "projecao": {
                "volumeBaseLitros": round(litros_base, 2),
                "volumeNovoLitros": round(litros_novo, 2),
                "deltaVolumePct": round(delta_pct_vol * 100, 2),
                "faturamentoBase": round(fat_base, 2),
                "faturamentoNovo": round(fat_novo, 2),
                "lucroBrutoBase": round(margem_base, 2),
                "lucroBrutoNovo": round(margem_nova, 2),
                "precoBase": round(preco_base, 4),
                "precoNovo": round(preco_novo, 4),
            },
        }

    async def _load_rows(
        self, start: date, end: date, empresa_codigo: int | None
    ) -> list[SalesDailySummaryModel]:
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(SalesDailySummaryModel).where(
                    col(SalesDailySummaryModel.data_referencia) >= start,
                    col(SalesDailySummaryModel.data_referencia) <= end,
                    col(SalesDailySummaryModel.litros_vendidos) > 0,
                )
                if empresa_codigo:
                    stmt = stmt.where(
                        SalesDailySummaryModel.empresa_codigo == int(empresa_codigo)
                    )
                result = await session.execute(stmt)
                return list(result.scalars().all())
        except Exception as exc:
            logger.warning("elasticity_simulator load falhou: %s", exc)
            return []

    @staticmethod
    def _epsilon_for_series(rows: list[SalesDailySummaryModel]) -> float:
        """ε ≈ Δ%vol / Δ%preço ao longo da série diária (ordenado por data)."""
        points: list[tuple[float, float]] = []
        for r in sorted(rows, key=lambda x: x.data_referencia):
            litros = float(r.litros_vendidos or 0)
            fat = float(r.faturamento_bruto or 0)
            if litros <= 0 or fat <= 0:
                continue
            points.append((fat / litros, litros))
        if len(points) < 3:
            return -1.2  # default combustível inelasticidade típica leve
        p0, v0 = points[0]
        p1, v1 = points[-1]
        if p0 <= 0 or v0 <= 0:
            return -1.2
        d_p = (p1 - p0) / p0
        d_v = (v1 - v0) / v0
        if abs(d_p) < 1e-6:
            return -1.2
        eps = d_v / d_p
        # clamp razoável para combustível
        return round(max(-5.0, min(-0.1, eps)), 3)
