from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
import re
from typing import Any

from src.domain.entities.filial_master import filial_name_lookup
from src.gateway.webposto_client import WebPostoClient
from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse


FILIAIS = filial_name_lookup()


@dataclass(frozen=True)
class FuelAnalyticsFilters:
    data_inicial: str
    data_final: str
    empresa_codigo: int | None = None


class FuelAnalyticsService:
    """Analitico executivo de combustiveis baseado em CONSULTAR_LMC_REDE."""

    def __init__(self, client: WebPostoClient) -> None:
        self.client = client

    @staticmethod
    def _rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            for key in ("resultados", "data", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]
        return []

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        if value is None:
            return Decimal("0")
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("0")

    @staticmethod
    def _extract_litros(row: dict[str, Any]) -> Decimal:
        liters = row.get("saida")
        if liters is None:
            liters = row.get("venda")
        if liters is None:
            bicos = row.get("lmcBico")
            if isinstance(bicos, dict):
                liters = bicos.get("venda")
            elif isinstance(bicos, list):
                total = Decimal("0")
                for bico in bicos:
                    if not isinstance(bico, dict):
                        continue
                    total += FuelAnalyticsService._to_decimal(bico.get("venda"))
                liters = total
        return FuelAnalyticsService._to_decimal(liters)

    @staticmethod
    def _extract_product_code(row: dict[str, Any]) -> int | None:
        raw = row.get("produtoCodigo")
        if isinstance(raw, list):
            for item in raw:
                if item in (None, ""):
                    continue
                raw = item
                break
            else:
                raw = None

        if raw in (None, ""):
            raw = row.get("produtoLmcCodigo")

        if raw in (None, ""):
            return None

        if isinstance(raw, int):
            return raw
        if isinstance(raw, float):
            return int(raw)

        text = str(raw).strip()
        if text.isdigit():
            return int(text)

        digits = re.sub(r"\D", "", text)
        if digits:
            return int(digits)
        return None

    @staticmethod
    def _extract_data(row: dict[str, Any]) -> str:
        for key in ("data", "dataMovimento", "dataLmc", "dia"):
            if row.get(key):
                return str(row.get(key))
        return ""

    @staticmethod
    def _company_name(empresa_codigo: int | None, raw_name: str | None) -> str:
        if raw_name:
            return raw_name
        if empresa_codigo is None:
            return "Filial nao identificada"
        return FILIAIS.get(empresa_codigo, f"Filial {empresa_codigo}")

    @staticmethod
    def _normalize_category(name: str) -> str:
        fuel = name.lower()
        if "diesel" in fuel and "s10" in fuel:
            return "Diesel S10"
        if "diesel" in fuel and "s500" in fuel:
            return "Diesel S500"
        if "diesel" in fuel:
            return "Diesel"
        if "etanol" in fuel or "alcool" in fuel:
            return "Etanol"
        if "gasolina" in fuel:
            return "Gasolina"
        return "Outros"

    @staticmethod
    def _clean_product_name(value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if text.lower() in {"none", "null", "undefined"}:
            return ""
        return text

    @staticmethod
    def _to_float(value: Decimal) -> float:
        return round(float(value), 3)

    async def _product_name_map(self, filtros: FuelAnalyticsFilters, empresas: set[int]) -> tuple[dict[int, str], dict[int, str]]:
        by_code: dict[int, str] = {}
        by_lmc_code: dict[int, str] = {}
        for empresa_codigo in sorted(empresas):
            response = await self.client.call_endpoint(
                "produto",
                params={
                    "dataInicial": filtros.data_inicial,
                    "dataFinal": filtros.data_final,
                    "empresaCodigo": empresa_codigo,
                },
            )
            if not response.success:
                continue
            for produto in self._rows(response.data):
                codigo = produto.get("produtoCodigo") or produto.get("codigo")
                if codigo is None:
                    continue
                try:
                    codigo_int = int(codigo)
                except Exception:
                    continue
                nome = self._clean_product_name(produto.get("nome") or produto.get("descricao"))
                if nome and codigo_int not in by_code:
                    by_code[codigo_int] = nome
                lmc_codigo = produto.get("produtoLmcCodigo")
                try:
                    lmc_codigo_int = int(lmc_codigo)
                except Exception:
                    lmc_codigo_int = None
                if nome and lmc_codigo_int is not None and lmc_codigo_int not in by_lmc_code:
                    by_lmc_code[lmc_codigo_int] = nome
        return by_code, by_lmc_code

    async def _fetch_lmc_rows(self, filtros: FuelAnalyticsFilters) -> WebPostoResponse:
        params: dict[str, Any] = {
            "dataInicial": filtros.data_inicial,
            "dataFinal": filtros.data_final,
        }
        if filtros.empresa_codigo is not None:
            params["empresaCodigo"] = filtros.empresa_codigo

        lmc_resp = await self.client.call_endpoint("lmc_rede", params=params)
        if not lmc_resp.success:
            return lmc_resp

        rows = self._rows(lmc_resp.data)
        if filtros.empresa_codigo is not None:
            rows = [r for r in rows if int(r.get("empresaCodigo") or 0) == filtros.empresa_codigo]

        return WebPostoResponse.ok(rows)

    async def _build_groupings(self, filtros: FuelAnalyticsFilters) -> WebPostoResponse:
        rows_resp = await self._fetch_lmc_rows(filtros)
        if not rows_resp.success:
            return rows_resp

        rows = rows_resp.data if isinstance(rows_resp.data, list) else []
        empresas = set()
        for row in rows:
            codigo = row.get("empresaCodigo")
            try:
                if codigo is not None:
                    empresas.add(int(codigo))
            except Exception:
                continue

        product_names, product_names_by_lmc = await self._product_name_map(filtros, empresas)

        by_company: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
        by_product: dict[int, dict[str, Any]] = {}
        by_company_product: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))
        by_company_product_date: dict[tuple[int, int, str], Decimal] = defaultdict(lambda: Decimal("0"))
        litros_total = Decimal("0")

        for row in rows:
            empresa_codigo_raw = row.get("empresaCodigo")
            produto_codigo = self._extract_product_code(row)
            if empresa_codigo_raw is None or produto_codigo is None:
                continue

            try:
                empresa_codigo = int(empresa_codigo_raw)
            except Exception:
                continue

            litros = self._extract_litros(row)
            if litros <= 0:
                continue

            data_ref = self._extract_data(row)
            nome_produto = ""
            for candidate in (
                row.get("produtoNome"),
                row.get("produto"),
                row.get("descricaoProduto"),
                product_names.get(produto_codigo),
            ):
                nome_produto = self._clean_product_name(candidate)
                if nome_produto:
                    break
            if not nome_produto:
                lmc_codigo = row.get("produtoLmcCodigo")
                try:
                    lmc_codigo_int = int(lmc_codigo) if lmc_codigo is not None else None
                except Exception:
                    lmc_codigo_int = None
                if lmc_codigo_int is not None:
                    nome_produto = self._clean_product_name(product_names_by_lmc.get(lmc_codigo_int))
            if not nome_produto:
                nome_produto = f"Produto {produto_codigo}"

            litros_total += litros
            by_company[empresa_codigo] += litros
            by_company_product[(empresa_codigo, produto_codigo)] += litros
            by_company_product_date[(empresa_codigo, produto_codigo, data_ref)] += litros

            if produto_codigo not in by_product:
                by_product[produto_codigo] = {
                    "produtoCodigo": produto_codigo,
                    "combustivel": nome_produto,
                    "categoria": self._normalize_category(nome_produto),
                    "litros": Decimal("0"),
                }
            by_product[produto_codigo]["litros"] += litros

        filiais = []
        for empresa_codigo, litros in sorted(by_company.items(), key=lambda item: item[1], reverse=True):
            participacao = (litros / litros_total * 100) if litros_total > 0 else Decimal("0")
            filiais.append(
                {
                    "empresaCodigo": empresa_codigo,
                    "nomeFilial": self._company_name(empresa_codigo, None),
                    "litros": self._to_float(litros),
                    "participacao": round(float(participacao), 2),
                }
            )

        combustiveis = []
        for _, item in sorted(by_product.items(), key=lambda pair: pair[1]["litros"], reverse=True):
            litros = item["litros"]
            participacao = (litros / litros_total * 100) if litros_total > 0 else Decimal("0")
            combustiveis.append(
                {
                    "produtoCodigo": item["produtoCodigo"],
                    "combustivel": item["combustivel"],
                    "categoria": item["categoria"],
                    "litros": self._to_float(litros),
                    "participacao": round(float(participacao), 2),
                }
            )

        ranking = []
        for idx, filial in enumerate(filiais[:10], start=1):
            ranking.append({"posicao": idx, **filial})

        detalhes = []
        for (empresa_codigo, produto_codigo, data_ref), litros in sorted(
            by_company_product_date.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            nome_produto = by_product.get(produto_codigo, {}).get("combustivel", f"Produto {produto_codigo}")
            participacao = (litros / litros_total * 100) if litros_total > 0 else Decimal("0")
            detalhes.append(
                {
                    "empresaCodigo": empresa_codigo,
                    "nomeFilial": self._company_name(empresa_codigo, None),
                    "produtoCodigo": produto_codigo,
                    "combustivel": nome_produto,
                    "data": data_ref,
                    "litros": self._to_float(litros),
                    "participacao": round(float(participacao), 2),
                }
            )

        return WebPostoResponse.ok(
            {
                "litrosTotal": self._to_float(litros_total),
                "filiais": filiais,
                "combustiveis": combustiveis,
                "ranking": ranking,
                "detalhes": detalhes,
                "agrupamento": {
                    "empresaCodigo": True,
                    "produtoCodigo": True,
                    "data": True,
                },
                "consistencia": {
                    "somaCombustiveis": round(sum(float(i["litros"]) for i in combustiveis), 3),
                    "somaFiliais": round(sum(float(i["litros"]) for i in filiais), 3),
                },
            }
        )

    async def get_fuel_summary(self, filtros: FuelAnalyticsFilters) -> WebPostoResponse:
        return await self._build_groupings(filtros)

    async def get_fuel_by_company(self, filtros: FuelAnalyticsFilters) -> WebPostoResponse:
        summary = await self._build_groupings(filtros)
        if not summary.success:
            return summary
        return WebPostoResponse.ok(summary.data.get("filiais", []))

    async def get_fuel_by_product(self, filtros: FuelAnalyticsFilters) -> WebPostoResponse:
        summary = await self._build_groupings(filtros)
        if not summary.success:
            return summary
        return WebPostoResponse.ok(summary.data.get("combustiveis", []))

    async def get_fuel_ranking(self, filtros: FuelAnalyticsFilters) -> WebPostoResponse:
        summary = await self._build_groupings(filtros)
        if not summary.success:
            return summary
        return WebPostoResponse.ok(summary.data.get("ranking", []))
