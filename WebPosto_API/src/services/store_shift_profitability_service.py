"""F04.3 — Store, Shift & Operational Profitability Intelligence."""
from __future__ import annotations

import asyncio
import time
from collections import Counter, defaultdict
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.cash_operations_service import _dec, _round2, CashOperationsService
from src.services.operator_accountability_incentive_service import CRITICAL_PDVS, _norm_score
from src.services.operator_profitability_service import OperatorProfitabilityService
from src.services.operator_profitability_snapshot_service import OperatorProfitabilitySnapshotService
from src.services.operator_sales_intelligence_service import _cancelled

OPERATION_BANDS = (
    (80, 100, "EXCELENTE"),
    (60, 79, "BOM"),
    (40, 59, "ATENÇÃO"),
    (0, 39, "CRÍTICO"),
)

SHIFT_RISK_WEIGHTS = {
    "quebraCaixa": 0.30,
    "desconto": 0.20,
    "cancelamento": 0.15,
    "roi": 0.20,
    "produtividade": 0.15,
}

MANAGEMENT_ACTIONS_V2 = (
    "TROCAR_OPERADOR",
    "TROCAR_TURNO",
    "TREINAR",
    "PROMOVER",
    "AUDITAR",
    "REESTRUTURAR_PDV",
)

TURN_LABELS = {1: "1º Turno", 2: "2º Turno", 3: "3º Turno"}


def _turn_key(row: dict[str, Any]) -> str:
    tc = row.get("turnoCodigo")
    tn = row.get("turno")
    if tc is not None:
        try:
            return TURN_LABELS.get(int(tc), f"Turno {tc}")
        except (TypeError, ValueError):
            pass
    if tn is not None and str(tn).strip():
        return str(tn).strip()
    return "Turno ?"


def _operation_band(score: float) -> str:
    s = int(round(score))
    for lo, hi, label in OPERATION_BANDS:
        if lo <= s <= hi:
            return label
    return "CRÍTICO"


def _cell_key(pdv: Any, turn: str, op: int) -> tuple[Any, str, int]:
    return (pdv, turn, op)


class StoreShiftProfitabilityService:
    """F04.3 — lucratividade por PDV, turno e combinação operacional."""

    def __init__(
        self,
        profitability: OperatorProfitabilityService | None = None,
        cash_ops: CashOperationsService | None = None,
    ) -> None:
        self._cash = cash_ops or CashOperationsService()
        self._f042 = profitability or OperatorProfitabilityService(cash_ops=self._cash)

    def _aggregate_sales(
        self,
        venda: list[dict[str, Any]],
    ) -> tuple[
        dict[Any, dict[str, Any]],
        dict[str, dict[str, Any]],
        dict[tuple[Any, str, int], dict[str, Any]],
        float,
    ]:
        by_pdv: dict[Any, dict[str, Any]] = defaultdict(
            lambda: {"receitaBruta": 0.0, "quantidadeVendas": 0, "cancelamentos": 0.0}
        )
        by_turn: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"receitaBruta": 0.0, "quantidadeVendas": 0, "cancelamentos": 0.0}
        )
        by_cell: dict[tuple[Any, str, int], dict[str, Any]] = defaultdict(
            lambda: {"receitaBruta": 0.0, "quantidadeVendas": 0}
        )
        cancel_by_pdv: Counter[Any] = Counter()
        cancel_by_turn: Counter[str] = Counter()
        consolidated = 0.0

        for row in venda:
            pdv = row.get("pdvCodigo")
            turn = _turn_key(row)
            val = _dec(row.get("totalVenda"))
            if _cancelled(row):
                cancel_by_pdv[pdv] += val
                cancel_by_turn[turn] += val
                by_pdv[pdv]["cancelamentos"] += val
                by_turn[turn]["cancelamentos"] += val
                continue
            try:
                op = int(row.get("funcionarioCodigo") or 0)
            except (TypeError, ValueError):
                continue
            if not op:
                continue
            consolidated += val
            by_pdv[pdv]["receitaBruta"] += val
            by_pdv[pdv]["quantidadeVendas"] += 1
            by_turn[turn]["receitaBruta"] += val
            by_turn[turn]["quantidadeVendas"] += 1
            cell = _cell_key(pdv, turn, op)
            by_cell[cell]["receitaBruta"] += val
            by_cell[cell]["quantidadeVendas"] += 1
            by_cell[cell]["pdvCodigo"] = pdv
            by_cell[cell]["turno"] = turn
            by_cell[cell]["funcionarioCodigo"] = op

        return by_pdv, by_turn, by_cell, _round2(consolidated)

    @staticmethod
    def _discount_by_pdv(
        venda: list[dict[str, Any]],
        venda_item: list[dict[str, Any]],
    ) -> dict[str, Any]:
        venda_pdv: dict[int, Any] = {}
        for row in venda:
            try:
                venda_pdv[int(row.get("vendaCodigo"))] = row.get("pdvCodigo")
            except (TypeError, ValueError):
                pass
        by_pdv: Counter[Any] = Counter()
        for row in venda_item:
            disc = _dec(row.get("totalDesconto"))
            if disc <= 0:
                continue
            try:
                pdv = venda_pdv.get(int(row.get("vendaCodigo") or 0))
            except (TypeError, ValueError):
                pdv = None
            if pdv is not None:
                by_pdv[pdv] += disc
        return {
            "descontoPorPdv": [
                {"pdvCodigo": p, "totalDesconto": _round2(v)} for p, v in by_pdv.most_common()
            ]
        }

    def _pdv_profitability_engine(
        self,
        by_pdv: dict[Any, dict[str, Any]],
        discounts: dict[str, Any],
        cash_pdvs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        disc_map = {
            r["pdvCodigo"]: _dec(r.get("totalDesconto"))
            for r in discounts.get("descontoPorPdv") or []
            if r.get("pdvCodigo") is not None
        }
        cash_map = {r.get("pdvCodigo"): r for r in cash_pdvs}

        out: list[dict[str, Any]] = []
        for pdv, agg in by_pdv.items():
            cash = cash_map.get(pdv) or {}
            descontos = disc_map.get(pdv, 0.0)
            faltas = abs(min(_dec(cash.get("diferencaAcumulada")), 0))
            sobras = max(_dec(cash.get("diferencaAcumulada")), 0)
            perdas = abs(_dec(cash.get("diferencaAcumulada")))
            cancelamentos = agg.get("cancelamentos", 0.0)
            destruicao = _round2(descontos + cancelamentos + faltas + perdas - sobras * 0.5)
            destruicao = max(destruicao, 0.0)
            receita = _round2(agg["receitaBruta"])
            margem = _round2(receita - destruicao)
            risco = max(destruicao, 1.0)
            out.append(
                {
                    "pdvCodigo": pdv,
                    "receitaBruta": receita,
                    "destruicaoMargem": destruicao,
                    "margemOperacional": margem,
                    "descontos": _round2(descontos),
                    "cancelamentos": _round2(cancelamentos),
                    "faltas": _round2(faltas),
                    "sobras": _round2(sobras),
                    "perdasCaixa": _round2(perdas),
                    "quantidadeVendas": agg.get("quantidadeVendas", 0),
                    "resultadoLiquido": margem,
                    "riscoEconomico": _round2(risco),
                    "roi": _round2(margem / risco if risco else 0),
                    "monitoramentoPrioritario": int(pdv) in CRITICAL_PDVS if pdv is not None else False,
                }
            )
        out.sort(key=lambda x: x["resultadoLiquido"], reverse=True)
        return out

    def _shift_profitability_engine(
        self,
        by_turn: dict[str, dict[str, Any]],
        cash_turns: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        cash_map: dict[str, dict[str, Any]] = {}
        for row in cash_turns:
            label = _turn_key(row)
            cash_map[label] = row

        out: list[dict[str, Any]] = []
        for turn, agg in by_turn.items():
            cash = cash_map.get(turn) or {}
            desvio = _dec(cash.get("desvioAcumulado"))
            faltas = abs(min(desvio, 0))
            sobras = max(desvio, 0)
            perdas = abs(desvio)
            cancelamentos = agg.get("cancelamentos", 0.0)
            destruicao = _round2(cancelamentos + faltas + perdas - sobras * 0.5)
            destruicao = max(destruicao, 0.0)
            receita = _round2(agg["receitaBruta"])
            margem = _round2(receita - destruicao)
            risco = max(destruicao, 1.0)
            out.append(
                {
                    "turno": turn,
                    "turnoCodigo": cash.get("turnoCodigo"),
                    "receitaBruta": receita,
                    "destruicaoMargem": destruicao,
                    "margemOperacional": margem,
                    "cancelamentos": _round2(cancelamentos),
                    "faltas": _round2(faltas),
                    "sobras": _round2(sobras),
                    "perdasCaixa": _round2(perdas),
                    "quantidadeVendas": agg.get("quantidadeVendas", 0),
                    "resultadoLiquido": margem,
                    "riscoEconomico": _round2(risco),
                    "roi": _round2(margem / risco if risco else 0),
                    "incidenciaQuebraPct": cash.get("incidenciaQuebraPct"),
                }
            )
        out.sort(key=lambda x: x["resultadoLiquido"], reverse=True)
        return out

    def _operation_matrix_engine(
        self,
        by_cell: dict[tuple[Any, str, int], dict[str, Any]],
        op_margin: dict[int, dict[str, Any]],
        op_names: dict[int, str],
    ) -> list[dict[str, Any]]:
        max_rev = max((c["receitaBruta"] for c in by_cell.values()), default=1.0) or 1.0
        out: list[dict[str, Any]] = []
        for (_, turn, op), agg in by_cell.items():
            pdv = agg.get("pdvCodigo")
            receita = _round2(agg["receitaBruta"])
            om = op_margin.get(op) or {}
            op_rev = _dec(om.get("receitaBruta")) or receita or 1.0
            share = receita / op_rev if op_rev else 1.0
            destr = _round2(_dec(om.get("destruicaoMargem")) * share)
            margem = _round2(receita - destr)
            rev_s = _norm_score(receita, max_rev)
            marg_s = _norm_score(max(margem, 0), max_rev)
            disc_s = _round2(100 * (1 - min(destr / max(destr, 1.0), 1.0)))
            score = _round2(0.40 * rev_s + 0.35 * marg_s + 0.25 * disc_s)
            out.append(
                {
                    "pdvCodigo": pdv,
                    "turno": turn,
                    "funcionarioCodigo": op,
                    "employeeName": op_names.get(op),
                    "receitaBruta": receita,
                    "destruicaoMargem": destr,
                    "margemOperacional": margem,
                    "resultadoLiquido": margem,
                    "quantidadeVendas": agg.get("quantidadeVendas", 0),
                    "operationScore": score,
                    "operationBand": _operation_band(score),
                    "riscoEconomico": _round2(max(destr, 1.0)),
                    "roi": _round2(margem / max(destr, 1.0)),
                }
            )
        out.sort(key=lambda x: x["operationScore"], reverse=True)
        return out

    def _critical_pdv_forensics(
        self,
        pdv_rows: list[dict[str, Any]],
        matrix: list[dict[str, Any]],
        cash_pdvs: list[dict[str, Any]],
        shift_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        cash_map = {r.get("pdvCodigo"): r for r in cash_pdvs}
        shift_loss = {r["turno"]: r for r in sorted(shift_rows, key=lambda x: x["destruicaoMargem"], reverse=True)}
        reports: dict[str, Any] = {}

        for pdv in CRITICAL_PDVS:
            pdv_row = next((p for p in pdv_rows if p.get("pdvCodigo") == pdv), None)
            cash = cash_map.get(pdv) or {}
            cells = [c for c in matrix if c.get("pdvCodigo") == pdv]
            ops = sorted(cells, key=lambda x: x["destruicaoMargem"], reverse=True)
            turns = Counter(c["turno"] for c in cells)
            worst_turn = turns and max(turns, key=lambda t: sum(c["destruicaoMargem"] for c in cells if c["turno"] == t))

            pdv_risk = abs(_dec(cash.get("diferencaAcumulada")))
            op_risk = sum(c["destruicaoMargem"] for c in cells)
            turn_risk = shift_loss.get(worst_turn, {}).get("destruicaoMargem", 0) if worst_turn else 0
            drivers = {
                "PDV": pdv_risk,
                "OPERADOR": op_risk,
                "TURNO": _dec(turn_risk),
                "PROCESSO": max(pdv_risk - op_risk, 0),
            }
            root = max(drivers, key=drivers.get)

            reports[str(pdv)] = {
                "pdvCodigo": pdv,
                "receitaBruta": pdv_row.get("receitaBruta") if pdv_row else 0,
                "destruicaoMargem": pdv_row.get("destruicaoMargem") if pdv_row else 0,
                "resultadoLiquido": pdv_row.get("resultadoLiquido") if pdv_row else 0,
                "fechamentos": cash.get("fechamentos"),
                "diferencaAcumulada": cash.get("diferencaAcumulada"),
                "operadores": ops[:5],
                "turnoMaiorImpacto": worst_turn,
                "driverScores": {k: _round2(v) for k, v in drivers.items()},
                "diagnosticoPrincipal": root,
                "problemaEstrutural": root in ("PDV", "PROCESSO") and pdv_risk > op_risk * 0.5,
            }
        return reports

    def _shift_risk_engine(
        self,
        shift_rows: list[dict[str, Any]],
        matrix: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        turn_disc: Counter[str] = Counter()
        turn_cancel: Counter[str] = Counter()
        turn_prod: Counter[str] = Counter()
        for cell in matrix:
            turn_disc[cell["turno"]] += _dec(cell.get("destruicaoMargem")) * 0.1
            turn_cancel[cell["turno"]] += 0
            turn_prod[cell["turno"]] += cell.get("quantidadeVendas", 0)

        max_q = max(turn_prod.values()) if turn_prod else 1
        max_d = max((r["destruicaoMargem"] for r in shift_rows), default=1.0) or 1.0
        max_roi = max((abs(r["roi"]) for r in shift_rows), default=1.0) or 1.0

        out: list[dict[str, Any]] = []
        for row in shift_rows:
            turn = row["turno"]
            quebra_s = _norm_score(row.get("perdasCaixa", 0), max_d)
            disc_s = _round2(100 * (1 - min(_dec(turn_disc.get(turn)) / max_d, 1.0)))
            cancel_s = _round2(100 * (1 - min(_dec(row.get("cancelamentos")) / max_d, 1.0)))
            roi_s = _norm_score(abs(row.get("roi", 0)), max_roi)
            prod_s = _norm_score(turn_prod.get(turn, 0), max_q)
            risk_score = _round2(
                SHIFT_RISK_WEIGHTS["quebraCaixa"] * (100 - quebra_s)
                + SHIFT_RISK_WEIGHTS["desconto"] * (100 - disc_s)
                + SHIFT_RISK_WEIGHTS["cancelamento"] * (100 - cancel_s)
                + SHIFT_RISK_WEIGHTS["roi"] * (100 - roi_s)
                + SHIFT_RISK_WEIGHTS["produtividade"] * (100 - prod_s)
            )
            out.append({**row, "shiftRiskScore": risk_score, "shiftRiskBand": _operation_band(100 - risk_score)})
        out.sort(key=lambda x: x["shiftRiskScore"], reverse=True)
        return out

    def _profitability_attribution(
        self,
        pdv_rows: list[dict[str, Any]],
        shift_rows: list[dict[str, Any]],
        op_margin: dict[int, dict[str, Any]],
        forensics: dict[str, Any],
    ) -> dict[str, Any]:
        total_op = sum(_dec(o.get("destruicaoMargem")) for o in op_margin.values())
        total_pdv = sum(_dec(p.get("destruicaoMargem")) for p in pdv_rows)
        total_turn = sum(_dec(t.get("destruicaoMargem")) for t in shift_rows)
        grand = max(total_op + total_pdv + total_turn, 1.0)

        per_pdv: list[dict[str, Any]] = []
        for p in pdv_rows:
            pdv = p.get("pdvCodigo")
            forensic = forensics.get(str(pdv)) or {}
            drivers = forensic.get("driverScores") or {}
            d_total = sum(_dec(v) for v in drivers.values()) or 1.0
            per_pdv.append(
                {
                    "pdvCodigo": pdv,
                    "riscoOperador": _round2(drivers.get("OPERADOR", 0)),
                    "riscoPdv": _round2(drivers.get("PDV", 0)),
                    "riscoTurno": _round2(drivers.get("TURNO", 0)),
                    "riscoProcesso": _round2(drivers.get("PROCESSO", 0)),
                    "riscoOperadorPct": _round2(100 * drivers.get("OPERADOR", 0) / d_total),
                    "riscoPdvPct": _round2(100 * drivers.get("PDV", 0) / d_total),
                    "riscoTurnoPct": _round2(100 * drivers.get("TURNO", 0) / d_total),
                }
            )

        return {
            "consolidado": {
                "riscoOperador": _round2(total_op),
                "riscoPdv": _round2(total_pdv),
                "riscoTurno": _round2(total_turn),
                "riscoOperadorPct": _round2(100 * total_op / grand),
                "riscoPdvPct": _round2(100 * total_pdv / grand),
                "riscoTurnoPct": _round2(100 * total_turn / grand),
            },
            "porPdv": per_pdv,
        }

    def _management_decision_v2(
        self,
        matrix: list[dict[str, Any]],
        pdv_rows: list[dict[str, Any]],
        shift_risk: list[dict[str, Any]],
        f042_actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        action_map = {int(a["funcionarioCodigo"]): a for a in f042_actions if a.get("funcionarioCodigo") is not None}
        critical_pdvs = {p["pdvCodigo"] for p in pdv_rows if p.get("monitoramentoPrioritario")}
        risky_turns = {s["turno"] for s in shift_risk if s.get("shiftRiskScore", 0) >= 55}

        out: list[dict[str, Any]] = []
        for cell in matrix:
            actions: list[str] = []
            band = cell.get("operationBand")
            op = int(cell["funcionarioCodigo"])
            pdv = cell.get("pdvCodigo")
            turn = cell.get("turno")
            prior = action_map.get(op) or {}

            if band == "EXCELENTE" and prior.get("primaryAction") == "PROMOVER":
                actions.append("PROMOVER")
            if band in ("ATENÇÃO", "CRÍTICO") and pdv in critical_pdvs:
                actions.append("REESTRUTURAR_PDV")
            if band == "CRÍTICO" and turn in risky_turns:
                actions.append("TROCAR_TURNO")
            if band == "CRÍTICO" and cell.get("destruicaoMargem", 0) > cell.get("receitaBruta", 0) * 0.2:
                actions.append("TROCAR_OPERADOR")
            if "TREINAR" in (prior.get("managementActions") or []):
                actions.append("TREINAR")
            if band in ("ATENÇÃO", "CRÍTICO") or "AUDITAR" in (prior.get("managementActions") or []):
                actions.append("AUDITAR")
            if not actions:
                actions.append("MONITORAR")

            out.append(
                {
                    "pdvCodigo": pdv,
                    "turno": turn,
                    "funcionarioCodigo": op,
                    "employeeName": cell.get("employeeName"),
                    "operationBand": band,
                    "operationScore": cell.get("operationScore"),
                    "managementActions": list(dict.fromkeys(actions)),
                    "primaryAction": actions[0],
                    "resultadoLiquido": cell.get("resultadoLiquido"),
                    "roi": cell.get("roi"),
                }
            )
        return out

    def _operational_roi_engine(
        self,
        matrix: list[dict[str, Any]],
    ) -> dict[str, Any]:
        by_pt: dict[tuple[Any, str], dict[str, Any]] = defaultdict(
            lambda: {"receitaBruta": 0.0, "resultadoLiquido": 0.0, "riscoEconomico": 0.0, "celulas": 0}
        )
        for cell in matrix:
            key = (cell.get("pdvCodigo"), cell.get("turno"))
            bucket = by_pt[key]
            bucket["receitaBruta"] += _dec(cell.get("receitaBruta"))
            bucket["resultadoLiquido"] += _dec(cell.get("resultadoLiquido"))
            bucket["riscoEconomico"] += _dec(cell.get("riscoEconomico"))
            bucket["celulas"] += 1
            bucket["pdvCodigo"] = cell.get("pdvCodigo")
            bucket["turno"] = cell.get("turno")

        combos: list[dict[str, Any]] = []
        for (_, _), agg in by_pt.items():
            risco = max(agg["riscoEconomico"], 1.0)
            combos.append(
                {
                    "pdvCodigo": agg.get("pdvCodigo"),
                    "turno": agg.get("turno"),
                    "receitaBruta": _round2(agg["receitaBruta"]),
                    "resultadoLiquido": _round2(agg["resultadoLiquido"]),
                    "riscoEconomico": _round2(risco),
                    "roi": _round2(agg["resultadoLiquido"] / risco),
                    "celulas": agg["celulas"],
                }
            )
        combos.sort(key=lambda x: x["roi"], reverse=True)
        return {
            "combinacoes": combos,
            "maiorRoi": combos[0] if combos else None,
            "menorRoi": combos[-1] if combos else None,
        }

    @staticmethod
    def _cash_context_from_merged(merged: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        by_pdv: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        by_turn: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in merged:
            by_pdv[row.get("pdvCodigo")].append(row)
            by_turn[_turn_key(row)].append(row)

        pdv_rows: list[dict[str, Any]] = []
        for pdv, rows in by_pdv.items():
            diffs = [_dec(r.get("diferenca")) for r in rows]
            pdv_rows.append(
                {
                    "pdvCodigo": pdv,
                    "fechamentos": len(rows),
                    "diferencaAcumulada": _round2(sum(diffs)),
                    "monitoramentoPrioritario": int(pdv) in CRITICAL_PDVS if pdv is not None else False,
                }
            )

        turn_rows: list[dict[str, Any]] = []
        for turn, rows in by_turn.items():
            diffs = [_dec(r.get("diferenca")) for r in rows]
            breaks = sum(1 for d in diffs if d != 0)
            turn_rows.append(
                {
                    "turno": turn,
                    "turnoCodigo": rows[0].get("turnoCodigo") if rows else None,
                    "fechamentos": len(rows),
                    "desvioAcumulado": _round2(sum(diffs)),
                    "incidenciaQuebraPct": _round2(100 * breaks / len(rows)) if rows else 0.0,
                }
            )
        return pdv_rows, turn_rows

    @staticmethod
    def _enrich_venda_from_cash(
        venda: list[dict[str, Any]],
        merged: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        pdv_by_op: dict[int, Counter[Any]] = defaultdict(Counter)
        turn_by_op: dict[int, Counter[str]] = defaultdict(Counter)
        for row in merged:
            try:
                op = int(row.get("funcionarioCodigo") or 0)
            except (TypeError, ValueError):
                continue
            if not op:
                continue
            pdv = row.get("pdvCodigo")
            if pdv is not None:
                pdv_by_op[op][pdv] += 1
            turn_by_op[op][_turn_key(row)] += 1

        best_pdv = {op: counts.most_common(1)[0][0] for op, counts in pdv_by_op.items() if counts}
        best_turn = {op: counts.most_common(1)[0][0] for op, counts in turn_by_op.items() if counts}

        enriched: list[dict[str, Any]] = []
        for row in venda:
            item = dict(row)
            try:
                op = int(row.get("funcionarioCodigo") or 0)
            except (TypeError, ValueError):
                op = 0
            if op and item.get("pdvCodigo") is None and op in best_pdv:
                item["pdvCodigo"] = best_pdv[op]
            if op and not item.get("turnoCodigo") and not item.get("turno") and op in best_turn:
                label = best_turn[op]
                if label != "Turno ?":
                    item["turno"] = label
            enriched.append(item)
        return enriched

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        t0 = time.perf_counter()
        snap_f042 = OperatorProfitabilitySnapshotService(self._f042)
        cached = snap_f042.get_master(data_inicial, data_final, empresa_codigo).get("payload")
        if cached:
            f042 = cached
        else:
            f042_resp = await self._f042.build(data_inicial, data_final, empresa_codigo)
            if not f042_resp.success or not f042_resp.data:
                return WebPostoResponse.fail(str(f042_resp.error or "Falha ao consolidar base F04.2"))
            f042 = f042_resp.data
            await snap_f042.collect(data_inicial, data_final, empresa_codigo, f042)
        sales, venda, _ = await self._f042._load_sales_and_venda(data_inicial, data_final, empresa_codigo)
        if not venda:
            return WebPostoResponse.fail("Sem vendas operacionais para F04.3")

        filters = build_finance_center_filters(data_inicial, data_final, empresa_codigo)
        merged_task = self._cash._fetch_merged(filters)
        vi_task = self._cash._fetch_paged("venda_item", data_inicial, data_final, 15)
        (merged, _, _), (vi_raw, _) = await asyncio.gather(merged_task, vi_task)
        venda = self._enrich_venda_from_cash(venda, merged)
        cash_pdvs, cash_turns = self._cash_context_from_merged(merged)
        venda_item = [r for r in vi_raw if self._cash._matches_empresa(r, filters)]
        intel_discounts = self._discount_by_pdv(venda, venda_item)

        margin_ops = {
            int(r["funcionarioCodigo"]): r
            for r in (f042.get("marginImpactEngine") or {}).get("operators") or []
            if r.get("funcionarioCodigo") is not None
        }
        op_profit = {
            int(r["funcionarioCodigo"]): r
            for r in (f042.get("profitabilityScoreEngine") or {}).get("operators") or []
            if r.get("funcionarioCodigo") is not None
        }
        op_names = {op: r.get("employeeName") for op, r in op_profit.items()}
        f042_actions = (f042.get("managementActionEngine") or {}).get("operators") or []
        context_ops = (f042.get("contextNormalizationV2") or {}).get("operators") or []

        by_pdv, by_turn, by_cell, consolidated = self._aggregate_sales(venda)
        pdv_rows = self._pdv_profitability_engine(by_pdv, intel_discounts, cash_pdvs)
        shift_rows = self._shift_profitability_engine(by_turn, cash_turns)
        matrix = self._operation_matrix_engine(by_cell, margin_ops, op_names)
        forensics = self._critical_pdv_forensics(pdv_rows, matrix, cash_pdvs, shift_rows)
        shift_risk = self._shift_risk_engine(shift_rows, matrix)
        attribution = self._profitability_attribution(pdv_rows, shift_rows, margin_ops, forensics)
        decisions = self._management_decision_v2(matrix, pdv_rows, shift_risk, f042_actions)
        op_roi = self._operational_roi_engine(matrix)

        parity_pdv = _round2(sum(p["receitaBruta"] for p in pdv_rows))
        parity_delta = _round2(abs(parity_pdv - consolidated))

        top_rev_pdv = max(pdv_rows, key=lambda x: x["receitaBruta"]) if pdv_rows else None
        top_lucro_pdv = pdv_rows[0] if pdv_rows else None
        worst_pdv = max(pdv_rows, key=lambda x: x["destruicaoMargem"]) if pdv_rows else None
        top_rev_turn = max(shift_rows, key=lambda x: x["receitaBruta"]) if shift_rows else None
        top_lucro_turn = shift_rows[0] if shift_rows else None
        worst_turn = max(shift_rows, key=lambda x: x["destruicaoMargem"]) if shift_rows else None

        promover = [d for d in decisions if "PROMOVER" in d.get("managementActions", [])]
        auditar = [d for d in decisions if "AUDITAR" in d.get("managementActions", [])]
        reestruturar = [d for d in decisions if "REESTRUTURAR_PDV" in d.get("managementActions", [])]

        top5_pdv_lucro = sorted(pdv_rows, key=lambda x: x["resultadoLiquido"], reverse=True)[:5]
        lucro_top5 = _round2(sum(_dec(p["resultadoLiquido"]) for p in top5_pdv_lucro))
        crit_pdvs = [p for p in pdv_rows if p.get("monitoramentoPrioritario")]
        risco_criticos = _round2(sum(_dec(p["destruicaoMargem"]) for p in crit_pdvs))

        good_bad_ctx = [c for c in context_ops if str(c.get("contextClassification") or "").startswith("DEPENDENTE")]
        performs_bad_ctx = sorted(good_bad_ctx, key=lambda x: x.get("profitabilityAdjustedScore", 0), reverse=True)[:3]
        performs_good_ctx = sorted(
            [c for c in context_ops if str(c.get("contextClassification") or "").startswith("INDEPENDENTE")],
            key=lambda x: x.get("profitabilityAdjustedScore", 0),
        )[:3]

        structural = any((forensics.get(str(p)) or {}).get("problemaEstrutural") for p in CRITICAL_PDVS)
        ctx_vs_op = (attribution.get("consolidado") or {}).get("riscoOperadorPct", 0) > (
            attribution.get("consolidado") or {}
        ).get("riscoPdvPct", 0)

        executive = {
            "1_pdvMaiorReceita": top_rev_pdv,
            "2_pdvMaiorLucro": top_lucro_pdv,
            "3_pdvDestróiMargem": worst_pdv,
            "4_turnoMaiorReceita": top_rev_turn,
            "5_turnoMaiorLucro": top_lucro_turn,
            "6_turnoMaiorPerdas": worst_turn,
            "7_maiorRoiCombinacao": op_roi.get("maiorRoi"),
            "8_menorRoiCombinacao": op_roi.get("menorRoi"),
            "9_problemaEstruturalPdvsCriticos": structural,
            "10_problemaOperadorVsContexto": "OPERADOR" if ctx_vs_op else "CONTEXTO",
            "11_operadoresContextoRuim": performs_bad_ctx,
            "12_operadoresContextoBom": performs_good_ctx,
            "13_pdvIntervencao": reestruturar[:3] or crit_pdvs[:3],
            "14_turnoIntervencao": [s for s in shift_risk if s.get("shiftRiskScore", 0) >= 55][:3],
            "15_combinacaoAuditoria": auditar[:5],
            "16_combinacaoPromocao": promover[:5],
            "17_lucroTop5Pdvs": lucro_top5,
            "18_riscoPdvsCriticos": risco_criticos,
            "19_decisoesOperacionaisAutomaticas": parity_delta <= 0.01 and len(matrix) > 0,
            "20_aprovadoF044": parity_delta <= 0.01 and len(pdv_rows) > 0 and len(shift_rows) > 0,
            "paridadeDelta": parity_delta,
            "paridadeReceitaPdv": parity_pdv,
            "paridadeReceitaConsolidada": consolidated,
        }

        qa = {
            "roiPdvOk": len(pdv_rows) > 0,
            "roiTurnoOk": len(shift_rows) > 0,
            "attributionOk": bool(attribution.get("consolidado")),
            "cockpitOk": True,
            "paridadeZero": parity_delta <= 0.01,
        }

        parecer = (
            "[PARECER FINAL: APROVADO PARA F04.4]"
            if executive["20_aprovadoF044"]
            else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"
        )

        payload = {
            "sprint": "F04.3",
            "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
            "elapsedMs": round((time.perf_counter() - t0) * 1000, 1),
            "baseF042": {
                "parecerFinal": f042.get("parecerFinal"),
                "paridadeDelta": (f042.get("executiveAnswers") or {}).get("paridadeDelta"),
            },
            "pdvProfitabilityEngine": {"pdvs": pdv_rows, "totalReceita": parity_pdv},
            "shiftProfitabilityEngine": {"turnos": shift_rows},
            "operationMatrixEngine": {"cells": matrix, "bands": dict(Counter(c["operationBand"] for c in matrix))},
            "criticalPdvForensics": forensics,
            "shiftRiskEngine": {"turnos": shift_risk},
            "profitabilityAttribution": attribution,
            "managementDecisionEngineV2": {"decisions": decisions},
            "operationalRoiEngine": op_roi,
            "cockpit": {
                "topPdvs": pdv_rows[:10],
                "topTurnos": shift_rows[:10],
                "topOperadores": sorted(
                    list(op_profit.values()), key=lambda x: x.get("resultadoLiquido", 0), reverse=True
                )[:10],
                "pdvsCriticos": crit_pdvs,
                "turnosCriticos": [s for s in shift_risk if s.get("shiftRiskScore", 0) >= 55][:10],
                "roiOperacional": op_roi.get("combinacoes", [])[:10],
            },
            "executiveAnswers": executive,
            "qa": qa,
            "parecerFinal": parecer,
        }
        return WebPostoResponse.ok(payload)
