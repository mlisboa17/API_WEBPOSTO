from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any

from src.services.analytics_service import AnalyticsService
from src.services.data_quality_service import DataQualityFilters, DataQualityService
from src.services.fuel_analytics_service import FuelAnalyticsFilters, FuelAnalyticsService
from src.services.fuel_kpi_engine import FuelKpiEngine
from src.services.multiselect_utils import parse_empresa_codigos
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService
from src.services.snapshot_store import SnapshotStore

EXECUTIVE_SNAPSHOT_TTL_SECONDS = 5 * 60

_parse_empresa_codigos = parse_empresa_codigos


def build_snapshot_key(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
    from src.services.multiselect_utils import empresa_snapshot_suffix

    suffix = empresa_snapshot_suffix(empresa_codigo)
    return f"{data_inicial}:{data_final}:{suffix}"


def _safe_filename(key: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", key)


def _to_number(value: Any) -> float:
    try:
        return float(str(value or 0).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _aggregate_kpis(items: list[dict[str, Any]], data_inicial: str, data_final: str) -> dict[str, Any]:
    faturamento = sum(_to_number(item.get("faturamento")) for item in items)
    despesas = sum(_to_number(item.get("despesasTotais")) for item in items)
    resultado = sum(_to_number(item.get("resultadoOperacional")) for item in items)
    qtd_vendas = sum(_to_number(item.get("qtdVendas")) for item in items)
    qtd_clientes = sum(_to_number(item.get("qtdClientes")) for item in items)
    estoque_total = sum(_to_number(item.get("estoqueTotal")) for item in items)
    margem = (resultado / faturamento * 100) if faturamento > 0 else 0.0
    ticket = (faturamento / qtd_vendas) if qtd_vendas > 0 else 0.0
    return {
        "faturamento": str(faturamento),
        "despesasTotais": str(despesas),
        "resultadoOperacional": str(resultado),
        "margemPct": str(margem),
        "ticketMedio": str(ticket),
        "qtdVendas": int(qtd_vendas),
        "qtdClientes": int(qtd_clientes),
        "estoqueTotal": str(estoque_total),
        "periodoInicial": data_inicial,
        "periodoFinal": data_final,
        "origemSistema": "webpostos",
        "lineage": {"aggregate": "multiselect_backend"},
    }


def _aggregate_dre(items: list[dict[str, Any]], data_inicial: str, data_final: str) -> dict[str, Any]:
    receitas = sum(_to_number(item.get("receitas")) for item in items)
    custos = sum(_to_number(item.get("custosProduto")) for item in items)
    outras = sum(_to_number(item.get("outrasDespesas")) for item in items)
    resultado = sum(_to_number(item.get("resultadoOperacional")) for item in items)
    margem = (resultado / receitas * 100) if receitas > 0 else 0.0
    return {
        "receitas": str(receitas),
        "custosProduto": str(custos),
        "outrasDespesas": str(outras),
        "resultadoOperacional": str(resultado),
        "margemPct": str(margem),
        "validacaoOk": True,
        "divergencia": "0",
        "periodoInicial": data_inicial,
        "periodoFinal": data_final,
        "agrupamento": [],
        "formula": "receitas - custosProduto - outrasDespesas = resultadoOperacional",
        "lineage": {"aggregate": "multiselect_backend"},
    }


def _aggregate_data_quality(items: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {"totalRegistros": 0.0, "validos": 0.0, "invalidos": 0.0}
    issues = {"duplicados": 0.0, "valoresInvalidos": 0.0}
    for item in items:
        data_summary = item.get("summary") or {}
        data_issues = item.get("issues") or {}
        summary["totalRegistros"] += _to_number(data_summary.get("totalRegistros"))
        summary["validos"] += _to_number(data_summary.get("validos"))
        summary["invalidos"] += _to_number(data_summary.get("invalidos"))
        issues["duplicados"] += _to_number(data_issues.get("duplicados"))
        issues["valoresInvalidos"] += _to_number(data_issues.get("valoresInvalidos"))
    score = round((summary["validos"] / summary["totalRegistros"]) * 100, 2) if summary["totalRegistros"] > 0 else 0.0
    status = "ok" if score >= 95 else "warning" if score >= 80 else "danger"
    return {"score": score, "status": status, "summary": summary, "issues": issues}


def build_network_coverage(companies: list[dict[str, Any]]) -> dict[str, Any]:
    def _status(company: dict[str, Any]) -> str:
        return str(company.get("status") or "").strip().upper()

    def _status_operacional(company: dict[str, Any]) -> str:
        raw = str(company.get("statusOperacional") or "").strip().upper()
        if raw:
            return raw
        status = _status(company)
        if status == "INATIVA":
            return "INATIVA"
        if status == "PENDENTE_IDENTIFICACAO":
            return "PENDENTE_IDENTIFICACAO"
        return "ATIVA"

    def _has_operational_data(company: dict[str, Any]) -> bool:
        explicit = company.get("possuiDadosOperacionais")
        if explicit is not None:
            return bool(explicit)
        detail = str(company.get("statusDetalhado") or company.get("status_detalhado") or "").strip().lower()
        return detail not in {"token insuficiente", "pendente identificacao", "inativa"}

    filiais_totais = len(companies)
    filiais_confirmadas = [c for c in companies if _status(c) in {"CONFIRMADA", "ATIVA"}]
    filiais_pendentes = [c for c in companies if _status(c) == "PENDENTE_IDENTIFICACAO"]
    filiais_inativas = [c for c in companies if _status(c) == "INATIVA"]
    filiais_ativas = [c for c in filiais_confirmadas if _status_operacional(c) == "ATIVA"]
    filiais_com_dados = [c for c in filiais_ativas if _has_operational_data(c)]
    filiais_sem_dados = [c for c in filiais_ativas if not _has_operational_data(c)]

    def _is_token_limited(company: dict[str, Any]) -> bool:
        detail = str(company.get("statusDetalhado") or company.get("status_detalhado") or "").lower()
        return "token" in detail

    def _has_fuel_data(company: dict[str, Any]) -> bool:
        explicit = company.get("possuiDadosCombustivel")
        if explicit is not None:
            return bool(explicit)
        cod = company.get("empresaCodigo") or company.get("codWeb")
        return cod in {5555, 11495} and _has_operational_data(company)

    def _is_unsynced(company: dict[str, Any]) -> bool:
        if company.get("apiEncontrada") is False:
            return True
        detail = str(company.get("statusDetalhado") or "").lower()
        return "sincroniz" in detail or "pendente identificacao" in detail

    filiais_sem_token = [c for c in filiais_ativas if _is_token_limited(c)]
    filiais_com_combustivel = [c for c in filiais_ativas if _has_fuel_data(c)]
    filiais_sem_sincronizacao = [c for c in companies if _is_unsynced(c)]

    num_totais = filiais_totais
    num_confirmadas = len(filiais_confirmadas)
    num_pendentes = len(filiais_pendentes)
    num_ativas = len(filiais_ativas)
    num_inativas = len(filiais_inativas)
    num_com_dados = len(filiais_com_dados)
    num_sem_dados = len(filiais_sem_dados)

    num_sem_token = len(filiais_sem_token)
    num_com_combustivel = len(filiais_com_combustivel)
    num_sem_sincronizacao = len(filiais_sem_sincronizacao)

    coverage_confirmed_percent = round((num_confirmadas / num_totais) * 100, 2) if num_totais > 0 else 0.0
    coverage_operational_percent = round((num_com_dados / num_ativas) * 100, 2) if num_ativas > 0 else 0.0
    fuel_coverage_percent = round((num_com_combustivel / num_ativas) * 100, 2) if num_ativas > 0 else 0.0
    network_health = coverage_operational_percent
    indice_cobertura_rede = round(
        (coverage_operational_percent * 0.5) + (fuel_coverage_percent * 0.3) + (coverage_confirmed_percent * 0.2),
        2,
    )

    return {
        "filiaisTotais": num_totais,
        "filiaisConfirmadas": num_confirmadas,
        "filiaisPendentesIdentificacao": num_pendentes,
        "filiaisAtivas": num_ativas,
        "filiaisInativas": num_inativas,
        "filiaisComDados": num_com_dados,
        "filiaisSemDados": num_sem_dados,
        "filiaisComCombustivel": num_com_combustivel,
        "filiaisSemToken": num_sem_token,
        "filiaisSemSincronizacao": num_sem_sincronizacao,
        "coveragePercent": coverage_operational_percent,
        "coverageConfirmedPercent": coverage_confirmed_percent,
        "coverageOperationalPercent": coverage_operational_percent,
        "fuelCoveragePercent": fuel_coverage_percent,
        "networkHealth": network_health,
        "indiceCoberturaRede": indice_cobertura_rede,
        "mensagemDiretoria": (
            "O software LOGOS SPACE esta operacional. "
            "A limitacao atual e a integracao WebPosto (token e endpoints por filial)."
        ),
        "filiais": companies,
    }


class ExecutiveSnapshotService:
    def __init__(
        self,
        overview: NetworkFinancialOverviewService,
        analytics: AnalyticsService,
        data_quality: DataQualityService,
        fuel_analytics: FuelAnalyticsService,
        fuel_kpi_engine: FuelKpiEngine,
        output_dir: str | Path = "snapshots/executive",
    ) -> None:
        self._overview = overview
        self._analytics = analytics
        self._data_quality = data_quality
        self._fuel_analytics = fuel_analytics
        self._fuel_kpi_engine = fuel_kpi_engine
        self._store = SnapshotStore(output_dir, EXECUTIVE_SNAPSHOT_TTL_SECONDS)
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    def get_snapshot(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        key = build_snapshot_key(data_inicial, data_final, empresa_codigo)
        stored = self._store.load(key)
        if stored:
            return {
                "fromSnapshot": True,
                "lastUpdated": stored.get("lastUpdated"),
                "kpis": stored.get("kpis"),
                "dre": stored.get("dre"),
                "coverage": stored.get("coverage"),
                "dataQuality": stored.get("dataQuality"),
                "fuel": stored.get("fuel"),
                "warnings": stored.get("warnings") or [],
            }

        return {
            "fromSnapshot": False,
            "lastUpdated": None,
            "kpis": None,
            "dre": None,
            "coverage": None,
            "dataQuality": None,
            "fuel": None,
            "warnings": [],
        }

    def is_running(self, key: str) -> bool:
        return key in self._running

    async def collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        centro_custo: str | None = None,
        tipo_despesa: str | None = None,
    ) -> dict[str, Any]:
        warnings: list[str] = []
        empresa_codes = _parse_empresa_codigos(empresa_codigo)

        async def _fetch_kpis(code: int | None) -> dict[str, Any] | None:
            filters = FinancialOverviewFilters(
                data_inicial=data_inicial,
                data_final=data_final,
                empresa_codigo=code,
                centro_custo=centro_custo,
                tipo_despesa=tipo_despesa,
            )
            resp = await self._analytics.get_kpis(filters)
            if not resp.success:
                warnings.append(f"kpis: {resp.error or 'falha'}")
                return None
            return resp.data

        async def _fetch_dre(code: int | None) -> dict[str, Any] | None:
            filters = FinancialOverviewFilters(
                data_inicial=data_inicial,
                data_final=data_final,
                empresa_codigo=code,
                centro_custo=centro_custo,
                tipo_despesa=tipo_despesa,
            )
            resp = await self._analytics.get_dre(filters)
            if not resp.success:
                warnings.append(f"dre: {resp.error or 'falha'}")
                return None
            return resp.data

        async def _fetch_data_quality(code: int | None) -> dict[str, Any] | None:
            dq_filters = DataQualityFilters(
                data_inicial=data_inicial,
                data_final=data_final,
                empresa_codigo=code,
                centro_custo=centro_custo,
            )
            resp = await self._data_quality.get_data_quality(dq_filters)
            if not resp.success:
                warnings.append(f"data-quality: {resp.error or 'falha'}")
                return None
            return resp.data

        if len(empresa_codes) > 1:
            kpi_items = []
            dre_items = []
            dq_items = []
            for code in empresa_codes:
                kpi_item = await _fetch_kpis(code)
                if kpi_item:
                    kpi_items.append(kpi_item)
                dre_item = await _fetch_dre(code)
                if dre_item:
                    dre_items.append(dre_item)
                dq_item = await _fetch_data_quality(code)
                if dq_item:
                    dq_items.append(dq_item)
            kpis = _aggregate_kpis(kpi_items, data_inicial, data_final) if kpi_items else None
            dre = _aggregate_dre(dre_items, data_inicial, data_final) if dre_items else None
            data_quality = _aggregate_data_quality(dq_items) if dq_items else None
        else:
            single_code = empresa_codes[0] if empresa_codes else None
            kpis = await _fetch_kpis(single_code)
            dre = await _fetch_dre(single_code)
            data_quality = await _fetch_data_quality(single_code)

        coverage: dict[str, Any] | None = None
        companies_resp = await self._overview.get_companies()
        if companies_resp.success and companies_resp.data:
            companies = companies_resp.data.get("data") if isinstance(companies_resp.data, dict) else []
            if isinstance(companies, list):
                coverage = build_network_coverage(companies)
            else:
                warnings.append("coverage: formato inesperado")
        else:
            warnings.append(f"coverage: {companies_resp.error or 'falha'}")

        fuel: dict[str, Any] | None = None
        fuel_code = empresa_codes[0] if len(empresa_codes) == 1 else (None if empresa_codes else None)
        fuel_filters = FuelAnalyticsFilters(
            data_inicial=data_inicial,
            data_final=data_final,
            empresa_codigo=fuel_code,
        )
        fuel_resp = await self._fuel_analytics.get_fuel_summary(fuel_filters)
        if fuel_resp.success:
            payload = fuel_resp.data or {}
            payload["kpis"] = self._fuel_kpi_engine.build(payload)
            fuel = {"success": True, "data": payload, "error": None}
        else:
            warnings.append(f"fuel: {fuel_resp.error or 'falha'}")

        return {
            "lastUpdated": datetime.now().isoformat(timespec="seconds"),
            "kpis": kpis,
            "dre": dre,
            "coverage": coverage,
            "dataQuality": data_quality,
            "fuel": fuel,
            "warnings": warnings,
        }

    async def refresh(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        centro_custo: str | None = None,
        tipo_despesa: str | None = None,
    ) -> dict[str, Any]:
        key = build_snapshot_key(data_inicial, data_final, empresa_codigo)
        async with self._lock:
            if key in self._running:
                return {"status": "already_running", "key": key}
            self._running.add(key)

        try:
            collected = await self.collect(
                data_inicial=data_inicial,
                data_final=data_final,
                empresa_codigo=empresa_codigo,
                centro_custo=centro_custo,
                tipo_despesa=tipo_despesa,
            )
            has_data = any(
                collected.get(field) is not None
                for field in ("kpis", "dre", "coverage", "dataQuality", "fuel")
            )
            if has_data:
                self._store.save(key, collected)
            return {
                "status": "completed",
                "key": key,
                "lastUpdated": collected.get("lastUpdated"),
                "warnings": collected.get("warnings") or [],
            }
        finally:
            async with self._lock:
                self._running.discard(key)

    def start_refresh_background(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        centro_custo: str | None = None,
        tipo_despesa: str | None = None,
    ) -> dict[str, Any]:
        key = build_snapshot_key(data_inicial, data_final, empresa_codigo)
        if key in self._running:
            return {"status": "already_running", "key": key}

        async def _runner() -> None:
            await self.refresh(
                data_inicial=data_inicial,
                data_final=data_final,
                empresa_codigo=empresa_codigo,
                centro_custo=centro_custo,
                tipo_despesa=tipo_despesa,
            )

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_runner())
            return {"status": "started", "key": key}
        except RuntimeError:
            return {"status": "already_running", "key": key}
