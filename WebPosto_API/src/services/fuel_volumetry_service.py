"""Pista & Volumetria — D0 = cache RAM (<50ms), D-1/histórico = sales_daily_summary (<200ms).

Hot-path da Central de Relatórios: budget HTTP < 800ms.
Nunca varre ABASTECIMENTO paginado sem teto de tempo no request.
"""

from __future__ import annotations

import asyncio
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

# Budget da Central de Relatórios (aceite < 1.5s UI / < 800ms serviço)
_HTTP_BUDGET_S = 0.75
_RESP_CACHE: dict[str, tuple[float, "FuelVolumetryResult"]] = {}
_RESP_TTL_S = 60.0
_BACKFILL_KEYS: set[str] = set()


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


def _empty_buckets() -> tuple[
    dict[tuple[int, str], dict[str, float]],
    dict[int, dict[str, float]],
]:
    return (
        defaultdict(lambda: {"litros": 0.0, "valor": 0.0, "transacoes": 0.0}),
        defaultdict(lambda: {"litros": 0.0, "valor": 0.0, "transacoes": 0.0}),
    )


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


def _targets(empresa: int | None) -> list[int]:
    if empresa is not None:
        return [int(empresa)]
    return [EMPRESA_CASA_CAIADA, EMPRESA_VIP, EMPRESA_REAL_DOZE]


class FuelVolumetryService:
    """Agrega volumetria pista com política D0=RAM / histórico=DB local + fallbacks rápidos."""

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None = None,
    ) -> FuelVolumetryResult:
        t0 = time.perf_counter()
        empresa = resolve_empresa_codigo(empresa_codigo)
        cache_key = f"{data_inicial}|{data_final}|{empresa or 'all'}"
        now = time.monotonic()
        hit = _RESP_CACHE.get(cache_key)
        if hit and (now - hit[0]) < _RESP_TTL_S:
            cached = hit[1].model_copy(deep=True)
            cached.fromCache = True
            cached.latencyMs = round((time.perf_counter() - t0) * 1000.0, 3)
            cached.observacoes = list(cached.observacoes) + ["resp_cache_hit"]
            return cached

        hoje = date.today().isoformat()
        ontem = (date.today() - timedelta(days=1)).isoformat()
        obs: list[str] = [
            f"empresa={'TODAS' if empresa is None else empresa}",
        ]

        single = data_inicial == data_final
        is_d0 = single and data_inicial == hoje
        is_d1 = single and data_inicial == ontem

        by_prod, by_filial = _empty_buckets()
        fonte = ""
        from_cache = False

        if is_d0:
            self._ingest_ram(by_prod, by_filial, empresa, obs)
            fonte = "pista_cache_service+RAM"
            from_cache = True
        elif is_d1:
            fonte, from_cache = await self._build_d1(
                by_prod, by_filial, data_inicial, data_final, empresa, obs
            )
        else:
            await self._ingest_db(by_prod, by_filial, data_inicial, data_final, empresa, obs)
            if data_inicial <= hoje <= data_final:
                self._ingest_ram(by_prod, by_filial, empresa, obs)
                fonte = "sales_daily_summary+pista_cache_RAM"
                from_cache = True
            else:
                fonte = "sales_daily_summary+DB"
            if not by_filial:
                from src.services.webposto.offline_mode import webposto_offline_mode

                if not webposto_offline_mode():
                    await self._ingest_abastecimento_budgeted(
                        by_prod, by_filial, data_inicial, data_final, empresa, obs
                    )
                    if by_filial:
                        fonte = "ABASTECIMENTO(budget)"
                    else:
                        n_cx = await self._ingest_fechamento_turno(
                            by_prod, by_filial, data_inicial, empresa, obs
                        )
                        if n_cx:
                            fonte = "fechamento_turno(fallback)"
                else:
                    n_cx = await self._ingest_fechamento_turno(
                        by_prod, by_filial, data_inicial, empresa, obs
                    )
                    if n_cx:
                        fonte = "fechamento_turno(fallback)"

        por_produto, por_filial, margens, tot_l, tot_v, tot_t = _build_from_buckets(
            by_prod, by_filial
        )
        latency = round((time.perf_counter() - t0) * 1000.0, 3)
        if is_d0 and latency >= 50:
            obs.append(f"ALERTA latência D0={latency}ms (meta <50ms)")
        if is_d1 and latency >= 800:
            obs.append(f"ALERTA latência D-1={latency}ms (meta <800ms)")
        obs.append(f"fonte={fonte}")

        result = FuelVolumetryResult(
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
        # Cacheia inclusive zeros só se veio de RAM/DB estável — evita travar zeros de miss
        if tot_l > 0 or tot_v > 0 or from_cache:
            _RESP_CACHE[cache_key] = (time.monotonic(), result)
        return result

    async def _build_d1(
        self,
        by_prod: dict[tuple[int, str], dict[str, float]],
        by_filial: dict[int, dict[str, float]],
        data_inicial: str,
        data_final: str,
        empresa: int | None,
        obs: list[str],
    ) -> tuple[str, bool]:
        """D-1: DB → RAM (se data_ref=D-1) → fechamento turno → ABASTECIMENTO budgetado."""
        n = await self._ingest_db(by_prod, by_filial, data_inicial, data_final, empresa, obs)
        if n > 0:
            return "sales_daily_summary+DB", False

        obs.append("sales_daily_summary(vazio) — fallback rápido (sem varredura pesada)")
        # Backfill assíncrono aquece o DB; NÃO bloqueia o HTTP no ABASTECIMENTO paginado
        self._schedule_d1_backfill(data_inicial)

        # pista_cache ainda pode cobrir D-1 se o dia não rolou / stale preservado
        from src.services.pista_cache_service import get_pista_cache

        snap = get_pista_cache().get_snapshot()
        if snap.data_ref == data_inicial and (snap.baixados or snap.pendentes):
            self._ingest_ram(by_prod, by_filial, empresa, obs)
            if by_filial:
                return "pista_cache_service+RAM(D-1)", True

        n_cx = await self._ingest_fechamento_turno(
            by_prod, by_filial, data_inicial, empresa, obs
        )
        if n_cx > 0 and by_filial:
            return "fechamento_turno(fallback)", False

        from src.services.webposto.offline_mode import webposto_offline_mode

        if webposto_offline_mode():
            return "sales_daily_summary(vazio)+sem_dados", False

        # Último recurso: 1 página/filial em paralelo com timeout de socket curto
        await self._ingest_abastecimento_budgeted(
            by_prod, by_filial, data_inicial, data_final, empresa, obs
        )
        if by_filial:
            return "sales_daily_summary(vazio)+ABASTECIMENTO(budget)", False
        return "sales_daily_summary(vazio)+sem_dados", False

    def _schedule_d1_backfill(self, day: str) -> None:
        """Dispara sync_day em background para aquecer sales_daily_summary."""
        from src.services.webposto.offline_mode import webposto_offline_mode

        if webposto_offline_mode():
            return
        key = f"d1:{day}"
        if key in _BACKFILL_KEYS:
            return
        _BACKFILL_KEYS.add(key)

        async def _run() -> None:
            try:
                from src.services.data_sync_service import DataSyncService

                svc = DataSyncService()
                target = date.fromisoformat(day)
                await asyncio.gather(
                    *[svc.sync_day(code, target) for code in FILIAIS],
                    return_exceptions=True,
                )
                # Invalida cache de resposta para próximo hit usar DB
                for emp in list(FILIAIS) + [None]:
                    _RESP_CACHE.pop(f"{day}|{day}|{emp or 'all'}", None)
                LOGGER.info("fuel_volumetry backfill D-1 ok day=%s", day)
            except Exception:
                LOGGER.exception("fuel_volumetry backfill D-1 falhou day=%s", day)
            finally:
                _BACKFILL_KEYS.discard(key)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_run())
        except RuntimeError:
            _BACKFILL_KEYS.discard(key)

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

    async def _ingest_fechamento_turno(
        self,
        by_prod: dict[tuple[int, str], dict[str, float]],
        by_filial: dict[int, dict[str, float]],
        day: str,
        empresa: int | None,
        obs: list[str],
    ) -> int:
        """Fallback: totais de fechamento de turno (bico) — evita zerar faturamento."""
        n = 0
        try:
            from src.services.cashier_audit_service import get_cashier_audit_service

            store = get_cashier_audit_service().get_store()
            fechamentos = list(store.fechamentos or ())
            if store.data_ref == day and fechamentos:
                for f in fechamentos:
                    emp = int(f.postoCodigo or 0)
                    if empresa is not None and emp != empresa:
                        continue
                    if emp <= 0:
                        continue
                    valor = float(f.faturamentoBico or 0)
                    if valor <= 0:
                        continue
                    # litros: se já houver da fonte budgetada, não sobrescreve — só preenche valor
                    if by_filial[emp]["valor"] <= 0:
                        by_filial[emp]["valor"] += valor
                        by_filial[emp]["transacoes"] += int(f.qtdAbastecimentos or 0) or 1
                        key = (emp, "COMBUSTÍVEL (fechamento turno)")
                        by_prod[key]["valor"] += valor
                        by_prod[key]["transacoes"] += int(f.qtdAbastecimentos or 0) or 1
                        n += 1
                if n:
                    obs.append(f"fechamento_turno RAM data_ref={day} turnos={n}")
                    return n

            # CAIXA do dia (budget curto) — soma valor informado/apresentado por filial
            caixas = await asyncio.wait_for(self._fetch_caixas(day, day), timeout=0.35)
            by_emp_val: dict[int, float] = defaultdict(float)
            by_emp_tx: dict[int, int] = defaultdict(int)
            for cx in caixas:
                emp = int(cx.get("empresaCodigo") or 0)
                if empresa is not None and emp != empresa:
                    continue
                if emp not in FILIAIS:
                    continue
                valor = float(
                    cx.get("valorInformado")
                    or cx.get("valorApresentado")
                    or cx.get("valorFechamento")
                    or cx.get("totalInformado")
                    or cx.get("valorTotal")
                    or 0
                )
                litros = float(
                    cx.get("litros")
                    or cx.get("volumeLitros")
                    or cx.get("quantidadeLitros")
                    or 0
                )
                if valor <= 0 and litros <= 0:
                    continue
                by_emp_val[emp] += valor
                by_emp_tx[emp] += 1
                if litros > 0:
                    by_filial[emp]["litros"] += litros
                    key = (emp, "COMBUSTÍVEL (fechamento turno)")
                    by_prod[key]["litros"] += litros
            for emp, valor in by_emp_val.items():
                if by_filial[emp]["valor"] > 0:
                    continue
                by_filial[emp]["valor"] += valor
                by_filial[emp]["transacoes"] += by_emp_tx[emp]
                key = (emp, "COMBUSTÍVEL (fechamento turno)")
                by_prod[key]["valor"] += valor
                by_prod[key]["transacoes"] += by_emp_tx[emp]
                n += 1
            if n:
                obs.append(f"fechamento_turno CAIXA day={day} filiais={n}")
            else:
                obs.append(f"fechamento_turno sem dados day={day}")
            return n
        except asyncio.TimeoutError:
            obs.append("fechamento_turno timeout (<350ms)")
            return 0
        except Exception as exc:
            LOGGER.warning("fuel_volumetry fechamento_turno falhou: %s", exc)
            obs.append(f"fechamento_turno falhou: {exc}")
            return 0

    @staticmethod
    async def _fetch_caixas(inicio: str, fim: str) -> list[dict[str, Any]]:
        from src.gateway.shared_client import get_webposto_client
        from src.services.caixa_service import CaixaService

        resp = await CaixaService(get_webposto_client()).get_caixa(inicio, fim)
        if not resp.success:
            return []
        data = resp.data
        if isinstance(data, dict):
            rows = data.get("dados") or data.get("data") or data.get("resultados") or []
        elif isinstance(data, list):
            rows = data
        else:
            rows = []
        return [r for r in rows if isinstance(r, dict)]

    async def _ingest_abastecimento_budgeted(
        self,
        by_prod: dict[tuple[int, str], dict[str, float]],
        by_filial: dict[int, dict[str, float]],
        data_inicial: str,
        data_final: str,
        empresa: int | None,
        obs: list[str],
    ) -> int:
        """Multi-station paralelo com teto de tempo — nunca bloqueia 11s."""
        targets = _targets(empresa)
        deadline = time.monotonic() + _HTTP_BUDGET_S

        async def _one(code: int) -> list[dict[str, Any]]:
            remaining = deadline - time.monotonic()
            if remaining <= 0.05:
                return []
            try:
                return await asyncio.wait_for(
                    self._fetch_abastecimento_pages(
                        data_inicial, data_final, code, deadline
                    ),
                    timeout=remaining,
                )
            except (asyncio.TimeoutError, Exception) as exc:
                LOGGER.warning(
                    "ABASTECIMENTO budget empresa=%s: %s", code, exc
                )
                return []

        results = await asyncio.gather(*[_one(c) for c in targets])
        cleared: set[int] = set()
        n = 0
        for rows in results:
            for row in rows:
                emp = int(row.get("empresaCodigo") or row.get("empresa") or 0)
                if empresa is not None and emp != empresa:
                    continue
                if emp <= 0:
                    continue
                litros = float(row.get("quantidade") or row.get("litros") or 0)
                valor = float(row.get("valorTotal") or row.get("valor") or 0)
                if litros <= 0 and valor <= 0:
                    continue
                # Substitui placeholder do fechamento por linhas reais de produto
                placeholder = (emp, "COMBUSTÍVEL (fechamento turno)")
                if emp not in cleared and placeholder in by_prod:
                    by_filial[emp]["litros"] = 0.0
                    by_filial[emp]["valor"] = 0.0
                    by_filial[emp]["transacoes"] = 0.0
                    del by_prod[placeholder]
                    cleared.add(emp)

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
        elapsed = round((_HTTP_BUDGET_S - max(0.0, deadline - time.monotonic())) * 1000)
        obs.append(
            f"ABASTECIMENTO budget={_HTTP_BUDGET_S * 1000:.0f}ms filiais={len(targets)} rows={n} ~{elapsed}ms"
        )
        return n

    async def _fetch_abastecimento_pages(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int,
        deadline: float,
        *,
        max_pages: int = 1,
    ) -> list[dict[str, Any]]:
        """1 página/filial com timeout de socket curto (não usa client longo do gateway)."""
        import httpx

        from src.core.config import resolve_company_api_key
        from src.gateway.shared_client import get_webposto_client

        if time.monotonic() >= deadline:
            return []
        remaining = max(0.15, deadline - time.monotonic())
        base = get_webposto_client()
        api_key = resolve_company_api_key(int(empresa_codigo)) or (
            base._api_keys[0] if getattr(base, "_api_keys", None) else None
        )
        if not api_key:
            return []
        params = {
            "CHAVE": api_key,
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "empresaCodigo": str(empresa_codigo),
        }
        url = f"{base.config.webposto_base_url.rstrip('/')}/INTEGRACAO/ABASTECIMENTO"
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(remaining, connect=min(0.25, remaining))
            ) as client:
                resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return []
            raw = resp.json()
            batch: list[dict] = []
            if isinstance(raw, dict):
                batch = raw.get("dados") or raw.get("data") or raw.get("resultados") or []
            elif isinstance(raw, list):
                batch = raw
            return [
                row
                for row in batch
                if isinstance(row, dict)
                and int(row.get("empresaCodigo") or row.get("empresa") or 0)
                == int(empresa_codigo)
            ][:200]
        except Exception as exc:
            LOGGER.warning("ABASTECIMENTO fast-page empresa=%s: %s", empresa_codigo, exc)
            return []


_svc: FuelVolumetryService | None = None


def get_fuel_volumetry_service() -> FuelVolumetryService:
    global _svc
    if _svc is None:
        _svc = FuelVolumetryService()
    return _svc
