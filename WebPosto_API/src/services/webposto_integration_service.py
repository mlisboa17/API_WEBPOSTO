"""Integração real com a API webPosto — vendas, tanques e CPM.

Substitui mocks: todas as leituras passam pelo WebPostoClient oficial (httpx).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from src.gateway.shared_client import get_webposto_client
from src.services.company_settings_service import get_company_settings_service
from src.services.external_market_service import BRANCH_GEOCOORDINATES

logger = logging.getLogger(__name__)


@dataclass
class RealtimeSalesSnapshot:
    empresa_codigo: int
    data: str
    litros_total: float = 0.0
    faturamento_rs: float = 0.0
    qtd_abastecimentos: int = 0
    por_produto: list[dict[str, Any]] = field(default_factory=list)
    fonte: str = "webposto_abastecimento"
    sucesso: bool = True
    mensagem: str = ""


@dataclass
class TankLevelSnapshot:
    empresa_codigo: int
    tanques: list[dict[str, Any]] = field(default_factory=list)
    fonte: str = "webposto_tanque"
    sucesso: bool = True
    mensagem: str = ""


@dataclass
class WeightedCostSnapshot:
    empresa_codigo: int
    custos: list[dict[str, Any]] = field(default_factory=list)
    fonte: str = "webposto_produto_combustivel"
    sucesso: bool = True
    mensagem: str = ""


class WebPostoIntegrationService:
    """Fachada de produção para estoque, vendas e custo médio."""

    def __init__(self) -> None:
        self.client = get_webposto_client()
        self._settings = get_company_settings_service()

    def _client_for_company(self, empresa_codigo: int):
        """Usa token específico da filial; fallback para cliente global / WEBPOSTO_TOKEN."""
        from src.core.config import resolve_company_api_key
        from src.gateway.webposto_client import WebPostoClient

        key = resolve_company_api_key(empresa_codigo)
        if key:
            return WebPostoClient.for_api_key(key)
        return self.client

    @staticmethod
    def _extract_rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [r for r in payload if isinstance(r, dict)]
        if isinstance(payload, dict):
            for key in ("resultados", "dados", "data", "items"):
                rows = payload.get(key)
                if isinstance(rows, list):
                    return [r for r in rows if isinstance(r, dict)]
        return []

    async def get_realtime_sales(self, empresa_codigo: int) -> RealtimeSalesSnapshot:
        """Faturamento e volumetria acumulada do dia via /ABASTECIMENTO."""
        today = date.today().isoformat()
        snap = RealtimeSalesSnapshot(empresa_codigo=empresa_codigo, data=today)
        by_product: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"produto_codigo": "", "produto_nome": "", "litros": 0.0, "faturamento_rs": 0.0, "qtd": 0}
        )
        client = self._client_for_company(empresa_codigo)

        try:
            params: dict[str, Any] = {
                "dataInicial": today,
                "dataFinal": today,
                "empresaCodigo": empresa_codigo,
            }
            all_rows: list[dict[str, Any]] = []
            ultimo_codigo = None
            for _ in range(200):
                req = {**params}
                if ultimo_codigo is not None:
                    req["ultimoCodigo"] = ultimo_codigo
                resp = await client.call_endpoint("abastecimento", params=req)
                if not resp.success:
                    logger.warning(
                        "WebPosto abastecimento falhou empresa=%s status=%s err=%s",
                        empresa_codigo,
                        getattr(resp, "status_code", None),
                        resp.error,
                    )
                    if not all_rows:
                        snap.sucesso = False
                        snap.mensagem = str(resp.error or "Falha ao consultar abastecimentos")
                        return snap
                    break

                raw = resp.data
                batch = self._extract_rows(raw)
                new_ultimo = None
                if isinstance(raw, dict):
                    new_ultimo = raw.get("ultimoCodigo")

                if not batch:
                    break

                # WebPosto pode misturar filiais no mesmo token/rede — isola a filial pedida.
                batch = [
                    row
                    for row in batch
                    if int(row.get("empresaCodigo") or row.get("empresa") or 0) == int(empresa_codigo)
                ]
                all_rows.extend(batch)

                for row in batch:
                    litros = float(
                        row.get("quantidadeLitros")
                        or row.get("litros")
                        or row.get("quantidade")
                        or 0
                    )
                    valor = float(
                        row.get("valorTotal")
                        or row.get("valorVenda")
                        or row.get("total")
                        or row.get("valor")
                        or 0
                    )
                    codigo = str(
                        row.get("produtoCodigo")
                        or row.get("produtoLmcCodigo")
                        or row.get("codigoProduto")
                        or ""
                    )
                    nome = str(
                        row.get("produtoDescricao")
                        or row.get("produtoNome")
                        or row.get("produto")
                        or f"Produto {codigo}"
                    ).strip()
                    snap.litros_total += litros
                    snap.faturamento_rs += valor
                    snap.qtd_abastecimentos += 1
                    if codigo:
                        bucket = by_product[codigo]
                        bucket["produto_codigo"] = codigo
                        bucket["produto_nome"] = nome
                        bucket["litros"] += litros
                        bucket["faturamento_rs"] += valor
                        bucket["qtd"] += 1

                # Continua paginação com base no lote bruto da API (não no filtrado)
                if new_ultimo is None or new_ultimo == ultimo_codigo:
                    break
                ultimo_codigo = new_ultimo
                # WebPosto page size real ≈ 200; parar só em página parcial
                raw_batch_len = len(self._extract_rows(raw))
                if raw_batch_len < 200:
                    break

            snap.por_produto = [
                {
                    **v,
                    "litros": round(v["litros"], 2),
                    "faturamento_rs": round(v["faturamento_rs"], 2),
                }
                for v in by_product.values()
            ]
            snap.litros_total = round(snap.litros_total, 2)
            snap.faturamento_rs = round(snap.faturamento_rs, 2)
            snap.mensagem = f"{snap.qtd_abastecimentos} abastecimentos no dia"
            logger.info(
                "Vendas reais empresa=%s litros=%.2f fat=%.2f qtd=%s",
                empresa_codigo,
                snap.litros_total,
                snap.faturamento_rs,
                snap.qtd_abastecimentos,
            )
            return snap
        except Exception as exc:
            logger.exception("Erro vendas reais empresa=%s: %s", empresa_codigo, exc)
            snap.sucesso = False
            snap.mensagem = str(exc)
            return snap

    async def get_tank_levels(self, empresa_codigo: int) -> TankLevelSnapshot:
        """Volume físico atual e capacidade máxima por tanque."""
        snap = TankLevelSnapshot(empresa_codigo=empresa_codigo)
        client = self._client_for_company(empresa_codigo)
        try:
            resp = await client.call_endpoint(
                "tanque",
                params={"empresaCodigo": empresa_codigo},
            )
            if not resp.success:
                logger.warning(
                    "WebPosto tanque falhou empresa=%s err=%s",
                    empresa_codigo,
                    resp.error,
                )
                snap.sucesso = False
                snap.mensagem = str(resp.error or "Falha ao consultar tanques")
                return snap

            # Isola filial quando o payload de rede mistura empresas
            rows = [
                row
                for row in self._extract_rows(resp.data)
                if int(row.get("empresaCodigo") or row.get("empresa") or empresa_codigo)
                == int(empresa_codigo)
            ]
            geo = BRANCH_GEOCOORDINATES.get(empresa_codigo, {})
            for row in rows:
                volume = float(
                    row.get("estoqueEscritural")
                    or row.get("volumeAtual")
                    or row.get("estoque")
                    or row.get("quantidade")
                    or row.get("volume")
                    or 0
                )
                capacidade = float(
                    row.get("capacidade")
                    or row.get("capacidadeTotal")
                    or row.get("volumeMaximo")
                    or 0
                )
                snap.tanques.append(
                    {
                        "tanque_codigo": int(
                            row.get("tanqueCodigo") or row.get("codigo") or 0
                        ),
                        "produto_codigo": row.get("produtoCodigo")
                        or row.get("produtoLmcCodigo")
                        or row.get("codigoProduto"),
                        "produto_nome": str(
                            row.get("nome")
                            or row.get("produtoDescricao")
                            or row.get("nomeProduto")
                            or row.get("produto")
                            or ""
                        ).strip(),
                        "volume_atual_litros": round(volume, 2),
                        "capacidade_litros": round(capacidade, 2),
                        "ocupacao_pct": round(
                            (volume / capacidade * 100) if capacidade > 0 else 0.0, 1
                        ),
                        "temperatura_c": row.get("temperatura") or row.get("temp"),
                        "latitude": geo.get("latitude"),
                        "longitude": geo.get("longitude"),
                    }
                )
            snap.mensagem = f"{len(snap.tanques)} tanques lidos"
            logger.info(
                "Tanques reais empresa=%s qtd=%s",
                empresa_codigo,
                len(snap.tanques),
            )
            return snap
        except Exception as exc:
            logger.exception("Erro tanques reais empresa=%s: %s", empresa_codigo, exc)
            snap.sucesso = False
            snap.mensagem = str(exc)
            return snap

    async def get_weighted_avg_cost(
        self,
        empresa_codigo: int,
        dias_lookback: int = 30,
    ) -> WeightedCostSnapshot:
        """CPM do combustível: produto_combustivel + notas de entrada (quando disponível)."""
        snap = WeightedCostSnapshot(empresa_codigo=empresa_codigo)
        custos: dict[str, dict[str, Any]] = {}
        client = self._client_for_company(empresa_codigo)

        try:
            # 1) Cadastro combustível / custo médio registrado
            resp = await client.call_endpoint(
                "produto_combustivel",
                params={"empresaCodigo": empresa_codigo},
            )
            if resp.success:
                for row in self._extract_rows(resp.data):
                    codigo = str(
                        row.get("produtoCodigo")
                        or row.get("codigo")
                        or row.get("codigoProduto")
                        or ""
                    )
                    if not codigo:
                        continue
                    custo = float(
                        row.get("precoCusto")
                        or row.get("custoMedio")
                        or row.get("custoMedioPonderado")
                        or row.get("custo")
                        or 0
                    )
                    nome = str(
                        row.get("produtoDescricao")
                        or row.get("descricao")
                        or row.get("nome")
                        or f"Produto {codigo}"
                    ).strip()
                    if custo > 0:
                        custos[codigo] = {
                            "produto_codigo": codigo,
                            "produto_nome": nome,
                            "cpm_rs": round(custo, 4),
                            "origem": "produto_combustivel",
                        }
            else:
                logger.warning(
                    "produto_combustivel falhou empresa=%s err=%s",
                    empresa_codigo,
                    resp.error,
                )

            # 2) Enriquece/override com notas de entrada / estoque período
            await self._enrich_cost_from_invoices(
                empresa_codigo=empresa_codigo,
                dias_lookback=dias_lookback,
                custos=custos,
                client=client,
            )

            # 3) Fallback CompanySettings quando NF/produto sem CPM
            settings = self._settings.get_settings(empresa_codigo)
            meta = settings.metadata or {}
            fallback_map = meta.get("custo_fallback_por_produto") or {}
            for pricing in settings.precos_produtos:
                codigo = str(pricing.produto_codigo)
                if codigo in custos:
                    continue
                custo_fb = float(pricing.custo_aquisicao_rs or 0)
                if custo_fb <= 0 and isinstance(fallback_map, dict):
                    custo_fb = float(fallback_map.get(codigo) or 0)
                if custo_fb <= 0:
                    prod = self._settings.get_product_config(empresa_codigo, codigo)
                    custo_fb = float(prod.custo_base) if prod else 0.0
                if custo_fb > 0:
                    custos[codigo] = {
                        "produto_codigo": codigo,
                        "produto_nome": codigo,
                        "cpm_rs": round(custo_fb, 4),
                        "origem": "company_settings_fallback",
                    }

            # 4) Sincroniza CompanySettings (preços dinâmicos)
            for codigo, item in custos.items():
                if item.get("origem") != "company_settings_fallback":
                    self._settings.update_product_pricing(
                        empresa_codigo,
                        codigo,
                        custo_aquisicao=item["cpm_rs"],
                    )

            snap.custos = list(custos.values())
            if not snap.custos:
                snap.sucesso = False
                snap.mensagem = "Nenhum CPM encontrado (webPosto + fallback settings)"
                snap.fonte = "sem_dados"
            else:
                snap.mensagem = f"{len(snap.custos)} produtos com CPM"
                snap.fonte = "webposto+settings"
            return snap
        except Exception as exc:
            logger.exception("Erro CPM empresa=%s: %s", empresa_codigo, exc)
            snap.sucesso = False
            snap.mensagem = str(exc)
            return snap

    async def _enrich_cost_from_invoices(
        self,
        empresa_codigo: int,
        dias_lookback: int,
        custos: dict[str, dict[str, Any]],
        client: Any | None = None,
    ) -> None:
        """Tenta calcular CPM a partir de NOTA_FISCAL_ENTRADA (quando permitido)."""
        end = date.today()
        start = end - timedelta(days=max(1, dias_lookback))
        params = {
            "dataInicial": start.isoformat(),
            "dataFinal": end.isoformat(),
            "empresaCodigo": empresa_codigo,
        }
        wp_client = client or self._client_for_company(empresa_codigo)

        from src.gateway import webposto_client as wp_mod

        for endpoint_key in ("nota_fiscal_entrada", "estoque_periodo"):
            if endpoint_key not in wp_mod.ENDPOINTS:
                continue
            try:
                resp = await wp_client.call_endpoint(endpoint_key, params=params)
                if not resp.success:
                    logger.info(
                        "Enriquecimento CPM via %s indisponível empresa=%s: %s",
                        endpoint_key,
                        empresa_codigo,
                        resp.error,
                    )
                    continue

                agg: dict[str, dict[str, float]] = defaultdict(
                    lambda: {"litros": 0.0, "valor": 0.0}
                )
                enriched = 0
                for row in self._extract_rows(resp.data):
                    codigo = str(
                        row.get("produtoCodigo")
                        or row.get("codigoProduto")
                        or row.get("produto")
                        or ""
                    )
                    litros = float(
                        row.get("quantidade")
                        or row.get("quantidadeLitros")
                        or row.get("litros")
                        or 0
                    )
                    valor = float(
                        row.get("valorTotal")
                        or row.get("valor")
                        or row.get("total")
                        or 0
                    )
                    unit = float(
                        row.get("precoUnitario")
                        or row.get("precoCusto")
                        or row.get("valorUnitario")
                        or 0
                    )
                    if litros > 0 and valor <= 0 and unit > 0:
                        valor = litros * unit
                    if not codigo or litros <= 0 or valor <= 0:
                        continue
                    agg[codigo]["litros"] += litros
                    agg[codigo]["valor"] += valor

                for codigo, totals in agg.items():
                    if totals["litros"] <= 0:
                        continue
                    cpm = round(totals["valor"] / totals["litros"], 4)
                    nome = custos.get(codigo, {}).get("produto_nome") or f"Produto {codigo}"
                    custos[codigo] = {
                        "produto_codigo": codigo,
                        "produto_nome": nome,
                        "cpm_rs": cpm,
                        "origem": endpoint_key,
                        "litros_periodo": round(totals["litros"], 2),
                    }
                    enriched += 1

                if enriched:
                    return
            except Exception as exc:
                logger.warning(
                    "Falha ao enriquecer CPM via %s empresa=%s: %s",
                    endpoint_key,
                    empresa_codigo,
                    exc,
                )

    async def get_operational_bundle(self, empresa_codigo: int) -> dict[str, Any]:
        """Pacote único para painéis preditivos/compras."""
        sales = await self.get_realtime_sales(empresa_codigo)
        tanks = await self.get_tank_levels(empresa_codigo)
        costs = await self.get_weighted_avg_cost(empresa_codigo)
        settings = self._settings.get_settings(empresa_codigo)
        geo = BRANCH_GEOCOORDINATES.get(empresa_codigo)

        return {
            "empresa_codigo": empresa_codigo,
            "empresa_nome": settings.empresa_nome,
            "geo": geo,
            "vendas_dia": {
                "sucesso": sales.sucesso,
                "data": sales.data,
                "litros_total": sales.litros_total,
                "faturamento_rs": sales.faturamento_rs,
                "qtd_abastecimentos": sales.qtd_abastecimentos,
                "por_produto": sales.por_produto,
                "fonte": sales.fonte,
                "mensagem": sales.mensagem,
            },
            "tanques": {
                "sucesso": tanks.sucesso,
                "itens": tanks.tanques,
                "fonte": tanks.fonte,
                "mensagem": tanks.mensagem,
            },
            "cpm": {
                "sucesso": costs.sucesso,
                "itens": costs.custos,
                "fonte": costs.fonte,
                "mensagem": costs.mensagem,
            },
        }


_webposto_integration: WebPostoIntegrationService | None = None


def get_webposto_integration_service() -> WebPostoIntegrationService:
    global _webposto_integration
    if _webposto_integration is None:
        _webposto_integration = WebPostoIntegrationService()
    return _webposto_integration
