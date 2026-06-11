"""F03.4 — Operator Performance Intelligence (camada aditiva sobre Cash Ops + Employee Ledger)."""
from __future__ import annotations

import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.cash_operations_service import (
    CRITICAL_OPERATORS,
    CRITICAL_PDVS,
    CashOperationsService,
    _dec,
    _risk_band,
    _round2,
)
from src.services.network_financial_overview_service import FinancialOverviewFilters

PERFORMANCE_BANDS = (
    (90, 100, "Excelente"),
    (75, 89, "Bom"),
    (60, 74, "Atencao"),
    (0, 59, "Critico"),
)

W_DIFF = 0.40
W_RECURRENCE = 0.25
W_RISK = 0.15
W_COMPENSATED = 0.10
W_EVOLUTION = 0.10

WINDOW_PRESETS = {
    "7d": 6,
    "30d": 29,
    "90d": 89,
}


def _performance_band(score: float) -> str:
    s = int(round(score))
    for lo, hi, label in PERFORMANCE_BANDS:
        if lo <= s <= hi:
            return label
    return "Critico"


def _window_dates(data_final: str, days_back: int) -> tuple[str, str]:
    end = datetime.fromisoformat(data_final)
    start = end - timedelta(days=days_back)
    return start.isoformat()[:10], data_final


class OperatorPerformanceService:
    """Operator Performance Layer — não altera Cash Operations nem Employee Ledger."""

    def __init__(self, cash_ops: CashOperationsService | None = None) -> None:
        self._cash = cash_ops or CashOperationsService()

    async def _ledger_balances(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
    ) -> dict[Any, dict[str, Any]]:
        try:
            from src.services.employee_cash_ledger_service import EmployeeCashLedgerService
            from src.services.expense_lineage_service import ExpenseLineageService
            from src.services.expense_semantic_service import ExpenseSemanticService
            from src.services.management_classification_service import ManagementClassificationService

            filters = FinancialOverviewFilters(data_inicial=data_inicial, data_final=data_final)
            if empresa_codigo:
                try:
                    codes = [int(c.strip()) for c in str(empresa_codigo).split(",") if c.strip()]
                    filters = FinancialOverviewFilters(
                        data_inicial=data_inicial,
                        data_final=data_final,
                        empresa_codigos=tuple(codes) if len(codes) > 1 else None,
                        empresa_codigo=codes[0] if len(codes) == 1 else None,
                    )
                except ValueError:
                    pass

            ledger = EmployeeCashLedgerService()
            lineage = ExpenseLineageService()
            semantic = ExpenseSemanticService()
            mgmt = ManagementClassificationService()
            ctx = await lineage.build_context(self._cash._overview, filters)
            caixa_rows = list(ctx.closure_by_key.values())
            rows, err = await self._cash._overview._load_screen_expenses(filters)
            if err:
                return {}
            enriched = [
                mgmt.classify_row(semantic.classify_row(lineage.enrich_row(r, ctx)))
                for r in (rows or [])
            ]
            caixa_events = ledger.build_caixa_events(caixa_rows)
            expense_events = ledger.build_expense_events(enriched)
            balance_by_op = ledger.build_balance_by_operator(caixa_events, expense_events)
            return {k: v for k, v in balance_by_op.items() if k != "__SEM_OPERADOR__"}
        except Exception:
            return {}

    @staticmethod
    def _merged_rows(cash_payload: dict[str, Any]) -> list[dict[str, Any]]:
        return cash_payload.get("_merged") or []

    async def _cash_window(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
    ) -> dict[str, Any] | None:
        resp = await self._cash.build(data_inicial, data_final, empresa_codigo)
        if not resp.success or not resp.data:
            return None
        merged, _, _ = await self._cash._fetch_merged(
            build_finance_center_filters(data_inicial, data_final, empresa_codigo)
        )
        data = dict(resp.data)
        data["_merged"] = merged
        return data

    @staticmethod
    def _diff_component(items: list[dict[str, Any]], key: str = "diferencaAcumulada") -> None:
        abs_vals = [abs(_dec(i.get(key))) for i in items]
        mx = max(abs_vals) if abs_vals else 1.0
        mx = mx or 1.0
        for item in items:
            raw = abs(_dec(item.get(key)))
            item["componentDiferenca"] = _round2(100.0 * (1.0 - min(raw / mx, 1.0)))

    @staticmethod
    def _recurrence_component(items: list[dict[str, Any]]) -> None:
        for item in items:
            rec = float(item.get("indiceRecorrencia") or item.get("incidenciaQuebraPct") or 0)
            if rec > 1:
                rec = rec / 100.0
            item["componentRecorrencia"] = _round2(max(0.0, 100.0 * (1.0 - min(rec, 1.0))))

    @staticmethod
    def _risk_component(items: list[dict[str, Any]]) -> None:
        for item in items:
            item["componentRisk"] = _round2(float(item.get("cashRiskScore") or 50.0))

    @staticmethod
    def _compensated_component(items: list[dict[str, Any]], ledger: dict[Any, dict[str, Any]]) -> None:
        for item in items:
            op = item.get("funcionarioCodigo")
            bal = ledger.get(op) or {}
            faltas = float(bal.get("faltas") or 0)
            comp = float(bal.get("compensadoAutomatico") or 0)
            ratio = min(comp / faltas, 1.0) if faltas > 0 else (1.0 if comp > 0 else 0.5)
            item["componentCompensado"] = _round2(100.0 * ratio)
            item["saldoLedger"] = bal.get("saldo")
            item["compensadoAutomatico"] = comp

    @staticmethod
    def _evolution_component(
        items: list[dict[str, Any]],
        prior_scores: dict[Any, float],
    ) -> None:
        for item in items:
            op = item.get("funcionarioCodigo") or item.get("pdvCodigo") or item.get("turnoCodigo")
            prior = prior_scores.get(op)
            if prior is None:
                item["componentEvolucao"] = 50.0
                item["evolucaoDelta"] = 0.0
                continue
            current = float(item.get("_rawScore") or 50.0)
            delta = current - prior
            item["evolucaoDelta"] = _round2(delta)
            item["componentEvolucao"] = _round2(max(0.0, min(100.0, 50.0 + delta)))

    @staticmethod
    def _finalize_score(item: dict[str, Any]) -> None:
        score = (
            W_DIFF * float(item.get("componentDiferenca") or 0)
            + W_RECURRENCE * float(item.get("componentRecorrencia") or 0)
            + W_RISK * float(item.get("componentRisk") or 0)
            + W_COMPENSATED * float(item.get("componentCompensated") or item.get("componentCompensado") or 50)
            + W_EVOLUTION * float(item.get("componentEvolucao") or 50)
        )
        item["operatorPerformanceScore"] = _round2(score)
        item["performanceScore"] = _round2(score)
        item["performanceBand"] = _performance_band(score)

    def _score_operators(
        self,
        cash_payload: dict[str, Any],
        ledger: dict[Any, dict[str, Any]],
        prior_scores: dict[Any, float] | None = None,
    ) -> list[dict[str, Any]]:
        ops_data = cash_payload.get("operators") or {}
        items = [dict(x) for x in (ops_data.get("todos") or [])]
        if not items:
            risk_ops = (cash_payload.get("riskScore") or {}).get("operadores") or []
            items = [dict(x) for x in risk_ops]

        self._diff_component(items)
        self._recurrence_component(items)
        self._risk_component(items)
        self._compensated_component(items, ledger)

        for item in items:
            item["_rawScore"] = (
                0.55 * float(item.get("componentDiferenca") or 0)
                + 0.25 * float(item.get("componentRecorrencia") or 0)
                + 0.20 * float(item.get("componentRisk") or 0)
            )
        self._evolution_component(items, prior_scores or {})
        for item in items:
            self._finalize_score(item)
            op = item.get("funcionarioCodigo")
            item["monitoramentoPrioritario"] = int(op) in CRITICAL_OPERATORS if op is not None else False

        items.sort(key=lambda x: x.get("performanceScore") or 0, reverse=True)
        return items

    def _score_pdvs(
        self,
        cash_payload: dict[str, Any],
        prior_scores: dict[Any, float] | None = None,
    ) -> list[dict[str, Any]]:
        pdv_data = cash_payload.get("pdvs") or {}
        items = [dict(x) for x in (pdv_data.get("ranking") or [])]
        for item in items:
            breaks = item.get("fechamentos") or 1
            rec = abs(_dec(item.get("diferencaAcumulada"))) / breaks
            item["indiceRecorrencia"] = _round2(min(rec / 100.0, 1.0))
            item["diferencaAcumulada"] = item.get("diferencaAcumulada")

        self._diff_component(items, "diferencaAcumulada")
        self._recurrence_component(items)
        self._risk_component(items)
        for item in items:
            item["componentCompensado"] = 50.0
            item["_rawScore"] = (
                0.55 * float(item.get("componentDiferenca") or 0)
                + 0.25 * float(item.get("componentRecorrencia") or 0)
                + 0.20 * float(item.get("componentRisk") or 0)
            )
        self._evolution_component(items, prior_scores or {})
        for item in items:
            self._finalize_score(item)
            pdv = item.get("pdvCodigo")
            item["monitoramentoPrioritario"] = int(pdv) in CRITICAL_PDVS if pdv is not None else False

        items.sort(key=lambda x: x.get("performanceScore") or 0, reverse=True)
        return items

    def _score_turns(
        self,
        cash_payload: dict[str, Any],
        prior_scores: dict[Any, float] | None = None,
    ) -> list[dict[str, Any]]:
        turn_data = cash_payload.get("turns") or {}
        items = [dict(x) for x in (turn_data.get("porTurno") or [])]
        for item in items:
            item["diferencaAcumulada"] = item.get("desvioAcumulado")
            item["indiceRecorrencia"] = float(item.get("incidenciaQuebraPct") or 0) / 100.0
            item["cashRiskScore"] = {"Excelente": 95, "Bom": 80, "Atencao": 65, "Critico": 40}.get(
                str(item.get("matrizRisco") or ""), 50
            )

        self._diff_component(items, "diferencaAcumulada")
        self._recurrence_component(items)
        self._risk_component(items)
        for item in items:
            item["componentCompensado"] = 50.0
            item["_rawScore"] = (
                0.55 * float(item.get("componentDiferenca") or 0)
                + 0.25 * float(item.get("componentRecorrencia") or 0)
                + 0.20 * float(item.get("componentRisk") or 0)
            )
        self._evolution_component(items, prior_scores or {})
        for item in items:
            self._finalize_score(item)

        items.sort(key=lambda x: x.get("performanceScore") or 0, reverse=True)
        return items

    @staticmethod
    def _filial_performance(merged: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_emp: dict[Any, list[dict]] = defaultdict(list)
        for row in merged:
            by_emp[row.get("empresaCodigo")].append(row)

        items: list[dict[str, Any]] = []
        for emp, rows in by_emp.items():
            diffs = [_dec(r.get("diferenca")) for r in rows]
            breaks = sum(1 for d in diffs if d != 0)
            items.append(
                {
                    "empresaCodigo": emp,
                    "fechamentos": len(rows),
                    "diferencaAcumulada": _round2(sum(diffs)),
                    "diferencaMedia": _round2(statistics.mean(diffs)) if diffs else 0.0,
                    "incidenciaQuebraPct": _round2(100 * breaks / len(rows)) if rows else 0.0,
                }
            )
        items.sort(key=lambda x: abs(x["diferencaAcumulada"]))
        return items

    @staticmethod
    def _heatmaps(merged: list[dict[str, Any]]) -> dict[str, Any]:
        op_pdv: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        op_turn: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for row in merged:
            op = str(row.get("funcionarioCodigo") or "?")
            pdv = str(row.get("pdvCodigo") or "?")
            turn = str(row.get("turno") or row.get("turnoCodigo") or "?")
            val = abs(_dec(row.get("diferenca")))
            op_pdv[op][pdv] += val
            op_turn[op][turn] += val

        def cells(matrix: dict[str, dict[str, float]], row_label: str, col_label: str) -> dict[str, Any]:
            rows = sorted(matrix.keys())
            cols = sorted({c for r in matrix.values() for c in r.keys()})
            out = []
            for r in rows:
                for c in cols:
                    if c in matrix[r]:
                        out.append({row_label: r, col_label: c, "impactoAbsoluto": _round2(matrix[r][c])})
            return {"rows": rows, "cols": cols, "cells": out}

        return {
            "operadorPdv": cells(op_pdv, "funcionarioCodigo", "pdvCodigo"),
            "operadorTurno": cells(op_turn, "funcionarioCodigo", "turno"),
        }

    @staticmethod
    def _evolution_report(
        windows: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        scores_7 = {
            o.get("funcionarioCodigo"): o.get("performanceScore")
            for o in (windows.get("7d", {}).get("operators") or [])
        }
        scores_30 = {
            o.get("funcionarioCodigo"): o.get("performanceScore")
            for o in (windows.get("30d", {}).get("operators") or [])
        }
        scores_90 = {
            o.get("funcionarioCodigo"): o.get("performanceScore")
            for o in (windows.get("90d", {}).get("operators") or [])
        }

        improving: list[dict[str, Any]] = []
        worsening: list[dict[str, Any]] = []
        for op, s90 in scores_90.items():
            if op is None:
                continue
            s7 = scores_7.get(op)
            s30 = scores_30.get(op)
            if s7 is None or s30 is None:
                continue
            delta = float(s90 or 0) - float(s7 or 0)
            entry = {
                "funcionarioCodigo": op,
                "score7d": s7,
                "score30d": s30,
                "score90d": s90,
                "delta90vs7": _round2(delta),
            }
            if delta >= 5:
                improving.append(entry)
            elif delta <= -5:
                worsening.append(entry)

        improving.sort(key=lambda x: x["delta90vs7"], reverse=True)
        worsening.sort(key=lambda x: x["delta90vs7"])

        def band_transitions(items: list[dict[str, Any]], window_key: str) -> list[dict[str, Any]]:
            out = []
            for op_item in items[:50]:
                op = op_item.get("funcionarioCodigo")
                w7 = next((x for x in windows.get("7d", {}).get("operators") or [] if x.get("funcionarioCodigo") == op), {})
                w90 = next((x for x in windows.get("90d", {}).get("operators") or [] if x.get("funcionarioCodigo") == op), {})
                b7 = w7.get("performanceBand")
                b90 = w90.get("performanceBand")
                if b7 and b90 and b7 != b90:
                    out.append({"funcionarioCodigo": op, "de": b7, "para": b90, "window": window_key})
            return out[:20]

        return {
            "melhorando": improving[:20],
            "piorando": worsening[:20],
            "transicoesBanda": band_transitions(improving + worsening, "7d->90d"),
            "melhoraRede90d": _round2(
                statistics.mean([x["delta90vs7"] for x in improving]) if improving else 0.0
            ),
        }

    @staticmethod
    def _best_practices(
        operators: list[dict[str, Any]],
        pdvs: list[dict[str, Any]],
        turns: list[dict[str, Any]],
    ) -> dict[str, Any]:
        top_ops = operators[:5]
        low_risk_pdvs = sorted(pdvs, key=lambda x: x.get("performanceScore") or 0, reverse=True)[:5]
        best_turns = turns[:3]
        return {
            "padraoVencedor": {
                "operadoresReferencia": [o.get("funcionarioCodigo") for o in top_ops],
                "scoreMedioTop5": _round2(statistics.mean([o.get("performanceScore") or 0 for o in top_ops]))
                if top_ops
                else 0.0,
                "recorrenciaMediaTop5": _round2(
                    statistics.mean([o.get("indiceRecorrencia") or 0 for o in top_ops])
                )
                if top_ops
                else 0.0,
            },
            "pdvsMenorRisco": low_risk_pdvs,
            "turnosMelhorResultado": best_turns,
            "insights": [
                "Melhores operadores combinam baixa recorrência de quebra e alto índice de compensação por sobras.",
                "PDVs saudáveis apresentam desvio padrão inferior à média da rede.",
                "Turnos com menor incidência de quebra concentram volume financeiro estável.",
            ],
        }

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        include_windows: bool = True,
    ) -> WebPostoResponse:
        t0 = time.perf_counter()
        ledger = await self._ledger_balances(data_inicial, data_final, empresa_codigo)

        cash_main = await self._cash_window(data_inicial, data_final, empresa_codigo)
        if not cash_main:
            return WebPostoResponse.fail("Falha ao consolidar performance operacional")

        prior_op: dict[Any, float] = {}
        prior_pdv: dict[Any, float] = {}
        prior_turn: dict[Any, float] = {}
        window_payloads: dict[str, dict[str, Any]] = {}

        if include_windows:
            end = data_final
            for label, days in WINDOW_PRESETS.items():
                di, df = _window_dates(end, days)
                payload = await self._cash_window(di, df, empresa_codigo)
                if not payload:
                    continue
                leg = await self._ledger_balances(di, df, empresa_codigo)
                ops = self._score_operators(payload, leg)
                pdvs = self._score_pdvs(payload)
                turns = self._score_turns(payload)
                window_payloads[label] = {
                    "periodo": {"dataInicial": di, "dataFinal": df},
                    "operators": ops,
                    "pdvs": pdvs,
                    "turns": turns,
                }
            if "7d" in window_payloads and "90d" in window_payloads:
                prior_op = {
                    o.get("funcionarioCodigo"): o.get("performanceScore")
                    for o in window_payloads["7d"]["operators"]
                }

        operators = self._score_operators(cash_main, ledger, prior_op)
        pdvs = self._score_pdvs(cash_main, prior_pdv)
        turns = self._score_turns(cash_main, prior_turn)
        merged = self._merged_rows(cash_main)
        filiais = self._filial_performance(merged)
        heatmaps = self._heatmaps(merged)
        evolution = self._evolution_report(window_payloads) if window_payloads else {}
        best = self._best_practices(operators, pdvs, turns)

        from src.services.operator_context_attribution_service import OperatorContextAttributionService

        context_attribution = OperatorContextAttributionService.build(
            merged, operators, pdvs, turns, filiais
        )

        scores = [o.get("performanceScore") or 0 for o in operators]
        bands = Counter(o.get("performanceBand") for o in operators)

        best_op = operators[0] if operators else None
        worst_op = operators[-1] if operators else None
        best_pdv = pdvs[0] if pdvs else None
        worst_pdv = pdvs[-1] if pdvs else None
        best_turn = turns[0] if turns else None
        worst_turn = turns[-1] if turns else None

        critical_focus = {
            "operador276288": next((o for o in operators if o.get("funcionarioCodigo") == 276288), None),
            "operador294273": next((o for o in operators if o.get("funcionarioCodigo") == 294273), None),
            "pdv54193": next((p for p in pdvs if p.get("pdvCodigo") == 54193), None),
            "pdv15880": next((p for p in pdvs if p.get("pdvCodigo") == 15880), None),
        }

        total_ms = round((time.perf_counter() - t0) * 1000, 1)

        payload = {
            "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
            "summary": {
                "operatorPerformanceScoreMedio": _round2(statistics.mean(scores)) if scores else 0.0,
                "operadoresClassificados": len(operators),
                "pdvsClassificados": len(pdvs),
                "turnosClassificados": len(turns),
                "bandas": dict(bands),
                "criticos": bands.get("Critico", 0),
                "excelentes": bands.get("Excelente", 0),
                "melhorOperador": best_op,
                "piorOperador": worst_op,
                "melhorPdv": best_pdv,
                "piorPdv": worst_pdv,
                "melhorTurno": best_turn,
                "piorTurno": worst_turn,
                "melhoraOperacional90d": evolution.get("melhoraRede90d"),
            },
            "operators": {
                "total": len(operators),
                "ranking": operators[:20],
                "topMelhores": operators[:20],
                "topPiores": list(reversed(operators[-20:])),
                "todos": operators,
            },
            "pdvs": {
                "total": len(pdvs),
                "ranking": pdvs[:20],
                "topMelhores": pdvs[:20],
                "topPiores": list(reversed(pdvs[-20:])),
                "alvosCriticos": critical_focus,
            },
            "turns": {
                "total": len(turns),
                "ranking": turns,
                "topMelhores": turns[:20],
                "topPiores": list(reversed(turns[-20:])),
            },
            "filiais": filiais,
            "heatmaps": heatmaps,
            "evolution": evolution,
            "bestPractices": best,
            "contextAttribution": context_attribution,
            "windows": window_payloads,
            "criticalFocus": critical_focus,
            "formula": {
                "pesos": {
                    "diferencaCaixa": W_DIFF,
                    "recorrencia": W_RECURRENCE,
                    "cashRiskScore": W_RISK,
                    "sobrasCompensadas": W_COMPENSATED,
                    "evolucaoTemporal": W_EVOLUTION,
                },
                "bandas": list(PERFORMANCE_BANDS),
            },
            "performanceMs": {"total": total_ms},
        }
        return WebPostoResponse.ok(payload)
