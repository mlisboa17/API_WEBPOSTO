"""Inteligência de composição de vendas e cross-selling (Pista x Lubrificantes x Loja).

Regra crítica: quantidadeAbastecimentos = COUNT(DISTINCT abastecimentoCodigo)
a partir de /INTEGRACAO/ABASTECIMENTO — nunca COUNT de NFCe/notas fiscais.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from src.core.config import OFFICIAL_COMPANY_CODES, resolve_company_api_key
from src.domain.adelaide.fuel_catalog import eh_combustivel_codigo
from src.gateway.shared_client import get_webposto_client
from src.gateway.webposto_client import WebPostoClient
from src.interfaces.http.schemas.executive_sales_schema import (
    CompositionBySectorItem,
    CompositionSummaryKPI,
    CrossSellingFunnel,
    FuelBreakdownItem,
    SalesCompositionResponse,
)
from src.services.abastecimento_service import AbastecimentoService
from src.services.sales_analytics_service import (
    _AFFINITY_SCALE,
    _classify_fuel_label,
    _conv_category,
    _extract_rows,
    _is_pista_non_fuel,
    _litros,
    _produto_codigo,
    _produto_grupo_blob,
    _produto_nome,
    _valor,
)

logger = logging.getLogger(__name__)


def _abastecimento_id(row: dict[str, Any]) -> str:
    """Identificador operacional da bomba (não NFCe)."""
    for key in (
        "abastecimentoCodigo",
        "codigo",
        "vendaItemCodigo",
        "stringFull",
    ):
        val = row.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    # fallback estável sem inventar nota fiscal
    return (
        f"{row.get('empresaCodigo')}-"
        f"{row.get('dataHoraAbastecimento') or row.get('dataFiscal')}-"
        f"{row.get('codigoBico')}-"
        f"{row.get('quantidade')}-"
        f"{row.get('valorTotal')}"
    )


def _venda_key(row: dict[str, Any]) -> str:
    for key in ("vendaCodigo", "codigoVenda", "vendaItemCodigo", "abastecimentoCodigo"):
        val = row.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def _pct(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return round(num / den * 100, 1)


def _empty_response(
    data_inicial: str,
    data_final: str,
    empresa_codigo: int | None,
    *,
    fallback: bool = False,
    mensagem: str | None = None,
) -> SalesCompositionResponse:
    return SalesCompositionResponse(
        summary=CompositionSummaryKPI(),
        compositionBySector=[
            CompositionBySectorItem(setor="Combustíveis"),
            CompositionBySectorItem(setor="Produtos de Pista"),
            CompositionBySectorItem(setor="Conveniência"),
        ],
        crossSellingFunnel=CrossSellingFunnel(),
        combustiveis=[],
        produtosPista=[],
        conveniencia=[],
        empresaCodigo=empresa_codigo,
        periodo={"inicio": data_inicial, "fim": data_final},
        fallback=fallback,
        mensagem=mensagem,
    )


class SalesCompositionService:
    """Agrega combustível (ABASTECIMENTO) + não combustível (VENDA_ITEM)."""

    def __init__(self) -> None:
        self._client = get_webposto_client()
        self._abastecimento = AbastecimentoService(self._client)

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None = None,
    ) -> SalesCompositionResponse:
        try:
            abastecimentos = await self._fetch_abastecimentos(
                data_inicial, data_final, empresa_codigo
            )

            venda_items = await self._fetch_venda_items(
                data_inicial, data_final, empresa_codigo
            )
            return self._aggregate(
                abastecimentos,
                venda_items,
                data_inicial,
                data_final,
                empresa_codigo,
            )
        except Exception as exc:
            logger.exception(
                "Sales composition falhou empresa=%s: %s", empresa_codigo, exc
            )
            return _empty_response(
                data_inicial,
                data_final,
                empresa_codigo,
                fallback=True,
                mensagem=f"Fallback ativo: {exc}",
            )

    async def _fetch_abastecimentos(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None = None,
    ) -> list[dict[str, Any]]:
        """Busca paginada por filial (API key própria). Consolidado = soma das 3 oficiais."""
        targets = (
            [int(empresa_codigo)]
            if empresa_codigo
            else list(OFFICIAL_COMPANY_CODES)
        )
        all_rows: list[dict[str, Any]] = []
        for code in targets:
            resp = await self._abastecimento.get_periodo(
                data_inicial, data_final, empresa_codigo=code
            )
            if not resp.success:
                logger.warning(
                    "ABASTECIMENTO indisponível empresa=%s: %s",
                    code,
                    getattr(resp, "error", None),
                )
                continue
            rows = _extract_rows(resp.data)
            # defesa extra: só mantém a filial solicitada
            rows = [
                r
                for r in rows
                if int(r.get("empresaCodigo") or r.get("empresa") or 0) == int(code)
            ]
            all_rows.extend(rows)
            logger.info(
                "Composition abastecimentos empresa=%s n=%d",
                code,
                len(rows),
            )
        return all_rows

    def _client_for_company(self, empresa_codigo: int | None) -> WebPostoClient:
        if not empresa_codigo:
            return self._client
        try:
            key = resolve_company_api_key(int(empresa_codigo))
            if key:
                return WebPostoClient.for_api_key(key)
        except Exception as exc:
            logger.warning(
                "API key empresa=%s indisponível para venda_item: %s",
                empresa_codigo,
                exc,
            )
        return self._client

    async def _fetch_venda_items(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None,
    ) -> list[dict[str, Any]]:
        """VENDA_ITEM por filial com API key própria (mesma estratégia do ABASTECIMENTO)."""
        targets = (
            [int(empresa_codigo)]
            if empresa_codigo
            else list(OFFICIAL_COMPANY_CODES)
        )
        all_rows: list[dict[str, Any]] = []
        for code in targets:
            client = self._client_for_company(code)
            ultimo = None
            company_rows = 0
            try:
                for _ in range(40):
                    params: dict[str, Any] = {
                        "dataInicial": data_inicial,
                        "dataFinal": data_final,
                        "empresaCodigo": code,
                    }
                    if ultimo is not None:
                        params["ultimoCodigo"] = ultimo
                    resp = await client.call_endpoint("venda_item", params=params)
                    if not resp.success:
                        logger.warning(
                            "venda_item falhou empresa=%s: %s",
                            code,
                            getattr(resp, "error", None),
                        )
                        break
                    raw = resp.data
                    batch_raw = _extract_rows(raw)
                    if not batch_raw:
                        break
                    batch = [
                        r
                        for r in batch_raw
                        if int(r.get("empresaCodigo") or r.get("empresa") or 0)
                        == int(code)
                    ]
                    all_rows.extend(batch)
                    company_rows += len(batch)
                    new_ultimo = (
                        raw.get("ultimoCodigo") if isinstance(raw, dict) else None
                    )
                    # Continua paginação pelo cursor bruto — filtro de filial não encerra cedo
                    if (
                        new_ultimo is None
                        or new_ultimo == ultimo
                        or len(batch_raw) < 50
                    ):
                        break
                    ultimo = new_ultimo
            except Exception as exc:
                logger.warning("venda_item falhou empresa=%s: %s", code, exc)
            logger.info(
                "Composition venda_item empresa=%s n=%d", code, company_rows
            )
        return all_rows

    def _aggregate(
        self,
        abastecimentos: list[dict[str, Any]],
        venda_items: list[dict[str, Any]],
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None,
    ) -> SalesCompositionResponse:
        # --- Contagem operacional OBRIGATÓRIA via abastecimentos distintos ---
        by_abast: dict[str, dict[str, Any]] = {}
        for row in abastecimentos:
            aid = _abastecimento_id(row)
            # mantém o primeiro registro do abastecimento (evita inflar litros/R$)
            if aid not in by_abast:
                by_abast[aid] = row

        ids_abastecimento = set(by_abast.keys())
        litros_total = 0.0
        fat_combustivel = 0.0
        fuel_bucket: dict[str, dict[str, float]] = defaultdict(
            lambda: {"litros": 0.0, "faturamento": 0.0}
        )
        abast_venda_keys: set[str] = set()

        for row in by_abast.values():
            litros = _litros(row)
            valor = _valor(row)
            litros_total += litros
            fat_combustivel += valor
            codigo = _produto_codigo(row)
            nome = _produto_nome(row)
            label = _classify_fuel_label(codigo, nome)
            fuel_bucket[label]["litros"] += litros
            fuel_bucket[label]["faturamento"] += valor
            vk = _venda_key(row)
            if vk:
                abast_venda_keys.add(vk)

        qtd_abastecimentos = len(ids_abastecimento)

        pista_bucket: dict[str, dict[str, float]] = defaultdict(
            lambda: {"litros": 0.0, "faturamento": 0.0, "margem": 0.0}
        )
        conv_bucket: dict[str, dict[str, float]] = defaultdict(
            lambda: {"litros": 0.0, "faturamento": 0.0, "margem": 0.0}
        )
        clientes_loja: set[str] = set()
        vendas_pista: set[str] = set()
        vendas_loja: set[str] = set()

        for row in venda_items:
            codigo = _produto_codigo(row)
            if eh_combustivel_codigo(codigo):
                continue
            grupo = _produto_grupo_blob(row)
            nome = _produto_nome(row) or grupo or f"Produto {codigo}"
            valor = _valor(row)
            if valor <= 0:
                continue
            vk = _venda_key(row) or f"item-{len(clientes_loja)}"
            clientes_loja.add(vk)

            if _is_pista_non_fuel(nome, codigo, grupo):
                low = f"{nome} {grupo}".casefold()
                if "palheta" in low:
                    cat = "Palhetas"
                elif "fluido" in low or "fluído" in low or "arrefec" in low or "radiador" in low:
                    cat = "Fluídos"
                elif "filtro" in low:
                    cat = "Filtros"
                elif "aditiv" in low or "adblue" in low or "arla" in low:
                    cat = "Aditivos"
                else:
                    cat = "Lubrificantes"
                pista_bucket[cat]["faturamento"] += valor
                pista_bucket[cat]["margem"] += valor * 0.35
                vendas_pista.add(vk)
            else:
                cat = _conv_category(f"{nome} {grupo}")
                conv_bucket[cat]["faturamento"] += valor
                conv_bucket[cat]["margem"] += valor * 0.28
                vendas_loja.add(vk)

        fat_pista = sum(v["faturamento"] for v in pista_bucket.values())
        fat_loja = sum(v["faturamento"] for v in conv_bucket.values())

        # Contingência auditada: sem não-combustível classificado (API vazia ou só combustível)
        used_fallback_estimate = False
        if fat_combustivel > 0 and fat_pista <= 0 and fat_loja <= 0:
            used_fallback_estimate = True
            scale = _AFFINITY_SCALE.get(empresa_codigo, 1.0)
            fat_pista = round(fat_combustivel * 0.018 * scale, 2)
            fat_loja = round(fat_combustivel * 0.051 * scale, 2)
            pista_bucket.clear()
            conv_bucket.clear()
            pista_bucket["Lubrificantes / Aditivos"] = {
                "litros": 0.0,
                "faturamento": fat_pista,
                "margem": fat_pista * 0.35,
            }
            conv_bucket["Bebidas"] = {
                "litros": 0.0,
                "faturamento": round(fat_loja * 0.40, 2),
                "margem": round(fat_loja * 0.40 * 0.28, 2),
            }
            conv_bucket["Café/Padaria"] = {
                "litros": 0.0,
                "faturamento": round(fat_loja * 0.25, 2),
                "margem": round(fat_loja * 0.25 * 0.28, 2),
            }
            conv_bucket["Tabacaria"] = {
                "litros": 0.0,
                "faturamento": round(fat_loja * 0.20, 2),
                "margem": round(fat_loja * 0.20 * 0.28, 2),
            }
            conv_bucket["Mercearia"] = {
                "litros": 0.0,
                "faturamento": round(fat_loja * 0.15, 2),
                "margem": round(fat_loja * 0.15 * 0.28, 2),
            }
            # Penetração pista: (Combustível+Produto Pista) / Abastecimentos
            tx_pista_pct = min(12.0, 4.0 * scale)
            tx_loja_pct = min(18.0, 7.5 * scale)
            n_pista = int(round(qtd_abastecimentos * tx_pista_pct / 100))
            n_loja = int(round(qtd_abastecimentos * tx_loja_pct / 100))
            vendas_pista = {f"est-pista-{i}" for i in range(max(n_pista, 1 if fat_pista > 0 else 0))}
            vendas_loja = {f"est-loja-{i}" for i in range(n_loja)}
            clientes_loja = vendas_pista | vendas_loja
            logger.info(
                "Fallback setorial auditado empresa=%s fat_comb=%.2f pista=%.2f loja=%.2f "
                "venda_items=%d",
                empresa_codigo,
                fat_combustivel,
                fat_pista,
                fat_loja,
                len(venda_items),
            )

        fat_total = fat_combustivel + fat_pista + fat_loja
        margem_fuel = fat_combustivel * 0.08
        margem_pista = sum(v.get("margem", v["faturamento"] * 0.35) for v in pista_bucket.values())
        margem_loja = sum(v.get("margem", v["faturamento"] * 0.28) for v in conv_bucket.values())

        # Funil: cruza chaves de venda quando disponíveis; senão usa contagens estimadas
        if abast_venda_keys and (vendas_pista or vendas_loja) and not used_fallback_estimate:
            tx_pista = len(abast_venda_keys & vendas_pista)
            tx_loja = len(abast_venda_keys & vendas_loja)
            tx_combo = len(abast_venda_keys & (vendas_pista | vendas_loja))
            # Se IDs não cruzam entre ABASTECIMENTO e VENDA_ITEM, usa proxy operacional
            if tx_combo == 0 and (fat_pista > 0 or fat_loja > 0):
                tx_pista = min(len(vendas_pista), qtd_abastecimentos)
                tx_loja = min(len(vendas_loja), qtd_abastecimentos)
                tx_combo = min(len(vendas_pista | vendas_loja), qtd_abastecimentos)
        else:
            tx_pista = len(vendas_pista)
            tx_loja = len(vendas_loja)
            tx_combo = len(vendas_pista | vendas_loja)
            # limita ao total de abastecimentos (nunca maior que a base operacional)
            tx_pista = min(tx_pista, qtd_abastecimentos)
            tx_loja = min(tx_loja, qtd_abastecimentos)
            tx_combo = min(tx_combo, qtd_abastecimentos)

        pen_pista = _pct(tx_pista, qtd_abastecimentos)
        pen_loja = _pct(tx_loja, qtd_abastecimentos)
        pen_total = _pct(tx_combo, qtd_abastecimentos)
        relacao_loja = _pct(len(clientes_loja), qtd_abastecimentos)

        ticket = (
            round(fat_combustivel / qtd_abastecimentos, 2) if qtd_abastecimentos else 0.0
        )
        nao_comb_por_abast = (
            round((fat_pista + fat_loja) / qtd_abastecimentos, 2)
            if qtd_abastecimentos
            else 0.0
        )
        litros_por_abast = (
            round(litros_total / qtd_abastecimentos, 2) if qtd_abastecimentos else 0.0
        )

        def _fuel_items(bucket: dict[str, dict[str, float]]) -> list[FuelBreakdownItem]:
            total = sum(v["faturamento"] for v in bucket.values()) or 1.0
            return [
                FuelBreakdownItem(
                    categoria=cat,
                    litros=round(vals.get("litros", 0.0), 2),
                    faturamento=round(vals["faturamento"], 2),
                    participacao=round(vals["faturamento"] / total * 100, 1),
                )
                for cat, vals in sorted(
                    bucket.items(), key=lambda x: x[1]["faturamento"], reverse=True
                )
                if vals["faturamento"] > 0 or vals.get("litros", 0) > 0
            ]

        summary = CompositionSummaryKPI(
            faturamentoTotal=round(fat_total, 2),
            faturamentoCombustivel=round(fat_combustivel, 2),
            faturamentoProdutosPista=round(fat_pista, 2),
            faturamentoConveniencia=round(fat_loja, 2),
            litrosVendidos=round(litros_total, 2),
            quantidadeAbastecimentos=qtd_abastecimentos,
            clientesLoja=len(clientes_loja),
            ticketMedioAbastecimento=ticket,
            receitaNaoCombustivelPorAbastecimento=nao_comb_por_abast,
            litrosPorAbastecimento=litros_por_abast,
            penetracaoProdutosPistaPercentual=pen_pista,
            penetracaoConvenienciaPercentual=pen_loja,
            penetracaoCrossSellingPercentual=pen_total,
        )

        sectors = [
            CompositionBySectorItem(
                setor="Combustíveis",
                faturamento=round(fat_combustivel, 2),
                margem=round(margem_fuel, 2),
                participacao=_pct(fat_combustivel, fat_total),
            ),
            CompositionBySectorItem(
                setor="Produtos de Pista",
                faturamento=round(fat_pista, 2),
                margem=round(margem_pista, 2),
                participacao=_pct(fat_pista, fat_total),
            ),
            CompositionBySectorItem(
                setor="Conveniência",
                faturamento=round(fat_loja, 2),
                margem=round(margem_loja, 2),
                participacao=_pct(fat_loja, fat_total),
            ),
        ]

        funnel = CrossSellingFunnel(
            totalAbastecimentos=qtd_abastecimentos,
            clientesLoja=len(clientes_loja),
            transacoesCombustivelProdutoPista=tx_pista,
            transacoesCombustivelConveniencia=tx_loja,
            transacoesCombustivelComboTotal=tx_combo,
            penetracaoProdutosPistaPercentual=pen_pista,
            penetracaoConvenienciaPercentual=pen_loja,
            penetracaoTotalPercentual=pen_total,
            relacaoLojaPistaPercentual=relacao_loja,
        )

        return SalesCompositionResponse(
            summary=summary,
            compositionBySector=sectors,
            crossSellingFunnel=funnel,
            combustiveis=_fuel_items(fuel_bucket),
            produtosPista=_fuel_items(pista_bucket),
            conveniencia=_fuel_items(conv_bucket),
            empresaCodigo=empresa_codigo,
            periodo={"inicio": data_inicial, "fim": data_final},
            fonteAbastecimentos="INTEGRACAO/ABASTECIMENTO",
            fallback=used_fallback_estimate or qtd_abastecimentos == 0,
            mensagem=(
                "Fallback auditado: sem itens não-combustível classificados no período "
                f"(venda_item n={len(venda_items)}; setores estimados a partir do combustível)"
                if used_fallback_estimate
                else (
                    "Sem abastecimentos no período"
                    if qtd_abastecimentos == 0
                    else None
                )
            ),
        )
