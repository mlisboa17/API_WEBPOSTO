from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.money_normalizer import normalize_webposto_money
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService


@dataclass(frozen=True)
class DataQualityFilters:
    data_inicial: str
    data_final: str
    empresa_codigo: int | None = None
    filial: str | None = None
    centro_custo: str | None = None
    tipo_produto: str | None = None
    grupo_produto: str | None = None


class DataQualityService:
    def __init__(self, overview: NetworkFinancialOverviewService) -> None:
        self._overview = overview

    @staticmethod
    def _parse_date(value: Any) -> datetime | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text[:10])
        except Exception:
            return None

    @staticmethod
    def _status_from_score(score: float) -> str:
        if score >= 95:
            return "ok"
        if score >= 90:
            return "warning"
        return "danger"

    @staticmethod
    def _safe_company_code(value: Any) -> int | None:
        try:
            return int(value)
        except Exception:
            return None

    @staticmethod
    def _is_missing(value: Any) -> bool:
        return value is None or str(value).strip() == ""

    @staticmethod
    def _value_is_invalid(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        try:
            normalized = normalize_webposto_money(value)
        except Exception:
            return True
        return normalized < Decimal("0")

    @staticmethod
    def _expense_key(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            row.get("empresaCodigo"),
            str(row.get("data") or row.get("dataMovimento") or ""),
            str(row.get("valor") or row.get("valorDespesa") or row.get("valorTotal") or ""),
            str(row.get("planoConta") or row.get("descricaoPlanoConta") or ""),
            str(row.get("contaCodigo") or row.get("planoContaCodigo") or ""),
        )

    @staticmethod
    def _sale_key(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            row.get("empresaCodigo"),
            row.get("vendaCodigo") or row.get("codigo"),
            str(row.get("data") or row.get("dataVenda") or row.get("dataMovimento") or ""),
            str(row.get("totalVenda") or row.get("valorTotal") or row.get("valor") or ""),
        )

    @staticmethod
    def _account_key(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            row.get("empresaCodigo"),
            str(row.get("fornecedor") or row.get("fornecedorNome") or ""),
            str(row.get("vencimento") or ""),
            str(row.get("valor") or row.get("valorTotal") or ""),
        )

    @classmethod
    def evaluate_records(
        cls,
        expenses_rows: list[dict[str, Any]],
        sales_rows: list[dict[str, Any]],
        sale_item_rows: list[dict[str, Any]],
        accounts_rows: list[dict[str, Any]],
        mapped_company_codes: set[int],
        mapped_filiais_by_company: dict[int, str],
        mapped_product_codes: set[int],
        data_inicial: str,
        data_final: str,
        fuel_product_codes: set[int] | None = None,
    ) -> dict[str, Any]:
        periodo_inicial = cls._parse_date(data_inicial)
        periodo_final = cls._parse_date(data_final)

        total_registros = len(expenses_rows) + len(sales_rows) + len(sale_item_rows) + len(accounts_rows)

        duplicated = 0
        empresas_nao_mapeadas = 0
        filiais_nao_mapeadas = 0
        produtos_nao_mapeados = 0
        despesas_sem_conta = 0
        vendas_sem_filial = 0
        valores_invalidos = 0
        datas_invalidas = 0
        formas_pagamento_nao_mapeadas = 0
        contas_pagar_sem_vencimento = 0

        seen_keys: set[tuple[str, tuple[Any, ...]]] = set()

        def _check_duplicate(kind: str, key: tuple[Any, ...]) -> bool:
            nonlocal duplicated
            dedupe_key = (kind, key)
            if dedupe_key in seen_keys:
                duplicated += 1
                return True
            seen_keys.add(dedupe_key)
            return False

        for row in expenses_rows:
            _check_duplicate("expense", cls._expense_key(row))
            company_code = cls._safe_company_code(row.get("empresaCodigo"))
            if company_code is None or company_code not in mapped_company_codes:
                empresas_nao_mapeadas += 1

            filial_nome = str(row.get("filial") or mapped_filiais_by_company.get(company_code or -1, "")).strip()
            if not filial_nome:
                filiais_nao_mapeadas += 1

            if cls._is_missing(row.get("contaCodigo")) and cls._is_missing(row.get("planoContaCodigo")) and cls._is_missing(row.get("planoConta")):
                despesas_sem_conta += 1

            if cls._value_is_invalid(row.get("valor") or row.get("valorDespesa") or row.get("valorTotal")):
                valores_invalidos += 1

            raw_date = row.get("data") or row.get("dataMovimento")
            parsed = cls._parse_date(raw_date)
            if parsed is None:
                datas_invalidas += 1
            elif periodo_inicial and periodo_final and (parsed < periodo_inicial or parsed > periodo_final):
                datas_invalidas += 1

        for row in sales_rows:
            _check_duplicate("sale", cls._sale_key(row))
            company_code = cls._safe_company_code(row.get("empresaCodigo"))
            if company_code is None or company_code not in mapped_company_codes:
                empresas_nao_mapeadas += 1

            filial_nome = str(row.get("filial") or mapped_filiais_by_company.get(company_code or -1, "")).strip()
            if not filial_nome:
                filiais_nao_mapeadas += 1
                vendas_sem_filial += 1

            if cls._value_is_invalid(row.get("totalVenda") or row.get("valorTotal") or row.get("valor")):
                valores_invalidos += 1

            raw_date = row.get("data") or row.get("dataVenda") or row.get("dataMovimento")
            parsed = cls._parse_date(raw_date)
            if parsed is None:
                datas_invalidas += 1
            elif periodo_inicial and periodo_final and (parsed < periodo_inicial or parsed > periodo_final):
                datas_invalidas += 1

            if cls._is_missing(row.get("formaPagamento")) and cls._is_missing(row.get("formaPagamentoCodigo")):
                formas_pagamento_nao_mapeadas += 1

        actual_fuels = fuel_product_codes if fuel_product_codes is not None else mapped_product_codes

        for row in sale_item_rows:
            produto_codigo = row.get("produtoCodigo")
            if cls._is_missing(produto_codigo):
                produtos_nao_mapeados += 1
                continue
            parsed_produto = cls._safe_company_code(produto_codigo)
            if parsed_produto is None:
                produtos_nao_mapeados += 1
            elif actual_fuels and parsed_produto in actual_fuels:
                if parsed_produto not in mapped_product_codes:
                    produtos_nao_mapeados += 1

        for row in accounts_rows:
            _check_duplicate("account", cls._account_key(row))
            company_code = cls._safe_company_code(row.get("empresaCodigo"))
            if company_code is None or company_code not in mapped_company_codes:
                empresas_nao_mapeadas += 1

            filial_nome = str(row.get("filial") or mapped_filiais_by_company.get(company_code or -1, "")).strip()
            if not filial_nome:
                filiais_nao_mapeadas += 1

            if cls._value_is_invalid(row.get("valor") or row.get("valorTotal")):
                valores_invalidos += 1

            vencimento = row.get("vencimento")
            parsed_venc = cls._parse_date(vencimento)
            if cls._is_missing(vencimento):
                contas_pagar_sem_vencimento += 1
                datas_invalidas += 1
            elif parsed_venc is None:
                datas_invalidas += 1

        invalidos = (
            duplicated
            + empresas_nao_mapeadas
            + filiais_nao_mapeadas
            + produtos_nao_mapeados
            + despesas_sem_conta
            + vendas_sem_filial
            + valores_invalidos
            + datas_invalidas
            + formas_pagamento_nao_mapeadas
            + contas_pagar_sem_vencimento
        )

        if total_registros == 0:
            score = 100.0
            validos = 0
        else:
            validos = max(total_registros - invalidos, 0)
            score = round((validos / total_registros) * 100, 2)

        status = cls._status_from_score(score)

        return {
            "score": score,
            "status": status,
            "summary": {
                "totalRegistros": total_registros,
                "validos": validos,
                "invalidos": invalidos,
            },
            "issues": {
                "duplicados": duplicated,
                "filiaisNaoMapeadas": filiais_nao_mapeadas,
                "empresasNaoMapeadas": empresas_nao_mapeadas,
                "produtosNaoMapeados": produtos_nao_mapeados,
                "despesasSemConta": despesas_sem_conta,
                "vendasSemFilial": vendas_sem_filial,
                "valoresInvalidos": valores_invalidos,
                "datasInvalidas": datas_invalidas,
                "formasPagamentoNaoMapeadas": formas_pagamento_nao_mapeadas,
                "contasPagarSemVencimento": contas_pagar_sem_vencimento,
            },
            "totalRegistros": total_registros,
            "validos": validos,
            "invalidos": invalidos,
            "duplicados": duplicated,
            "filiaisNaoMapeadas": filiais_nao_mapeadas,
            "empresasNaoMapeadas": empresas_nao_mapeadas,
            "produtosNaoMapeados": produtos_nao_mapeados,
            "despesasSemConta": despesas_sem_conta,
            "vendasSemFilial": vendas_sem_filial,
            "valoresInvalidos": valores_invalidos,
            "datasInvalidas": datas_invalidas,
            "formasPagamentoNaoMapeadas": formas_pagamento_nao_mapeadas,
            "contasPagarSemVencimento": contas_pagar_sem_vencimento,
            "lineage": [],
        }

    async def get_data_quality(self, filters: DataQualityFilters) -> WebPostoResponse:
        companies_resp = await self._overview.get_companies()
        if not companies_resp.success:
            return companies_resp

        companies = (companies_resp.data or {}).get("data") or []
        mapped_company_codes: set[int] = set()
        mapped_filiais_by_company: dict[int, str] = {}
        for company in companies:
            code = self._safe_company_code(company.get("empresaCodigo"))
            if code is None:
                continue
            mapped_company_codes.add(code)
            mapped_filiais_by_company[code] = str(company.get("nome") or "").strip()

        # Busca dados de todas as empresas (sem filtro de empresa_codigo na chamada ao
        # WebPosto, pois o campo empresaCodigo da API bruta pode usar chave diferente de
        # "empresaCodigo").  O filtro por empresa é aplicado nos resultados depois.
        if filters.empresa_codigo is not None:
            all_codes = [filters.empresa_codigo]
        else:
            all_codes = sorted(mapped_company_codes)

        expenses_rows: list[dict[str, Any]] = []
        sales_rows: list[dict[str, Any]] = []
        sale_item_rows: list[dict[str, Any]] = []
        accounts_rows: list[dict[str, Any]] = []
        mapped_product_codes: set[int] = set()
        fuel_product_codes: set[int] = set()

        from src.services.network_financial_overview_service import is_active_fuel_product

        for company_code in all_codes:
            company_filters = FinancialOverviewFilters(
                data_inicial=filters.data_inicial,
                data_final=filters.data_final,
                empresa_codigo=company_code,
                centro_custo=filters.centro_custo,
            )

            expenses_resp = await self._overview.get_financial_expenses(company_filters, page=1, limit=5000)
            if not expenses_resp.success:
                return expenses_resp
            expenses_rows.extend((expenses_resp.data or {}).get("data") or [])

            accounts_resp = await self._overview.get_accounts_payable(company_filters, page=1, limit=5000)
            if not accounts_resp.success:
                return accounts_resp
            accounts_rows.extend((accounts_resp.data or {}).get("data") or [])

            sales_resp = await self._overview.get_sales(company_filters, page=1, limit=5000)
            if not sales_resp.success:
                return sales_resp
            sales_rows.extend((sales_resp.data or {}).get("data") or [])

            # Reuso dos mesmos dados de integracao de vendas para checks de produto/forma pagamento.
            raw_sales_resp = await self._overview._fetch_vendas_produtos(company_filters, company_code)
            if raw_sales_resp.success:
                raw_sales_data = raw_sales_resp.data or {}
                sale_item_rows.extend(self._overview._rows(raw_sales_data.get("venda_item")))

            produto_resp = await self._overview.client.call_endpoint(
                "produto",
                params={
                    "dataInicial": filters.data_inicial,
                    "dataFinal": filters.data_final,
                    "empresaCodigo": company_code,
                },
            )
            if produto_resp.success:
                for prod in self._overview._rows(produto_resp.data):
                    codigo = self._safe_company_code(prod.get("produtoCodigo") or prod.get("codigo"))
                    if codigo is not None:
                        if is_active_fuel_product(prod):
                            mapped_product_codes.add(codigo)
                        # Force active status to check if it represents a fuel product general catalog item
                        forced_active = {**prod, "ativo": True, "status": "ativo", "situacao": "ativo", "situação": "ativo"}
                        if is_active_fuel_product(forced_active):
                            fuel_product_codes.add(codigo)

        # Filtro por empresa_codigo (pos-busca, seguro independente da chave interna da API)
        if filters.empresa_codigo is not None:
            target_code = filters.empresa_codigo
            expenses_rows = [r for r in expenses_rows if self._safe_company_code(r.get("empresaCodigo")) == target_code]
            sales_rows = [r for r in sales_rows if self._safe_company_code(r.get("empresaCodigo")) == target_code]
            accounts_rows = [r for r in accounts_rows if self._safe_company_code(r.get("empresaCodigo")) == target_code]
            sale_item_rows = [r for r in sale_item_rows if self._safe_company_code(r.get("empresaCodigo")) == target_code]

        if filters.filial:
            filt = filters.filial.casefold()
            expenses_rows = [r for r in expenses_rows if filt in str(r.get("filial") or "").casefold()]
            sales_rows = [r for r in sales_rows if filt in str(r.get("filial") or "").casefold()]
            accounts_rows = [r for r in accounts_rows if filt in str(r.get("filial") or "").casefold()]

        quality = self.evaluate_records(
            expenses_rows=expenses_rows,
            sales_rows=sales_rows,
            sale_item_rows=sale_item_rows,
            accounts_rows=accounts_rows,
            mapped_company_codes=mapped_company_codes,
            mapped_filiais_by_company=mapped_filiais_by_company,
            mapped_product_codes=mapped_product_codes,
            data_inicial=filters.data_inicial,
            data_final=filters.data_final,
            fuel_product_codes=fuel_product_codes,
        )

        quality["lineage"] = [
            "endpoint=/v1/financial/companies|fonte=/INTEGRACAO/EMPRESAS|campo=empresaCodigo",
            "endpoint=/v1/financial/expenses|fonte=/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE|campos=data,valor,planoConta",
            "endpoint=/v1/financial/accounts-payable|fonte=/INTEGRACAO/TITULO_PAGAR|campos=vencimento,valor",
            "endpoint=/v1/sales|fonte=/INTEGRACAO/VENDA+VENDA_ITEM+VENDA_FORMA_PAGAMENTO|campos=vendaCodigo,totalVenda,formaPagamento",
        ]

        return WebPostoResponse.ok(quality)
