"""Pista & Volumetria — D0 = cache RAM (<50ms), D-1/histórico = sales_daily_summary (<200ms)."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select

from src.domain.adelaide.fuel_catalog import rotulo_combustivel
from src.utils.filial_normalizer import (
    EMPRESA_CASA_CAIADA,
    EMPRESA_REAL_DOZE,
    EMPRESA_VIP,
    resolve_empresa_codigo,
)

LOGGER = logging.getLogger(__name__)

FILIAIS: dict[int, str] = {
    EMPRESA_CASA_CAIADA: "AP CASA CAIADA",
    EMPRESA_VIP: "POSTO VIP",
    EMPRESA_REAL_DOZE: "POSTO REAL / DOZE",
}


class FuelRow(BaseModel):
    produto: str = ""
    empresa_codigo: int = 0
    nome_filial: str = ""
    litros: float = 0.0
    valor: float = 0.0
    transacoes: int = 0
    percentual_rede: float = 0.0


class MargemRow(BaseModel):
    empresa_codigo: int = 0
    nome: str = ""
    litros: float = 0.0
    valor: float = 0.0
    receita_por_litro: float = 0.0


class FuelVolumetryResult(BaseModel):
    success: bool = True
    fromCache: bool = False
    fonte: str = ""
    latencyMs: float = 0.0
    periodo: dict[str, str] = Field(default_factory=dict)
    empresaCodigo: int | None = None
    total_litros: float = 0.0
    total_valor: float = 0.0
    total_transacoes: int = 0
    por_produto: list[FuelRow] = Field(default_factory=list)
    por_filial: list[FuelRow] = Field(default_factory=list)
    faturamento_por_litro: list[MargemRow] = Field(default_factory=list)
    observacoes: list[str] = Field(default_factory=list)

    def as_bloco_compat(self) -> dict[str, Any]:
        """Shape compatível com a UI que lê ExecutiveReport.bloco_1 / bloco_3."""
        return {
            "gerado_em": date.today().isoformat(),
            "periodo_principal": self.periodo,
            "filiais_monitoradas": [
                {"empresa_codigo": k, "nome": v} for k, v in FILIAIS.items()
            ],
            "bloco_1_combustiveis": {
                "titulo": "Pista & Volumetria",
                "status": "OK",
                "periodo": self.periodo,
                "resumo": {
                    "total_litros": self.total_litros,
                    "total_valor": self.total_valor,
                    "total_transacoes": self.total_transacoes,
                    "por_produto": [r.model_dump() for r in self.por_produto],
                    "por_filial": [r.model_dump() for r in self.por_filial],
                    "observacao": " · ".join(self.observacoes),
                },
                "ranking_filial": [
                    {
                        "empresa_codigo": f.empresa_codigo,
                        "nome": f.nome_filial,
                        "litros": f.litros,
                        "valor": f.valor,
                        "transacoes": f.transacoes,
                        "participacao_rede_pct": f.percentual_rede,
                    }
                    for f in self.por_filial
                ],
            },
            "bloco_3_margens": {
                "periodo": self.periodo,
                "faturamento_por_litro": [m.model_dump() for m in self.faturamento_por_litro],
            },
            "fonte": self.fonte,
            "fromCache": self.fromCache,
            "latencyMs": self.latencyMs,
            "observacoes": self.observacoes,
        }


def _round3(v: float) -> float:
    return round(float(v or 0), 3)


def _round2(v: float) -> float:
    return round(float(v or 0), 2)


def _build_from_buckets(
    by_prod: dict[tuple[int, str], dict[str, float]],
    by_filial: dict[int, dict[str, float]],
) -> tuple[list[FuelRow], list[FuelRow], list[MargemRow], float, float, int]:
    total_l = sum(v["litros"] for v in by_filial.values())
    total_v = sum(v["valor"] for v in by_filial.values())
    total_t = int(sum(v["transacoes"] for v in by_filial.values()))

    por_produto: list[FuelRow] = []
    for (emp, prod), vals in sorted(by_prod.items(), key=lambda x: -x[1]["valor"]):
        pct = (vals["valor"] / total_v * 100) if total_v > 0 else 0.0
        por_produto.append(
            FuelRow(
                produto=prod,
                empresa_codigo=emp,
                nome_filial=FILIAIS.get(emp, f"Filial {emp}"),
                litros=_round3(vals["litros"]),
                valor=_round2(vals["valor"]),
                transacoes=int(vals["transacoes"]),
                percentual_rede=round(pct, 2),
            )
        )

    por_filial: list[FuelRow] = []
    margens: list[MargemRow] = []
    for emp, vals in sorted(by_filial.items(), key=lambda x: -x[1]["litros"]):
        pct = (vals["valor"] / total_v * 100) if total_v > 0 else 0.0
        litros = _round3(vals["litros"])
        valor = _round2(vals["valor"])
        nome = FILIAIS.get(emp, f"Filial {emp}")
        por_filial.append(
            FuelRow(
                produto="COMBUSTÍVEL (total)",
                empresa_codigo=emp,
                nome_filial=nome,
                litros=litros,
                valor=valor,
                transacoes=int(vals["transacoes"]),
                percentual_rede=round(pct, 2),
            )
        )
        margens.append(
            MargemRow(
                empresa_codigo=emp,
                nome=nome,
                litros=litros,
                valor=valor,
                receita_por_litro=_round2(valor / litros) if litros > 0 else 0.0,
            )
        )

    return (
        por_produto,
        por_filial,
        margens,
        _round3(total_l),
        _round2(total_v),
        total_t,
    )


class FuelVolumetryService:
    """Agrega volumetria pista com política D0=RAM / histórico=DB local."""

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None = None,
    ) -> FuelVolumetryResult:
        t0 = time.perf_counter()
        empresa = resolve_empresa_codigo(empresa_codigo)
        hoje = date.today().isoformat()
        ontem = (date.today() - timedelta(days=1)).isoformat()
        obs: list[str] = [
            f"empresa={'TODAS' if empresa is None else empresa}",
        ]

        single = data_inicial == data_final
        is_d0 = single and data_inicial == hoje
        is_d1 = single and data_inicial == ontem

        by_prod: dict[tuple[int, str], dict[str, float]] = defaultdict(
            lambda: {"litros": 0.0, "valor": 0.0, "transacoes": 0.0}
        )
        by_filial: dict[int, dict[str, float]] = defaultdict(
            lambda: {"litros": 0.0, "valor": 0.0, "transacoes": 0.0}
        )
        fonte = ""
        from_cache = False

        if is_d0:
            self._ingest_ram(by_prod, by_filial, empresa, obs)
            fonte = "pista_cache_service+RAM"
            from_cache = True
        elif is_d1:
            n = await self._ingest_db(by_prod, by_filial, data_inicial, data_final, empresa, obs)
            fonte = "sales_daily_summary+DB"
            if n == 0:
                await self._ingest_abastecimento(
                    by_prod, by_filial, data_inicial, data_final, empresa, obs
                )
                fonte = "sales_daily_summary(vazio)+ABASTECIMENTO"
        else:
            await self._ingest_db(by_prod, by_filial, data_inicial, data_final, empresa, obs)
            if data_inicial <= hoje <= data_final:
                self._ingest_ram(by_prod, by_filial, empresa, obs)
                fonte = "sales_daily_summary+pista_cache_RAM"
                from_cache = True
            else:
                fonte = "sales_daily_summary+DB"
            if not by_filial:
                await self._ingest_abastecimento(
                    by_prod, by_filial, data_inicial, data_final, empresa, obs
                )
                fonte = "ABASTECIMENTO(fallback)"

        por_produto, por_filial, margens, tot_l, tot_v, tot_t = _build_from_buckets(
            by_prod, by_filial
        )
        latency = round((time.perf_counter() - t0) * 1000.0, 3)
        if is_d0 and latency >= 50:
            obs.append(f"ALERTA latência D0={latency}ms (meta <50ms)")
        if is_d1 and latency >= 200:
            obs.append(f"ALERTA latência D-1={latency}ms (meta <200ms)")
        obs.append(f"fonte={fonte}")

        return FuelVolumetryResult(
            fromCache=from_cache,
            fonte=fonte,
            latencyMs=latency,
            periodo={"inicio": data_inicial, "fim": data_final},
            empresaCodigo=empresa,
            total_litros=tot_l,
            total_valor=tot_v,
            total_transacoes=tot_t,
            por_produto=por_produto,
            por_filial=por_filial,
            faturamento_por_litro=margens,
            observacoes=obs,
        )

    def _ingest_ram(
        self,
        by_prod: dict[tuple[int, str], dict[str, float]],
        by_filial: dict[int, dict[str, float]],
        empresa: int | None,
        obs: list[str],
    ) -> int:
        from src.services.pista_cache_service import get_pista_cache

        snap = get_pista_cache().get_snapshot()
        items = list(snap.baixados or [])
        if not items:
            obs.append("Cache RAM pista vazio — aguardando PistaSyncWorker")
            return 0
        n = 0
        for it in items:
            emp = int(getattr(it, "idEmpresa", 0) or 0)
            if empresa is not None and emp != empresa:
                continue
            if emp <= 0:
                continue
            litros = float(getattr(it, "litros", 0) or 0)
            valor = float(getattr(it, "valorTotal", 0) or 0)
            if litros <= 0 and valor <= 0:
                continue
            prod_cod = str(getattr(it, "idProduto", None) or "")
            nome = str(getattr(it, "descricaoProduto", None) or "").strip()
            produto = nome or rotulo_combustivel(prod_cod) or f"Produto {prod_cod or '?'}"
            key = (emp, produto)
            by_prod[key]["litros"] += litros
            by_prod[key]["valor"] += valor
            by_prod[key]["transacoes"] += 1
            by_filial[emp]["litros"] += litros
            by_filial[emp]["valor"] += valor
            by_filial[emp]["transacoes"] += 1
            n += 1
        obs.append(f"RAM data_ref={snap.data_ref} baixados_filtrados={n}")
        return n

    async def _ingest_db(
        self,
        by_prod: dict[tuple[int, str], dict[str, float]],
        by_filial: dict[int, dict[str, float]],
        data_inicial: str,
        data_final: str,
        empresa: int | None,
        obs: list[str],
    ) -> int:
        try:
            from src.infrastructure.config.database import AsyncSessionLocal
            from src.models.sales_daily_summary_model import SalesDailySummaryModel

            start = date.fromisoformat(data_inicial)
            end = date.fromisoformat(data_final)
            hoje = date.today()
            if end >= hoje:
                end = hoje - timedelta(days=1)
            if start > end:
                obs.append("Período sem dias históricos locais (apenas D0)")
                return 0

            async with AsyncSessionLocal() as session:
                stmt = select(SalesDailySummaryModel).where(
                    SalesDailySummaryModel.data_referencia >= start,
                    SalesDailySummaryModel.data_referencia <= end,
                )
                if empresa is not None:
                    stmt = stmt.where(SalesDailySummaryModel.empresa_codigo == empresa)
                result = await session.execute(stmt)
                rows = list(result.scalars().all())

            n = 0
            for row in rows:
                emp = int(row.empresa_codigo)
                litros = float(row.litros_vendidos or 0)
                valor = float(row.faturamento_bruto or 0)
                if litros <= 0 and valor <= 0:
                    continue
                produto = (
                    str(row.nome_produto or "").strip()
                    or rotulo_combustivel(str(row.codigo_produto_webposto or ""))
                    or f"Produto {row.codigo_produto_webposto}"
                )
                key = (emp, produto)
                by_prod[key]["litros"] += litros
                by_prod[key]["valor"] += valor
                tx = int(row.quantidade_abastecimentos or 0) or 1
                by_prod[key]["transacoes"] += tx
                by_filial[emp]["litros"] += litros
                by_filial[emp]["valor"] += valor
                by_filial[emp]["transacoes"] += tx
                n += 1
            obs.append(f"DB sales_daily_summary rows={n} periodo={start}..{end}")
            return n
        except Exception as exc:
            LOGGER.warning("fuel_volumetry DB falhou: %s", exc)
            obs.append(f"DB indisponível: {exc}")
            return 0

    async def _ingest_abastecimento(
        self,
        by_prod: dict[tuple[int, str], dict[str, float]],
        by_filial: dict[int, dict[str, float]],
        data_inicial: str,
        data_final: str,
        empresa: int | None,
        obs: list[str],
    ) -> int:
        """Fallback degradado — nunca usado em D0 (meta RAM)."""
        try:
            from src.gateway.shared_client import get_webposto_client
            from src.services.abastecimento_service import AbastecimentoService

            svc = AbastecimentoService(get_webposto_client())
            resp = await svc.get_periodo(data_inicial, data_final, empresa_codigo=empresa)
            data = resp.data if resp.success else None
            rows: list[dict[str, Any]] = []
            if isinstance(data, dict):
                for k in ("resultados", "items", "data"):
                    if isinstance(data.get(k), list):
                        rows = [x for x in data[k] if isinstance(x, dict)]
                        break
            elif isinstance(data, list):
                rows = [x for x in data if isinstance(x, dict)]

            n = 0
            for row in rows:
                emp = int(row.get("empresaCodigo") or 0)
                if empresa is not None and emp != empresa:
                    continue
                litros = float(row.get("quantidade") or row.get("litros") or 0)
                valor = float(row.get("valorTotal") or row.get("valor") or 0)
                if litros <= 0 and valor <= 0:
                    continue
                cod = str(row.get("codigoProduto") or row.get("produtoCodigo") or "")
                nome = str(
                    row.get("descricaoProduto") or row.get("nomeProduto") or ""
                ).strip()
                produto = nome or rotulo_combustivel(cod) or f"Produto {cod or '?'}"
                key = (emp, produto)
                by_prod[key]["litros"] += litros
                by_prod[key]["valor"] += valor
                by_prod[key]["transacoes"] += 1
                by_filial[emp]["litros"] += litros
                by_filial[emp]["valor"] += valor
                by_filial[emp]["transacoes"] += 1
                n += 1
            obs.append(f"Fallback ABASTECIMENTO rows={n}")
            return n
        except Exception as exc:
            LOGGER.warning("fuel_volumetry ABASTECIMENTO fallback falhou: %s", exc)
            obs.append(f"Fallback ABASTECIMENTO falhou: {exc}")
            return 0


_svc: FuelVolumetryService | None = None


def get_fuel_volumetry_service() -> FuelVolumetryService:
    global _svc
    if _svc is None:
        _svc = FuelVolumetryService()
    return _svc
