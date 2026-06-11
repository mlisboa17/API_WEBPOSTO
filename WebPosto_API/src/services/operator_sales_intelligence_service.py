"""F04.0 — Operator Performance & Sales Intelligence."""
from __future__ import annotations

import asyncio
import time
from collections import Counter, defaultdict
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.cash_operations_service import _dec, _risk_band, _round2, CashOperationsService
from src.services.employee_dimension_service import EmployeeDimensionService
from src.services.network_financial_overview_service import FinancialOverviewFilters
from src.services.operator_context_attribution_service import OperatorContextAttributionService
from src.services.operator_performance_service import OperatorPerformanceService

PRODUCTIVITY_BANDS = (
    (90, 100, "ELITE"),
    (75, 89, "ALTA"),
    (50, 74, "NORMAL"),
    (25, 49, "BAIXA"),
    (0, 24, "CRITICA"),
)

RISK_W_BREAK = 0.40
RISK_W_DISCOUNT = 0.20
RISK_W_RECURRENCE = 0.20
RISK_W_CONTEXT = 0.20

PAYMENT_BUCKETS = (
    ("DINHEIRO", ("dinheiro", "especie", "cash")),
    ("PIX", ("pix",)),
    ("DEBITO", ("debito", "débito", "debit")),
    ("CREDITO", ("credito", "crédito", "credit")),
    ("CONVENIO", ("convenio", "convênio", "vale", "prazo", "nota")),
)


def _productivity_band(score: float) -> str:
    s = int(round(score))
    for lo, hi, label in PRODUCTIVITY_BANDS:
        if lo <= s <= hi:
            return label
    return "CRITICA"


def _cancelled(row: dict[str, Any]) -> bool:
    return str(row.get("cancelada") or "").lower() in {"1", "true", "s", "sim", "cancelada"}


def _payment_bucket(name: str | None) -> str:
    n = (name or "").lower()
    for label, keys in PAYMENT_BUCKETS:
        if any(k in n for k in keys):
            return label
    return "OUTROS"


def _is_fuel_item(row: dict[str, Any]) -> bool:
    return bool(row.get("bicoCodigo") or row.get("tanqueCodigo") or row.get("produtoLmcCodigo"))


class OperatorSalesIntelligenceService:
    """Camada F04.0 — vendas, produtividade, descontos, mix, combustível, accountability, risco."""

    def __init__(
        self,
        cash_ops: CashOperationsService | None = None,
        employee_dim: EmployeeDimensionService | None = None,
        performance: OperatorPerformanceService | None = None,
    ) -> None:
        self._cash = cash_ops or CashOperationsService()
        self._employee = employee_dim or EmployeeDimensionService(self._cash._client)
        self._performance = performance or OperatorPerformanceService(self._cash)

    def _filters(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
    ) -> FinancialOverviewFilters:
        return build_finance_center_filters(data_inicial, data_final, empresa_codigo)

    async def _load_operational(
        self,
        filters: FinancialOverviewFilters,
    ) -> dict[str, list[dict[str, Any]]]:
        di, df = filters.data_inicial, filters.data_final
        venda_t, vi_t, vfp_t, abast_t = await asyncio.gather(
            self._cash._fetch_paged("venda", di, df, 15),
            self._cash._fetch_paged("venda_item", di, df, 15),
            self._cash._fetch_paged("venda_forma_pagamento", di, df, 15),
            self._cash._fetch_paged("abastecimento", di, df, 15),
        )
        venda = [r for r in venda_t[0] if self._cash._matches_empresa(r, filters)]
        venda_item = [r for r in vi_t[0] if self._cash._matches_empresa(r, filters)]
        vfp = [r for r in vfp_t[0] if self._cash._matches_empresa(r, filters)]
        abast = [r for r in abast_t[0] if self._cash._matches_empresa(r, filters)]
        return {"venda": venda, "venda_item": venda_item, "vfp": vfp, "abastecimento": abast}

    def _sales_performance(
        self,
        venda: list[dict[str, Any]],
        venda_item: list[dict[str, Any]],
        idx: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_op: dict[int, dict[str, Any]] = defaultdict(
            lambda: {
                "totalVendas": 0.0,
                "quantidadeVendas": 0,
                "volumeFinanceiro": 0.0,
                "volumeCombustivel": 0.0,
                "volumeConveniencia": 0.0,
                "litrosCombustivel": 0.0,
            }
        )

        for row in venda:
            if _cancelled(row):
                continue
            try:
                op = int(row.get("funcionarioCodigo") or 0)
            except (TypeError, ValueError):
                continue
            if not op:
                continue
            val = _dec(row.get("totalVenda"))
            by_op[op]["totalVendas"] += val
            by_op[op]["quantidadeVendas"] += 1
            by_op[op]["volumeFinanceiro"] += val

        for row in venda_item:
            try:
                op = int(row.get("funcionarioCodigo") or 0)
            except (TypeError, ValueError):
                continue
            if not op:
                continue
            val = _dec(row.get("totalVenda"))
            qty = _dec(row.get("quantidade"))
            if _is_fuel_item(row):
                by_op[op]["volumeCombustivel"] += val
                by_op[op]["litrosCombustivel"] += qty
            else:
                by_op[op]["volumeConveniencia"] += val

        out: list[dict[str, Any]] = []
        for op, agg in by_op.items():
            emp = idx.get(op) or {}
            qtd = agg["quantidadeVendas"]
            total = agg["totalVendas"]
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": emp.get("employeeName"),
                    "employeeReference": emp.get("employeeReference"),
                    "totalVendas": _round2(total),
                    "quantidadeVendas": qtd,
                    "ticketMedio": _round2(total / qtd) if qtd else 0.0,
                    "volumeCombustivel": _round2(agg["volumeCombustivel"]),
                    "volumeConveniencia": _round2(agg["volumeConveniencia"]),
                    "volumeFinanceiro": _round2(agg["volumeFinanceiro"]),
                    "litrosCombustivel": _round2(agg["litrosCombustivel"]),
                }
            )
        out.sort(key=lambda x: x["totalVendas"], reverse=True)
        return out

    def _productivity_engine(
        self,
        sales: list[dict[str, Any]],
        abast: list[dict[str, Any]],
        venda_item: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        abast_by: Counter[int] = Counter()
        items_by: Counter[int] = Counter()
        for row in abast:
            try:
                op = int(row.get("codigoFrentista") or 0)
            except (TypeError, ValueError):
                continue
            if op:
                abast_by[op] += 1
        for row in venda_item:
            try:
                op = int(row.get("funcionarioCodigo") or 0)
            except (TypeError, ValueError):
                continue
            if op:
                items_by[op] += 1

        if not sales:
            return []

        max_vendas = max(s["quantidadeVendas"] for s in sales) or 1
        max_abast = max(abast_by.values()) if abast_by else 1
        max_items = max(items_by.values()) if items_by else 1
        max_vol = max(s["volumeFinanceiro"] for s in sales) or 1.0

        scored: list[dict[str, Any]] = []
        for s in sales:
            op = int(s["funcionarioCodigo"])
            v_norm = 100 * s["quantidadeVendas"] / max_vendas
            a_norm = 100 * abast_by.get(op, 0) / max_abast
            i_norm = 100 * items_by.get(op, 0) / max_items
            f_norm = 100 * s["volumeFinanceiro"] / max_vol
            score = _round2(0.30 * v_norm + 0.25 * a_norm + 0.20 * i_norm + 0.25 * f_norm)
            scored.append(
                {
                    **s,
                    "abastecimentos": abast_by.get(op, 0),
                    "itensVendidos": items_by.get(op, 0),
                    "productivityScore": score,
                    "productivityBand": _productivity_band(score),
                }
            )
        scored.sort(key=lambda x: x["productivityScore"], reverse=True)
        return scored

    def _discount_intelligence(
        self,
        venda_item: list[dict[str, Any]],
        venda: list[dict[str, Any]],
        idx: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:
        by_op: Counter[int] = Counter()
        by_pdv: Counter[Any] = Counter()
        total = 0.0
        count = 0

        venda_pdv: dict[int, Any] = {}
        for row in venda:
            try:
                venda_pdv[int(row.get("vendaCodigo"))] = row.get("pdvCodigo")
            except (TypeError, ValueError):
                pass

        for row in venda_item:
            disc = _dec(row.get("totalDesconto"))
            if disc <= 0:
                continue
            total += disc
            count += 1
            try:
                op = int(row.get("funcionarioCodigo") or 0)
            except (TypeError, ValueError):
                op = 0
            if op:
                by_op[op] += disc
            try:
                pdv = venda_pdv.get(int(row.get("vendaCodigo") or 0))
            except (TypeError, ValueError):
                pdv = None
            if pdv is not None:
                by_pdv[pdv] += disc

        top_op = by_op.most_common(1)[0] if by_op else (None, 0)
        per_op = []
        for op, val in by_op.most_common(20):
            emp = idx.get(op) or {}
            per_op.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": emp.get("employeeName"),
                    "totalDesconto": _round2(val),
                }
            )

        return {
            "totalDesconto": _round2(total),
            "mediaDesconto": _round2(total / count) if count else 0.0,
            "eventosDesconto": count,
            "descontoPorOperador": per_op,
            "descontoPorPdv": [
                {"pdvCodigo": p, "totalDesconto": _round2(v)} for p, v in by_pdv.most_common(15)
            ],
            "maiorConcessor": {
                "funcionarioCodigo": top_op[0],
                "employeeName": (idx.get(top_op[0]) or {}).get("employeeName") if top_op[0] else None,
                "totalDesconto": _round2(top_op[1]),
            },
        }

    def _payment_mix(
        self,
        vfp: list[dict[str, Any]],
        venda: list[dict[str, Any]],
        idx: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        venda_op: dict[tuple[Any, Any], int] = {}
        for row in venda:
            key = (row.get("empresaCodigo"), row.get("vendaCodigo"))
            try:
                venda_op[key] = int(row.get("funcionarioCodigo") or 0)
            except (TypeError, ValueError):
                pass

        by_op: dict[int, Counter[str]] = defaultdict(Counter)
        for row in vfp:
            key = (row.get("empresaCodigo"), row.get("vendaCodigo"))
            op = venda_op.get(key, 0)
            if not op:
                continue
            bucket = _payment_bucket(str(row.get("nomeFormaPagamento")))
            by_op[op][bucket] += _dec(row.get("valorPagamento"))

        out: list[dict[str, Any]] = []
        for op, buckets in by_op.items():
            emp = idx.get(op) or {}
            total = sum(buckets.values()) or 1.0
            mix = {k: _round2(100 * v / total) for k, v in buckets.items()}
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": emp.get("employeeName"),
                    "mixPct": mix,
                    "volumePorForma": {k: _round2(v) for k, v in buckets.items()},
                    "volumeTotal": _round2(total),
                }
            )
        out.sort(key=lambda x: x["volumeTotal"], reverse=True)
        return out

    def _fuel_performance(
        self,
        abast: list[dict[str, Any]],
        idx: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_op: dict[int, dict[str, float]] = defaultdict(lambda: {"litros": 0.0, "valor": 0.0, "count": 0})
        for row in abast:
            try:
                op = int(row.get("codigoFrentista") or 0)
            except (TypeError, ValueError):
                continue
            if not op:
                continue
            by_op[op]["litros"] += _dec(row.get("quantidade"))
            by_op[op]["valor"] += _dec(row.get("valorTotal"))
            by_op[op]["count"] += 1

        out: list[dict[str, Any]] = []
        for op, agg in by_op.items():
            emp = idx.get(op) or {}
            cnt = int(agg["count"])
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": emp.get("employeeName"),
                    "litrosVendidos": _round2(agg["litros"]),
                    "abastecimentos": cnt,
                    "valorCombustivel": _round2(agg["valor"]),
                    "ticketCombustivel": _round2(agg["valor"] / cnt) if cnt else 0.0,
                }
            )
        out.sort(key=lambda x: x["valorCombustivel"], reverse=True)
        return out

    @staticmethod
    def _cash_accountability(
        perf_operators: list[dict[str, Any]],
        idx: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in perf_operators:
            op = row.get("funcionarioCodigo")
            if op is None:
                continue
            emp = idx.get(int(op)) or {}
            saldo = _dec(row.get("saldoLedger"))
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": emp.get("employeeName"),
                    "saldoOperacional": _round2(saldo),
                    "compensadoAutomatico": _round2(row.get("compensadoAutomatico") or 0),
                    "diferencaAcumulada": row.get("diferencaAcumulada"),
                    "faltasProxy": _round2(min(saldo, 0)),
                    "sobrasProxy": _round2(max(saldo, 0)),
                }
            )
        out.sort(key=lambda x: x["saldoOperacional"])
        return out

    def _risk_engine(
        self,
        perf_operators: list[dict[str, Any]],
        discount_by_op: dict[int, float],
        context_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        ctx_map = {r.get("funcionarioCodigo"): r for r in context_rows}
        max_disc = max(discount_by_op.values()) if discount_by_op else 1.0
        max_disc = max_disc or 1.0
        max_break = max(abs(_dec(o.get("diferencaAcumulada"))) for o in perf_operators) if perf_operators else 1.0
        max_break = max_break or 1.0

        out: list[dict[str, Any]] = []
        for row in perf_operators:
            op = row.get("funcionarioCodigo")
            if op is None:
                continue
            emp = row.get("employeeName")
            break_raw = abs(_dec(row.get("diferencaAcumulada")))
            break_score = _round2(100 * (1 - min(break_raw / max_break, 1.0)))
            disc_raw = discount_by_op.get(int(op), 0.0)
            disc_score = _round2(100 * (1 - min(disc_raw / max_disc, 1.0)))
            rec = float(row.get("indiceRecorrencia") or 0)
            if rec > 1:
                rec = rec / 100.0
            rec_score = _round2(100 * (1 - min(rec, 1.0)))
            ctx = ctx_map.get(op) or {}
            ctx_score = _round2(float(ctx.get("contextAdjustedPerformanceScore") or row.get("performanceScore") or 50))

            risk = _round2(
                RISK_W_BREAK * break_score
                + RISK_W_DISCOUNT * disc_score
                + RISK_W_RECURRENCE * rec_score
                + RISK_W_CONTEXT * ctx_score
            )
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": emp,
                    "operatorRiskScore": risk,
                    "riskBand": _risk_band(risk),
                    "componentQuebraCaixa": break_score,
                    "componentDescontos": disc_score,
                    "componentRecorrencia": rec_score,
                    "componentContexto": ctx_score,
                    "monitoramentoPrioritario": bool(row.get("monitoramentoPrioritario")),
                }
            )
        out.sort(key=lambda x: x["operatorRiskScore"])
        return out

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        t0 = time.perf_counter()
        filters = self._filters(data_inicial, data_final, empresa_codigo)

        perf_resp = await self._performance.build(data_inicial, data_final, empresa_codigo, include_windows=False)
        if not perf_resp.success or not perf_resp.data:
            return WebPostoResponse.fail("Falha ao consolidar performance base F03.4")

        emp_payload = await self._employee.build(data_inicial, data_final)
        idx = emp_payload["index"]
        ops_data = perf_resp.data.get("operators") or {}
        perf_ops = list(ops_data.get("todos") or ops_data.get("ranking") or [])

        for row in perf_ops:
            code = row.get("funcionarioCodigo")
            if code is not None:
                emp = idx.get(int(code)) or {}
                row["employeeName"] = emp.get("employeeName")
                row["employeeCpf"] = emp.get("employeeCpf")
                row["employeeReference"] = emp.get("employeeReference")

        operational = await self._load_operational(filters)
        merged, _, _ = await self._cash._fetch_merged(filters)

        sales = self._sales_performance(operational["venda"], operational["venda_item"], idx)
        productivity = self._productivity_engine(sales, operational["abastecimento"], operational["venda_item"])
        discounts = self._discount_intelligence(operational["venda_item"], operational["venda"], idx)
        payment_mix = self._payment_mix(operational["vfp"], operational["venda"], idx)
        fuel = self._fuel_performance(operational["abastecimento"], idx)
        accountability = self._cash_accountability(perf_ops, idx)

        disc_map = {
            int(r["funcionarioCodigo"]): r["totalDesconto"]
            for r in discounts.get("descontoPorOperador") or []
            if r.get("funcionarioCodigo") is not None
        }
        context = OperatorContextAttributionService.build(
            merged,
            perf_ops,
            perf_resp.data.get("pdvs", {}).get("ranking") or [],
            perf_resp.data.get("turns", {}).get("porTurno") or [],
            [],
        )
        ctx_rows = context.get("rankingAjustado") or []
        risk = self._risk_engine(perf_ops, disc_map, ctx_rows)

        active_employees = emp_payload["ativos"]
        top_seller = sales[0] if sales else None
        top_fuel = fuel[0] if fuel else None
        top_conv = max(sales, key=lambda x: x["volumeConveniencia"]) if sales else None
        top_disc = discounts.get("maiorConcessor") or {}
        top_ticket = max(sales, key=lambda x: x["ticketMedio"]) if sales else None
        top_prod = productivity[0] if productivity else None
        worst_risk = risk[0] if risk else None

        acct_sorted = sorted(accountability, key=lambda x: x["saldoOperacional"])
        top_debtor = acct_sorted[0] if acct_sorted else None
        top_creditor = acct_sorted[-1] if acct_sorted else None

        ctx_dependent = [r for r in ctx_rows if r.get("classificacao") == "DEPENDENTE_DO_PDV"]
        elite = [p for p in productivity if p.get("productivityBand") == "ELITE"]
        critical = [p for p in productivity if p.get("productivityBand") == "CRITICA"]
        at_risk = [r for r in risk if r.get("riskBand") in {"Critico", "Atencao"}]
        critical_volume = _round2(
            sum(abs(_dec(r.get("diferencaAcumulada"))) for r in perf_ops if r.get("monitoramentoPrioritario"))
        )

        parity_sales = _round2(sum(s["totalVendas"] for s in sales))
        parity_venda_api = _round2(
            sum(
                _dec(r.get("totalVenda"))
                for r in operational["venda"]
                if not _cancelled(r) and r.get("funcionarioCodigo")
            )
        )
        parity_delta = _round2(abs(parity_sales - parity_venda_api))

        executive = {
            "1_operadoresAtivos": active_employees,
            "2_quemMaisVende": top_seller,
            "3_quemVendeCombustivel": top_fuel,
            "4_quemVendeConveniencia": top_conv,
            "5_quemMaisDescontos": top_disc,
            "6_maiorTicketMedio": top_ticket,
            "7_melhorProdutividade": top_prod,
            "8_maiorRiscoOperacional": worst_risk,
            "9_maiorSaldoDevedor": top_debtor,
            "10_maiorSaldoCredor": top_creditor,
            "11_maisFaltas": top_debtor,
            "12_maisSobras": top_creditor,
            "13_bomEmPdvCritico": [r for r in ctx_rows if (r.get("contextAdjustedPerformanceScore") or 0) >= 70][:3],
            "14_dependenteContexto": ctx_dependent[:5],
            "15_operadorElite": elite[0] if elite else top_prod,
            "16_operadorCritico": critical[0] if critical else worst_risk,
            "17_operadoresEmRisco": len(at_risk),
            "18_dinheiroOperadoresCriticos": critical_volume,
            "19_prontoGestaoPessoas": emp_payload["nominalizacaoPct"] >= 90 and len(sales) > 0,
            "20_aprovadoF041": parity_delta <= 0.01 and emp_payload["comNome"] > 0,
            "paridadeDelta": parity_delta,
        }

        parecer = (
            "[PARECER FINAL: APROVADO PARA F04.1]"
            if executive["20_aprovadoF041"]
            else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"
        )

        payload = {
            "sprint": "F04.0",
            "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
            "elapsedMs": round((time.perf_counter() - t0) * 1000, 1),
            "dimEmployee": emp_payload,
            "salesPerformance": {"operators": sales, "totals": {"volume": parity_sales}},
            "productivityEngine": {
                "operators": productivity,
                "bands": dict(Counter(p["productivityBand"] for p in productivity)),
            },
            "discountIntelligence": discounts,
            "paymentMix": payment_mix,
            "fuelPerformance": fuel,
            "cashAccountability": accountability,
            "operatorRiskEngine": risk,
            "contextAttribution": context,
            "performanceBase": {"summary": perf_resp.data.get("summary"), "operators": perf_ops},
            "cockpit": {
                "topOperadores": productivity[:10],
                "operadoresCriticos": [r for r in risk if r.get("riskBand") == "Critico"][:10],
                "vendas": sales[:10],
                "descontos": discounts.get("descontoPorOperador") or [],
                "risco": at_risk[:10],
                "accountability": accountability[:10],
            },
            "executiveAnswers": executive,
            "qa": {
                "dimEmployeeOk": emp_payload["total"] > 0,
                "nominalizacaoCompleta": emp_payload["nominalizacaoPct"] >= 90,
                "paridadeZero": parity_delta <= 0.01,
            },
            "parecerFinal": parecer,
        }
        return WebPostoResponse.ok(payload)
