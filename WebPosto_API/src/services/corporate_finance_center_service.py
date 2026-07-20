"""Centro Financeiro Corporativo — agregadores read-only (F01)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.logos_expense_classifier import VALID_CATEGORIES, classify_logos_expense_full
from src.services.logos_expense_classifier_v3 import classify_with_all_versions
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.money_normalizer import normalize_webposto_account_value, normalize_webposto_expense_value
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService

LOGGER = logging.getLogger(__name__)


def build_finance_center_snapshot_key(
    module: str,
    data_inicial: str,
    data_final: str,
    empresa_codigo: str | int | None,
) -> str:
    suffix = empresa_snapshot_suffix(empresa_codigo)
    return f"finance:center:{module}:{data_inicial}:{data_final}:{suffix}"


@dataclass(frozen=True)
class FinanceCenterMeta:
    data_inicial: str
    data_final: str
    empresa_codigo: str | int | None
    fetch_ms: dict[str, float] | None = None

    def snapshot_key(self, module: str) -> str:
        return build_finance_center_snapshot_key(module, self.data_inicial, self.data_final, self.empresa_codigo)


class CorporateFinanceCenterService:
    """Agrega fontes financeiras separadas — nunca soma fatos distintos."""

    def __init__(self, overview: NetworkFinancialOverviewService) -> None:
        self._overview = overview
        self._client = overview.client

    @staticmethod
    def _rows(payload: object) -> list[dict[str, Any]]:
        return NetworkFinancialOverviewService._rows(payload)

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except Exception:
            return Decimal("0")

    @staticmethod
    def _decimal_str(value: Decimal | int | float | str) -> str:
        return str(Decimal(str(value)).quantize(Decimal("0.01")))

    @staticmethod
    def _paginate(items: list[Any], page: int, limit: int) -> tuple[list[Any], int]:
        page = max(page, 1)
        limit = min(max(limit, 1), 500)
        start = (page - 1) * limit
        return items[start : start + limit], len(items)

    def _matches_empresa(self, row: dict[str, Any], filters: FinancialOverviewFilters) -> bool:
        return self._overview._expense_matches_empresa(row, filters)

    def _bucket_summary(self, buckets: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for name, rows in buckets.items():
            total = sum(self._to_decimal(r.get("valor")) for r in rows)
            out[name] = {"count": len(rows), "valor": self._decimal_str(total)}
        return out

    def _with_categoria(self, expense: dict[str, Any]) -> dict[str, Any]:
        raw = expense.get("raw") or {}
        desc = str(expense.get("planoConta") or raw.get("descricaoDocumento") or "")
        plano = str(raw.get("planoContaGerencialDescricao") or "")
        fornecedor = str(raw.get("fornecedor") or raw.get("fornecedorNome") or "")
        centro = str(expense.get("centroCusto") or "")
        classified = classify_with_all_versions(
            desc,
            plano,
            fornecedor,
            centro,
            desc,
            plano_conta_gerencial_codigo=raw.get("planoContaGerencialCodigo") or expense.get("planoContaCodigo"),
            centro_custo_codigo=raw.get("centroCustoCodigo"),
        )
        item = dict(expense)
        item["categoriaLogos"] = classified["categoriaLogos"]
        item["categoriaLogosV2"] = classified["categoriaLogosV2"]
        item["categoriaLogosV3"] = classified["categoriaLogosV3"]
        item["confidenceScore"] = classified["confidenceScore"]
        item["confidenceScoreV3"] = classified["confidenceScoreV3"]
        item["confidenceBand"] = classified["confidenceBand"]
        item["classificationSource"] = classified["classificationSource"]
        return item

    def _filter_expenses(
        self,
        expenses: list[dict[str, Any]],
        filters: FinancialOverviewFilters,
    ) -> list[dict[str, Any]]:
        categoria_filter = filters.categoria_logos
        result: list[dict[str, Any]] = []
        for row in expenses:
            item = self._with_categoria(row)
            if categoria_filter and item["categoriaLogos"].casefold() != categoria_filter.casefold():
                continue
            result.append(item)
        return result

    async def _fetch_movimento_conta_all(self, filters: FinancialOverviewFilters) -> tuple[list[dict[str, Any]], float]:
        import time

        t0 = time.perf_counter()
        resultados: list[dict[str, Any]] = []
        ultimo_codigo: Any = None
        params_base: dict[str, Any] = {
            "dataInicial": filters.data_inicial,
            "dataFinal": filters.data_final,
        }
        for _ in range(10):
            params = dict(params_base)
            if ultimo_codigo is not None:
                params["ultimoCodigo"] = ultimo_codigo
            resp = await self._client.call_endpoint("movimento_conta", params=params)
            if not resp.success:
                break
            batch = self._rows(resp.data)
            resultados.extend(batch)
            payload = resp.data
            if not isinstance(payload, dict):
                break
            novo = payload.get("ultimoCodigo")
            if novo is None or novo == ultimo_codigo or not batch:
                break
            ultimo_codigo = novo
        ms = round((time.perf_counter() - t0) * 1000, 1)
        filtered = [r for r in resultados if self._matches_empresa(r, filters)]
        return filtered, ms

    async def _fetch_titulo_pagar_all(self, filters: FinancialOverviewFilters) -> tuple[list[dict[str, Any]], float]:
        import time

        t0 = time.perf_counter()
        resp = await self._client.call_endpoint(
            "financeiro",
            params={"dataInicial": filters.data_inicial, "dataFinal": filters.data_final},
        )
        ms = round((time.perf_counter() - t0) * 1000, 1)
        if not resp.success:
            return [], ms
        rows = [r for r in self._rows(resp.data) if self._matches_empresa(r, filters)]
        return rows, ms

    async def _fetch_titulo_receber_all(self, filters: FinancialOverviewFilters) -> tuple[list[dict[str, Any]], float]:
        import time

        t0 = time.perf_counter()
        resp = await self._client.call_endpoint(
            "titulo_receber",
            params={"dataInicial": filters.data_inicial, "dataFinal": filters.data_final},
        )
        ms = round((time.perf_counter() - t0) * 1000, 1)
        if not resp.success:
            return [], ms
        rows = [r for r in self._rows(resp.data) if self._matches_empresa(r, filters)]
        return rows, ms

    async def _fetch_caixa_all(self, filters: FinancialOverviewFilters) -> tuple[list[dict], list[dict], float]:
        import time

        t0 = time.perf_counter()
        params = {"dataInicial": filters.data_inicial, "dataFinal": filters.data_final}
        caixa_resp, ap_resp = await asyncio.gather(
            self._client.call_endpoint("caixa", params=params),
            self._client.call_endpoint("caixa_apresentado", params=params),
        )
        ms = round((time.perf_counter() - t0) * 1000, 1)
        caixa = [r for r in self._rows(caixa_resp.data if caixa_resp.success else []) if self._matches_empresa(r, filters)]
        apresentado = [
            r for r in self._rows(ap_resp.data if ap_resp.success else []) if self._matches_empresa(r, filters)
        ]
        return caixa, apresentado, ms

    @staticmethod
    def _is_pago_payable(row: dict[str, Any]) -> bool:
        situacao = str(row.get("situacao") or "").casefold()
        if "pago" in situacao:
            return True
        return bool(row.get("dataPagamento"))

    def _classify_payables(
        self,
        rows: list[dict[str, Any]],
        reference_date: str,
    ) -> dict[str, list[dict[str, Any]]]:
        buckets: dict[str, list[dict[str, Any]]] = {
            "emAberto": [],
            "vencido": [],
            "pago": [],
            "aVencer": [],
        }
        for row in rows:
            valor = normalize_webposto_account_value(row.get("valor"))
            if valor is None:
                continue
            item = {
                "empresaCodigo": row.get("empresaCodigo"),
                "tituloPagarCodigo": row.get("tituloPagarCodigo") or row.get("codigo"),
                "fornecedor": row.get("nomeFornecedor") or row.get("fornecedor") or "",
                "valor": str(valor),
                "vencimento": str(row.get("vencimento") or ""),
                "situacao": str(row.get("situacao") or ""),
            }
            if self._is_pago_payable(row):
                buckets["pago"].append(item)
                continue
            buckets["emAberto"].append(item)
            venc = str(row.get("vencimento") or "")
            if venc and venc < reference_date:
                buckets["vencido"].append(item)
            else:
                buckets["aVencer"].append(item)
        return buckets

    @staticmethod
    def _is_recebido(row: dict[str, Any]) -> bool:
        if row.get("dataPagamento"):
            return True
        pendente = row.get("pendente")
        if isinstance(pendente, bool):
            return not pendente
        situacao = str(row.get("situacao") or "").casefold()
        return "pago" in situacao or "receb" in situacao

    def _classify_receivables(
        self,
        rows: list[dict[str, Any]],
        reference_date: str,
    ) -> dict[str, list[dict[str, Any]]]:
        buckets: dict[str, list[dict[str, Any]]] = {
            "pendente": [],
            "recebido": [],
            "vencido": [],
            "aVencer": [],
        }
        for row in rows:
            valor = normalize_webposto_account_value(row.get("valor"))
            if valor is None:
                continue
            venc = str(row.get("dataVencimento") or row.get("vencimento") or "")
            item = {
                "empresaCodigo": row.get("empresaCodigo"),
                "tituloCodigo": row.get("tituloCodigo") or row.get("codigo"),
                "cliente": row.get("nomeCliente") or row.get("cliente") or "",
                "valor": str(valor),
                "vencimento": venc,
                "pendente": row.get("pendente"),
            }
            if self._is_recebido(row):
                buckets["recebido"].append(item)
                continue
            buckets["pendente"].append(item)
            if venc and venc < reference_date:
                buckets["vencido"].append(item)
            else:
                buckets["aVencer"].append(item)
        return buckets

    def _classify_bank_movements(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        creditos: list[dict[str, Any]] = []
        debitos: list[dict[str, Any]] = []
        tarifas: list[dict[str, Any]] = []
        transferencias: list[dict[str, Any]] = []
        total_credito = Decimal("0")
        total_debito = Decimal("0")

        for row in rows:
            valor = self._to_decimal(row.get("valor"))
            tipo = str(row.get("tipo") or "")
            origem = str(row.get("tipoDocumentoOrigem") or "")
            item = {
                "empresaCodigo": row.get("empresaCodigo"),
                "movimentoContaCodigo": row.get("movimentoContaCodigo") or row.get("codigo"),
                "valor": self._decimal_str(valor),
                "dataMovimento": str(row.get("dataMovimento") or ""),
                "descricao": str(row.get("descricao") or ""),
                "tipo": tipo,
                "tipoDocumentoOrigem": origem,
                "contaCodigo": row.get("contaCodigo"),
            }
            if "crédito" in tipo.casefold() or "credito" in tipo.casefold():
                creditos.append(item)
                total_credito += valor
            elif "débito" in tipo.casefold() or "debito" in tipo.casefold():
                debitos.append(item)
                total_debito += valor
            if origem == "TAXA_TRANSFERENCIA":
                tarifas.append(item)
            if origem == "TRANSFERENCIA_BANCARIA":
                transferencias.append(item)

        return {
            "creditos": {
                "count": len(creditos),
                "valor": self._decimal_str(total_credito),
                "items": creditos,
            },
            "debitos": {
                "count": len(debitos),
                "valor": self._decimal_str(total_debito),
                "items": debitos,
            },
            "tarifas": {
                "count": len(tarifas),
                "valor": self._decimal_str(sum(self._to_decimal(r.get("valor")) for r in tarifas)),
                "items": tarifas,
            },
            "transferencias": {
                "count": len(transferencias),
                "valor": self._decimal_str(sum(self._to_decimal(r.get("valor")) for r in transferencias)),
                "items": transferencias,
            },
            "saldoMovimentado": {
                "creditos": self._decimal_str(total_credito),
                "debitos": self._decimal_str(total_debito),
                "liquido": self._decimal_str(total_credito - total_debito),
            },
            "totalRegistros": len(rows),
        }

    def _aggregate_cash(self, caixa_rows: list[dict], apresentado_rows: list[dict]) -> dict[str, Any]:
        turnos: list[dict[str, Any]] = []
        diferencas: list[dict[str, Any]] = []
        despesa_total = Decimal("0")
        vale_total = Decimal("0")
        emprestimo_total = Decimal("0")

        for row in caixa_rows:
            diff = self._to_decimal(row.get("diferenca"))
            turnos.append(
                {
                    "empresaCodigo": row.get("empresaCodigo"),
                    "caixaCodigo": row.get("caixaCodigo") or row.get("codigo"),
                    "data": str(row.get("data") or row.get("dataMovimento") or ""),
                    "diferenca": self._decimal_str(diff),
                }
            )
            if diff != 0:
                diferencas.append(turnos[-1])

        for row in apresentado_rows:
            despesa_total += self._to_decimal(row.get("despesaApurado"))
            vale_total += self._to_decimal(row.get("valeFunApurado"))
            emprestimo_total += self._to_decimal(row.get("emprestimoApurado"))

        return {
            "turnos": {"count": len(turnos), "items": turnos},
            "diferencas": {"count": len(diferencas), "items": diferencas},
            "despesaCaixa": {"apurado": self._decimal_str(despesa_total), "turnos": len(apresentado_rows)},
            "valeFuncionario": {"apurado": self._decimal_str(vale_total), "turnos": len(apresentado_rows)},
            "emprestimos": {"apurado": self._decimal_str(emprestimo_total), "turnos": len(apresentado_rows)},
            "fundoCaixa": {"disponivel": False, "apurado": None},
        }

    def _aggregate_expenses_summary(self, expenses: list[dict[str, Any]]) -> dict[str, Any]:
        total = Decimal("0")
        by_category: dict[str, Decimal] = {}
        by_empresa: dict[int, Decimal] = {}
        for row in expenses:
            val = self._to_decimal(row.get("valor"))
            total += val
            cat = row.get("categoriaLogos", "OUTROS")
            by_category[cat] = by_category.get(cat, Decimal("0")) + val
            try:
                emp = int(row.get("empresaCodigo"))
                by_empresa[emp] = by_empresa.get(emp, Decimal("0")) + val
            except (TypeError, ValueError):
                pass
        return {
            "totalRegistros": len(expenses),
            "totalValor": self._decimal_str(total),
            "porCategoriaLogos": {k: self._decimal_str(v) for k, v in sorted(by_category.items())},
            "porEmpresa": {str(k): self._decimal_str(v) for k, v in sorted(by_empresa.items())},
        }

    async def get_expenses(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo_raw: str | int | None,
        page: int = 1,
        limit: int = 50,
    ) -> WebPostoResponse:
        import time

        t0 = time.perf_counter()
        raw, err = await self._overview._load_filtered_expenses(filters)
        if err is not None:
            return err
        expenses = self._filter_expenses(raw, filters)
        page_data, total = self._paginate(expenses, page, limit)
        employee_index: dict[int, dict[str, Any]] = {}
        if any(r.get("funcionarioCodigo") not in (None, "", 0) for r in page_data):
            from src.services.employee_dimension_service import EmployeeDimensionService

            try:
                employee_ctx = await EmployeeDimensionService(self._client).build(
                    filters.data_inicial, filters.data_final
                )
                employee_index = employee_ctx.get("index") or {}
            except Exception:
                LOGGER.warning("Dimensão nominal indisponível no centro financeiro", exc_info=True)

        def employee_name(code: Any) -> str | None:
            if code in (None, "", 0):
                return None
            try:
                name = (employee_index.get(int(code)) or {}).get("employeeName")
            except (TypeError, ValueError):
                return None
            return str(name).strip() if name else None

        ms = round((time.perf_counter() - t0) * 1000, 1)
        meta = FinanceCenterMeta(filters.data_inicial, filters.data_final, empresa_codigo_raw, {"despesas": ms})
        public = [
            {
                "empresaCodigo": r.get("empresaCodigo"),
                "data": r.get("data"),
                "valor": r.get("valor"),
                "planoConta": r.get("planoConta"),
                "planoContaCodigo": r.get("planoContaCodigo"),
                "centroCusto": r.get("centroCusto"),
                "funcionarioCodigo": r.get("funcionarioCodigo"),
                "employeeName": employee_name(r.get("funcionarioCodigo")),
                "categoriaLogos": r.get("categoriaLogos"),
                "categoriaLogosV2": r.get("categoriaLogosV2"),
                "categoriaLogosV3": r.get("categoriaLogosV3"),
                "confidenceScore": r.get("confidenceScore"),
                "confidenceScoreV3": r.get("confidenceScoreV3"),
                "confidenceBand": r.get("confidenceBand"),
                "classificationSource": r.get("classificationSource"),
            }
            for r in page_data
        ]
        return WebPostoResponse.ok(
            {
                "page": max(page, 1),
                "limit": min(max(limit, 1), 500),
                "total": total,
                "resumo": self._aggregate_expenses_summary(expenses),
                "data": public,
                "snapshotKey": meta.snapshot_key("expenses"),
                "performanceMs": meta.fetch_ms,
            }
        )

    async def get_payables(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo_raw: str | int | None,
        page: int = 1,
        limit: int = 50,
    ) -> WebPostoResponse:
        rows, ms = await self._fetch_titulo_pagar_all(filters)
        ref = filters.data_final or date.today().isoformat()
        buckets = self._classify_payables(rows, ref)
        summary = self._bucket_summary(buckets)
        flat = buckets["pago"] + buckets["emAberto"]
        page_data, total = self._paginate(flat, page, limit)
        meta = FinanceCenterMeta(filters.data_inicial, filters.data_final, empresa_codigo_raw, {"payables": ms})
        return WebPostoResponse.ok(
            {
                "page": max(page, 1),
                "limit": min(max(limit, 1), 500),
                "total": total,
                "resumo": summary,
                "buckets": {k: self._bucket_summary({k: v})[k] for k, v in buckets.items()},
                "data": page_data,
                "snapshotKey": meta.snapshot_key("payables"),
                "performanceMs": meta.fetch_ms,
            }
        )

    async def get_receivables(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo_raw: str | int | None,
        page: int = 1,
        limit: int = 50,
    ) -> WebPostoResponse:
        rows, ms = await self._fetch_titulo_receber_all(filters)
        ref = filters.data_final or date.today().isoformat()
        buckets = self._classify_receivables(rows, ref)
        summary = self._bucket_summary(buckets)
        flat = buckets["recebido"] + buckets["pendente"]
        page_data, total = self._paginate(flat, page, limit)
        meta = FinanceCenterMeta(filters.data_inicial, filters.data_final, empresa_codigo_raw, {"receivables": ms})
        return WebPostoResponse.ok(
            {
                "page": max(page, 1),
                "limit": min(max(limit, 1), 500),
                "total": total,
                "resumo": summary,
                "buckets": {k: self._bucket_summary({k: v})[k] for k, v in buckets.items()},
                "data": page_data,
                "snapshotKey": meta.snapshot_key("receivables"),
                "performanceMs": meta.fetch_ms,
            }
        )

    async def get_bank_movements(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo_raw: str | int | None,
        page: int = 1,
        limit: int = 50,
    ) -> WebPostoResponse:
        rows, ms = await self._fetch_movimento_conta_all(filters)
        classified = self._classify_bank_movements(rows)
        all_items = (
            classified["creditos"]["items"]
            + classified["debitos"]["items"]
            + classified["tarifas"]["items"]
        )
        page_data, total = self._paginate(all_items, page, limit)
        meta = FinanceCenterMeta(filters.data_inicial, filters.data_final, empresa_codigo_raw, {"bank": ms})
        public = dict(classified)
        for key in ("creditos", "debitos", "tarifas", "transferencias"):
            public[key] = {k: v for k, v in public[key].items() if k != "items"}
        return WebPostoResponse.ok(
            {
                "page": max(page, 1),
                "limit": min(max(limit, 1), 500),
                "total": total,
                "resumo": public,
                "data": page_data,
                "paginacaoCompleta": len(rows),
                "snapshotKey": meta.snapshot_key("bank"),
                "performanceMs": meta.fetch_ms,
            }
        )

    async def get_cash(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo_raw: str | int | None,
    ) -> WebPostoResponse:
        caixa, apresentado, ms = await self._fetch_caixa_all(filters)
        data = self._aggregate_cash(caixa, apresentado)
        meta = FinanceCenterMeta(filters.data_inicial, filters.data_final, empresa_codigo_raw, {"cash": ms})
        warnings: list[str] = []
        if not data["fundoCaixa"]["disponivel"]:
            warnings.append("fundoCaixa: campo não disponível na API WebPosto")
        return WebPostoResponse.ok(
            {
                **data,
                "snapshotKey": meta.snapshot_key("cash"),
                "performanceMs": meta.fetch_ms,
                "warnings": warnings,
            }
        )

    async def get_summary(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo_raw: str | int | None,
    ) -> WebPostoResponse:
        import time

        t0 = time.perf_counter()
        ref = filters.data_final or date.today().isoformat()
        warnings: list[str] = []

        despesas_task = self._overview._load_filtered_expenses(filters)
        payables_task = self._fetch_titulo_pagar_all(filters)
        receivables_task = self._fetch_titulo_receber_all(filters)
        bank_task = self._fetch_movimento_conta_all(filters)
        cash_task = self._fetch_caixa_all(filters)

        (despesas_raw, despesas_err), (pay_rows, pay_ms), (rec_rows, rec_ms), (bank_rows, bank_ms), cash_result = await asyncio.gather(
            despesas_task,
            payables_task,
            receivables_task,
            bank_task,
            cash_task,
        )

        if despesas_err is not None:
            return despesas_err

        caixa_rows, apresentado_rows, cash_ms = cash_result
        expenses = self._filter_expenses(despesas_raw, filters)
        pay_buckets = self._classify_payables(pay_rows, ref)
        rec_buckets = self._classify_receivables(rec_rows, ref)
        bank = self._classify_bank_movements(bank_rows)
        cash = self._aggregate_cash(caixa_rows, apresentado_rows)

        if bank["totalRegistros"] >= 2000:
            warnings.append("movimentoBancario: limite de 10 páginas atingido — revisar paginação")
        if not cash["fundoCaixa"]["disponivel"]:
            warnings.append("caixa.fundoCaixa: indisponível na API")

        coverage = {
            "despesasGerenciais": {"status": "ok", "registros": len(expenses)},
            "contasPagar": {"status": "ok" if pay_rows else "empty", "registros": len(pay_rows)},
            "contasReceber": {"status": "ok" if rec_rows else "empty", "registros": len(rec_rows)},
            "movimentoBancario": {"status": "ok", "registros": bank["totalRegistros"]},
            "caixa": {"status": "ok", "turnos": cash["turnos"]["count"]},
        }

        total_ms = round((time.perf_counter() - t0) * 1000, 1)
        meta = FinanceCenterMeta(
            filters.data_inicial,
            filters.data_final,
            empresa_codigo_raw,
            {
                "despesas": 0,
                "payables": pay_ms,
                "receivables": rec_ms,
                "bank": bank_ms,
                "cash": cash_ms,
                "total": total_ms,
            },
        )

        bank_public = {k: v for k, v in bank.items() if k != "totalRegistros"}
        for key in ("creditos", "debitos", "tarifas", "transferencias"):
            if key in bank_public and isinstance(bank_public[key], dict):
                bank_public[key] = {k: v for k, v in bank_public[key].items() if k != "items"}

        return WebPostoResponse.ok(
            {
                "periodo": {"dataInicial": filters.data_inicial, "dataFinal": filters.data_final},
                "despesasGerenciais": self._aggregate_expenses_summary(expenses),
                "contasPagar": self._bucket_summary(pay_buckets),
                "contasReceber": self._bucket_summary(rec_buckets),
                "movimentoBancario": {
                    "totalRegistros": bank["totalRegistros"],
                    **{k: bank_public[k] for k in ("creditos", "debitos", "tarifas", "transferencias", "saldoMovimentado")},
                },
                "caixa": {
                    "turnos": cash["turnos"]["count"],
                    "despesaCaixa": cash["despesaCaixa"],
                    "valeFuncionario": cash["valeFuncionario"],
                    "emprestimos": cash["emprestimos"],
                    "diferencas": cash["diferencas"]["count"],
                },
                "coverage": coverage,
                "warnings": warnings,
                "snapshotKey": meta.snapshot_key("summary"),
                "performanceMs": meta.fetch_ms,
            }
        )
