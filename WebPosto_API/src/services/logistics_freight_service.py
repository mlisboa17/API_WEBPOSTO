"""Eficiência logística — frete real a partir de NF de entrada (webPosto)."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any, Optional

from src.core.config import OFFICIAL_COMPANY_CODES, resolve_company_api_key
from src.gateway.webposto_client import WebPostoClient
from src.interfaces.http.schemas.executive_logistics_schema import (
    LogisticsSummary,
    LogisticsSupplierEfficiency,
)
from src.utils.filial_normalizer import resolve_empresa_codigo

logger = logging.getLogger(__name__)

_LOGISTICS_CACHE: dict[str, tuple[float, LogisticsSummary]] = {}
_LOGISTICS_TTL_S = 600.0

FILIAL_LABELS = {
    5555: "Casa Caiada",
    11495: "VIP",
    74014: "Real Doze",
}

# Referência histórica FOB (R$/L) para custo de oportunidade — não entra no frete efetivo.
FOB_REF_RS_LITRO = 0.040


def _f(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data", "items"):
            if isinstance(payload.get(key), list):
                return [r for r in payload[key] if isinstance(r, dict)]
    return []


def _is_fuel_item(item: dict[str, Any]) -> bool:
    unidade = str(item.get("unidadeCompra") or item.get("unidade") or "").upper()
    qty = _f(item.get("quantidade") or item.get("quantide"))
    if unidade in {"LT", "L", "LITRO", "LITROS"}:
        return qty > 0
    # Carretas típicas ≥ 1.000 L mesmo sem unidade LT preenchida
    if qty >= 1000:
        return True
    # Item com LMC de combustível
    if item.get("produtoLmcCodigo") and qty > 0:
        return True
    return False


def compute_freight_from_notes(
    notas: list[dict[str, Any]],
    itens: list[dict[str, Any]],
    fornecedor_nomes: dict[int, str] | None = None,
) -> tuple[float, float, float, list[LogisticsSupplierEfficiency]]:
    """
    Custo real de frete:
      frete_total = Σ valorFrete das NFs
      litros = Σ quantidade dos itens combustível das mesmas NFs
      R$/L = frete_total / litros
    """
    nomes = fornecedor_nomes or {}
    items_by_compra: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for it in itens:
        emp = int(it.get("empresaCodigo") or 0)
        compra = int(it.get("compraCodigo") or it.get("codigo") or 0)
        if emp and compra:
            items_by_compra[(emp, compra)].append(it)

    by_supplier: dict[str, dict[str, float]] = defaultdict(
        lambda: {"frete": 0.0, "litros": 0.0, "cif_litros": 0.0, "fob_litros": 0.0}
    )
    frete_total = 0.0
    litros_total = 0.0

    for nota in notas:
        emp = int(nota.get("empresaCodigo") or 0)
        compra = int(nota.get("compraCodigo") or nota.get("codigo") or 0)
        frete = _f(nota.get("valorFrete") or nota.get("frete"))
        if frete <= 0:
            continue

        fuel_items = [
            it
            for it in items_by_compra.get((emp, compra), [])
            if _is_fuel_item(it)
        ]
        litros = sum(
            _f(it.get("quantidade") or it.get("quantide")) for it in fuel_items
        )
        if litros <= 0:
            # Fallback: volumetria pela própria NF (produto total / preço médio implícito não confiável)
            # Usa itens da NF com qty>0 se parecer combustível por valor alto
            litros = sum(
                _f(it.get("quantidade") or it.get("quantide"))
                for it in items_by_compra.get((emp, compra), [])
                if _f(it.get("quantidade") or it.get("quantide")) >= 500
            )
        if litros <= 0:
            continue

        forn_cod = int(nota.get("fornecedorCodigo") or 0)
        forn_nome = nomes.get(forn_cod) or f"Fornecedor {forn_cod or '—'}"
        tipo = str(nota.get("tipoFrete") or "").lower()
        # Destinatário / FOB ≈ frete próprio; Contratação por conta do Remetente ≈ CIF
        is_fob = "destinat" in tipo or "fob" in tipo

        bucket = by_supplier[forn_nome]
        bucket["frete"] += frete
        bucket["litros"] += litros
        if is_fob:
            bucket["fob_litros"] += litros
        else:
            bucket["cif_litros"] += litros

        frete_total += frete
        litros_total += litros

    eficiencia: list[LogisticsSupplierEfficiency] = []
    oportunidade = 0.0
    for nome, agg in sorted(by_supplier.items(), key=lambda x: -x[1]["litros"]):
        litros = agg["litros"]
        frete = agg["frete"]
        if litros <= 0:
            continue
        rs_l = frete / litros
        markup = (rs_l / FOB_REF_RS_LITRO - 1.0) * 100 if FOB_REF_RS_LITRO > 0 else 0.0
        delta = rs_l - FOB_REF_RS_LITRO
        if delta > 0 and agg["cif_litros"] > 0:
            oportunidade += delta * agg["cif_litros"]
        eficiencia.append(
            LogisticsSupplierEfficiency(
                fornecedor=nome,
                custo_frete_medio_rs_litro=round(rs_l, 4),
                markup_logistico_pct=round(markup, 2),
                delta_fob_cif_rs_litro=round(delta, 4),
                total_litros_comprados=round(litros, 2),
            )
        )

    frete_medio = (frete_total / litros_total) if litros_total > 0 else 0.0
    return (
        round(frete_total, 2),
        round(frete_medio, 4),
        round(oportunidade, 2),
        eficiencia,
    )


class LogisticsFreightService:
    """Análise de frete com dados reais de NF (COMPRA / NOTA_FISCAL_ENTRADA)."""

    def __init__(self, client: WebPostoClient | None = None) -> None:
        self._client = client or WebPostoClient()

    def _client_for(self, empresa_codigo: int) -> WebPostoClient:
        try:
            key = resolve_company_api_key(int(empresa_codigo))
            if key:
                return WebPostoClient.for_api_key(key)
        except Exception as exc:
            logger.warning("API key empresa=%s: %s", empresa_codigo, exc)
        return self._client

    async def _paginate(
        self,
        client: WebPostoClient,
        endpoint_key: str,
        params: dict[str, Any],
        max_pages: int = 30,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        ultimo = None
        for _ in range(max_pages):
            page = dict(params)
            if ultimo is not None:
                page["ultimoCodigo"] = ultimo
            resp = await client.call_endpoint(endpoint_key, params=page)
            if not resp.success:
                logger.info(
                    "logistics %s falhou: %s",
                    endpoint_key,
                    getattr(resp, "error", None),
                )
                break
            data = resp.data
            batch = _extract_rows(data)
            if not batch:
                break
            rows.extend(batch)
            novo = data.get("ultimoCodigo") if isinstance(data, dict) else None
            if novo is None or novo == ultimo or len(batch) < 40:
                break
            ultimo = novo
        return rows

    async def _fetch_nf_bundle(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
        """
        Usa COMPRA + COMPRA_ITEM (schema CompraRede = NF de entrada com valorFrete).
        NOTA_FISCAL_ENTRADA fica como fallback — hoje retorna 401 nas chaves do grupo
        e abre circuit breaker se chamado primeiro.
        """
        client = self._client_for(empresa_codigo)
        params = {
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "empresaCodigo": empresa_codigo,
        }

        notas_task = self._paginate(client, "compra", params)
        itens_task = self._paginate(client, "compra_item", params)
        notas, itens = await asyncio.gather(notas_task, itens_task)
        fonte = "COMPRA (NF entrada webPosto)"

        if not notas:
            notas = await self._paginate(client, "nota_fiscal_entrada", params)
            if notas:
                fonte = "NOTA_FISCAL_ENTRADA"

        notas = [
            n
            for n in notas
            if int(n.get("empresaCodigo") or 0) == int(empresa_codigo)
        ]
        itens = [
            i
            for i in itens
            if int(i.get("empresaCodigo") or 0) == int(empresa_codigo)
        ]
        return notas, itens, fonte

    async def _fornecedor_map(self, empresa_codigo: int) -> dict[int, str]:
        """Uma página basta para resolver os códigos usados nas NFs de combustível."""
        client = self._client_for(empresa_codigo)
        mapping: dict[int, str] = {128841: "VIBRA ENERGIA S.A"}
        try:
            resp = await client.call_endpoint("fornecedor", params={"limite": 200})
            if not resp.success:
                return mapping
            for row in _extract_rows(resp.data):
                cod = int(row.get("codigo") or row.get("fornecedorCodigo") or 0)
                nome = str(row.get("fantasia") or row.get("razao") or "").strip()
                if cod and nome:
                    mapping[cod] = nome
        except Exception as exc:
            logger.warning("fornecedor map empresa=%s: %s", empresa_codigo, exc)
        return mapping

    async def analyze(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: Optional[int] = None,
    ) -> LogisticsSummary:
        empresa = resolve_empresa_codigo(empresa_codigo)
        cache_key = f"{data_inicial}|{data_final}|{empresa}"
        now = time.monotonic()
        cached = _LOGISTICS_CACHE.get(cache_key)
        if cached and (now - cached[0]) < _LOGISTICS_TTL_S:
            return cached[1]

        targets = (
            [int(empresa)]
            if empresa is not None
            else list(OFFICIAL_COMPANY_CODES)
        )

        bundles = await asyncio.gather(
            *[
                self._fetch_nf_bundle(data_inicial, data_final, code)
                for code in targets
            ]
        )
        nomes = await self._fornecedor_map(targets[0])

        all_notas: list[dict[str, Any]] = []
        all_itens: list[dict[str, Any]] = []
        fontes: list[str] = []
        for code, (notas, itens, fonte) in zip(targets, bundles):
            all_notas.extend(notas)
            all_itens.extend(itens)
            if notas:
                fontes.append(f"{FILIAL_LABELS.get(code, code)}:{fonte}")

        frete_total, frete_medio, oportunidade, eficiencia = compute_freight_from_notes(
            all_notas, all_itens, nomes
        )

        notas_com_frete = sum(1 for n in all_notas if _f(n.get("valorFrete")) > 0)
        fonte_label = (
            "Dado Real - Fonte NF webPosto"
            if notas_com_frete > 0
            else "Sem frete destacado nas NFs do período"
        )

        logger.info(
            "logistics frete real periodo=%s..%s empresas=%s notas=%d comFrete=%d frete=%.2f litrosMed=%.4f fontes=%s",
            data_inicial,
            data_final,
            targets,
            len(all_notas),
            notas_com_frete,
            frete_total,
            frete_medio,
            fontes,
        )

        result = LogisticsSummary(
            custo_frete_efetivo_total_rs=frete_total,
            frete_medio_grupo_rs_litro=frete_medio,
            custo_oportunidade_frete_total_rs=oportunidade,
            eficiencia_por_fornecedor=eficiencia,
            fonte=fonte_label,
            notas_com_frete=notas_com_frete,
            detalhe_fonte="; ".join(fontes) if fontes else None,
        )
        _LOGISTICS_CACHE[cache_key] = (time.monotonic(), result)
        return result
