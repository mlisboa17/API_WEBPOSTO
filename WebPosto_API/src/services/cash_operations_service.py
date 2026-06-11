"""Sprint F03 — Cash Operations Intelligence (alertas, risk score, analytics)."""
from __future__ import annotations

import asyncio
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from src.gateway.webposto_client import WebPostoClient
from src.models.response_model import WebPostoResponse
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.network_financial_overview_service import (
    FinancialOverviewFilters,
    NetworkFinancialOverviewService,
)

ALERT_INFO_MIN = 0.01
ALERT_ATENCAO = 20.0
ALERT_ALTO = 50.0
ALERT_CRITICO = 100.0

W_OPERATOR = 0.40
W_PDV = 0.25
W_TURN = 0.20
W_HIST = 0.15

RISK_BANDS = (
    (90, 100, "Excelente"),
    (75, 89, "Bom"),
    (60, 74, "Atencao"),
    (0, 59, "Critico"),
)

CRITICAL_OPERATORS = {276288, 294273}
CRITICAL_PDVS = {54193, 15880}


def _dec(value: Any) -> float:
    try:
        return float(Decimal(str(value or 0)))
    except Exception:
        return 0.0


def _round2(value: float) -> float:
    return round(value, 2)


def _risk_band(score: float) -> str:
    s = int(round(score))
    for lo, hi, label in RISK_BANDS:
        if lo <= s <= hi:
            return label
    return "Critico"


def _alert_level(abs_diff: float, consecutive: int, pdv_breaks_30d: int) -> str:
    if abs_diff >= ALERT_CRITICO or consecutive >= 3 or pdv_breaks_30d >= 5:
        return "CRITICO"
    if abs_diff >= ALERT_ALTO:
        return "ALTO"
    if abs_diff >= ALERT_ATENCAO:
        return "ATENCAO"
    if abs_diff >= ALERT_INFO_MIN:
        return "INFO"
    return "OK"


class CashOperationsService:
    def __init__(self, client: WebPostoClient | None = None) -> None:
        self._client = client or WebPostoClient()
        self._overview = NetworkFinancialOverviewService(self._client)

    @staticmethod
    def _rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [r for r in payload if isinstance(r, dict)]
        if isinstance(payload, dict):
            for key in ("resultados", "data", "items", "content"):
                chunk = payload.get(key)
                if isinstance(chunk, list):
                    return [r for r in chunk if isinstance(r, dict)]
        return []

    @staticmethod
    def _matches_empresa(row: dict[str, Any], filters: FinancialOverviewFilters) -> bool:
        if not filters.empresa_codigos:
            return True
        code = row.get("empresaCodigo")
        try:
            return int(code) in filters.empresa_codigos
        except (TypeError, ValueError):
            return False

    async def _fetch_paged(
        self,
        endpoint_key: str,
        data_inicial: str,
        data_final: str,
        max_pages: int = 20,
    ) -> tuple[list[dict[str, Any]], float]:
        t0 = time.perf_counter()
        params: dict[str, Any] = {"dataInicial": data_inicial, "dataFinal": data_final}
        all_rows: list[dict[str, Any]] = []
        for page in range(max_pages):
            page_params = {**params, "pagina": page + 1} if page else params
            resp = await self._client.call_endpoint(endpoint_key, params=page_params)
            if not resp.success:
                break
            chunk = self._rows(resp.data)
            if not chunk:
                break
            all_rows.extend(chunk)
            if isinstance(resp.data, dict) and resp.data.get("ultimaPagina", True):
                break
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return all_rows, ms

    async def _fetch_merged(
        self,
        filters: FinancialOverviewFilters,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float]:
        params = {"dataInicial": filters.data_inicial, "dataFinal": filters.data_final}
        t0 = time.perf_counter()

        rede_resp, caixa_resp, ap_resp = await asyncio.gather(
            self._client.call_endpoint("caixa_rede", params=params),
            self._client.call_endpoint("caixa", params=params),
            self._client.call_endpoint("caixa_apresentado", params=params),
        )

        caixa_rows = self._rows(rede_resp.data if rede_resp.success else [])
        if not caixa_rows and caixa_resp.success:
            caixa_rows = self._rows(caixa_resp.data)

        ap_rows = self._rows(ap_resp.data if ap_resp.success else [])
        caixa_rows = [r for r in caixa_rows if self._matches_empresa(r, filters)]
        ap_rows = [r for r in ap_rows if self._matches_empresa(r, filters)]

        ap_map = {(r.get("empresaCodigo"), r.get("caixaCodigo")): r for r in ap_rows}
        merged: list[dict[str, Any]] = []
        for row in caixa_rows:
            key = (row.get("empresaCodigo"), row.get("caixaCodigo"))
            ap = ap_map.get(key, {})
            merged.append({**row, **{f"ap_{k}": v for k, v in ap.items()}})

        ms = round((time.perf_counter() - t0) * 1000, 1)
        return merged, ap_rows, ms

    @staticmethod
    def _shift_date(row: dict[str, Any]) -> str:
        return str(row.get("dataMovimento") or row.get("fechamento") or row.get("abertura") or "")[:10]

    def _consecutive_breaks(self, rows: list[dict[str, Any]]) -> dict[Any, int]:
        by_op: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            by_op[row.get("funcionarioCodigo")].append(row)

        max_consecutive: dict[Any, int] = defaultdict(int)
        for op, op_rows in by_op.items():
            op_rows.sort(key=lambda r: self._shift_date(r))
            streak = 0
            best = 0
            for row in op_rows:
                if _dec(row.get("diferenca")) != 0:
                    streak += 1
                    best = max(best, streak)
                else:
                    streak = 0
            max_consecutive[op] = best
        return max_consecutive

    def _pdv_breaks_30d(
        self,
        merged_30d: list[dict[str, Any]],
    ) -> dict[Any, int]:
        counts: Counter[Any] = Counter()
        for row in merged_30d:
            if _dec(row.get("diferenca")) != 0:
                counts[row.get("pdvCodigo")] += 1
        return dict(counts)

    def _build_alerts(
        self,
        merged: list[dict[str, Any]],
        consecutive: dict[Any, int],
        pdv_30d: dict[Any, int],
    ) -> dict[str, Any]:
        alerts: list[dict[str, Any]] = []
        counts = Counter({"INFO": 0, "ATENCAO": 0, "ALTO": 0, "CRITICO": 0, "OK": 0})

        for row in merged:
            diff = _dec(row.get("diferenca"))
            abs_diff = abs(diff)
            op = row.get("funcionarioCodigo")
            pdv = row.get("pdvCodigo")
            level = _alert_level(abs_diff, consecutive.get(op, 0), pdv_30d.get(pdv, 0))
            counts[level] += 1
            if level == "OK":
                continue
            alerts.append(
                {
                    "nivel": level,
                    "caixaCodigo": row.get("caixaCodigo"),
                    "empresaCodigo": row.get("empresaCodigo"),
                    "funcionarioCodigo": op,
                    "pdvCodigo": pdv,
                    "turno": row.get("turno"),
                    "turnoCodigo": row.get("turnoCodigo"),
                    "dataMovimento": self._shift_date(row),
                    "diferenca": _round2(diff),
                    "diferencaAbsoluta": _round2(abs_diff),
                    "consecutivasOperador": consecutive.get(op, 0),
                    "quebrasPdv30d": pdv_30d.get(pdv, 0),
                    "motivo": self._alert_reason(level, abs_diff, consecutive.get(op, 0), pdv_30d.get(pdv, 0)),
                }
            )

        severity_order = {"CRITICO": 0, "ALTO": 1, "ATENCAO": 2, "INFO": 3}
        alerts.sort(key=lambda a: (severity_order.get(a["nivel"], 9), -a["diferencaAbsoluta"]))

        active = [a for a in alerts if a["nivel"] in {"INFO", "ATENCAO", "ALTO", "CRITICO"}]
        return {
            "total": len(active),
            "porNivel": dict(counts),
            "ativos": active,
            "criticos": [a for a in active if a["nivel"] == "CRITICO"],
            "vermelhas": {
                "turnos": self._critical_turns(active),
                "pdvs": self._critical_entities(active, "pdvCodigo", CRITICAL_PDVS),
                "operadores": self._critical_entities(active, "funcionarioCodigo", CRITICAL_OPERATORS),
            },
        }

    @staticmethod
    def _alert_reason(level: str, abs_diff: float, consecutive: int, pdv_30d: int) -> str:
        parts: list[str] = []
        if abs_diff >= ALERT_CRITICO:
            parts.append(f"diferenca >= R$ {ALERT_CRITICO:.2f}")
        if consecutive >= 3:
            parts.append(f"{consecutive} quebras consecutivas operador")
        if pdv_30d >= 5:
            parts.append(f"{pdv_30d} quebras PDV em 30d")
        if not parts:
            if level == "ALTO":
                parts.append(f"diferenca >= R$ {ALERT_ALTO:.2f}")
            elif level == "ATENCAO":
                parts.append(f"diferenca >= R$ {ALERT_ATENCAO:.2f}")
            else:
                parts.append(f"diferenca >= R$ {ALERT_INFO_MIN:.2f}")
        return "; ".join(parts)

    @staticmethod
    def _critical_turns(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_turn: dict[str, list[dict]] = defaultdict(list)
        for alert in alerts:
            if alert["nivel"] in {"ALTO", "CRITICO"}:
                key = str(alert.get("turno") or alert.get("turnoCodigo") or "?")
                by_turn[key].append(alert)
        items = [
            {"turno": turn, "alertas": len(rows), "diferencaAbsoluta": _round2(sum(r["diferencaAbsoluta"] for r in rows))}
            for turn, rows in by_turn.items()
        ]
        items.sort(key=lambda x: x["diferencaAbsoluta"], reverse=True)
        return items

    @staticmethod
    def _critical_entities(
        alerts: list[dict[str, Any]],
        field: str,
        focus: set[int],
    ) -> list[dict[str, Any]]:
        by_id: dict[Any, list[dict]] = defaultdict(list)
        for alert in alerts:
            if alert["nivel"] in {"ALTO", "CRITICO"}:
                by_id[alert.get(field)].append(alert)
        items = []
        for entity_id, rows in by_id.items():
            try:
                code = int(entity_id)
            except (TypeError, ValueError):
                code = entity_id
            items.append(
                {
                    field: code,
                    "alertas": len(rows),
                    "diferencaAbsoluta": _round2(sum(r["diferencaAbsoluta"] for r in rows)),
                    "monitoramentoPrioritario": code in focus,
                }
            )
        items.sort(key=lambda x: (not x.get("monitoramentoPrioritario", False), -x["diferencaAbsoluta"]))
        return items

    def _dimension_score(self, rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 100.0
        diffs = [_dec(r.get("diferenca")) for r in rows]
        abs_sum = sum(abs(d) for d in diffs)
        recurrence = sum(1 for d in diffs if d != 0) / len(rows)
        severity = min(abs_sum / 5000.0, 1.0)
        return max(0.0, min(100.0, 100.0 * (1.0 - 0.55 * recurrence - 0.45 * severity)))

    def _pdv_dimension_score(self, rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 100.0
        diffs = [_dec(r.get("diferenca")) for r in rows]
        if len(diffs) > 1:
            stdev = statistics.pstdev(diffs)
        else:
            stdev = abs(diffs[0]) if diffs else 0.0
        vol_penalty = min(stdev / 200.0, 1.0)
        accum_penalty = min(abs(sum(diffs)) / 5000.0, 1.0)
        return max(0.0, min(100.0, 100.0 * (1.0 - 0.5 * vol_penalty - 0.5 * accum_penalty)))

    def _history_score(self, merged: list[dict[str, Any]], merged_90d: list[dict[str, Any]]) -> float:
        loss_7 = sum(abs(_dec(r.get("diferenca"))) for r in merged)
        loss_90 = sum(abs(_dec(r.get("diferenca"))) for r in merged_90d)
        days_7 = max(len({self._shift_date(r) for r in merged}), 1)
        days_90 = max(len({self._shift_date(r) for r in merged_90d}), 1)
        daily_7 = loss_7 / days_7
        daily_90 = loss_90 / days_90 if loss_90 else daily_7
        if daily_90 <= 0:
            return 100.0
        ratio = daily_7 / daily_90
        return max(0.0, min(100.0, 100.0 * (1.0 - min(ratio / 2.0, 1.0))))

    def _build_risk_score(
        self,
        merged: list[dict[str, Any]],
        merged_90d: list[dict[str, Any]],
    ) -> dict[str, Any]:
        by_op: dict[Any, list[dict]] = defaultdict(list)
        by_pdv: dict[Any, list[dict]] = defaultdict(list)
        by_turn: dict[Any, list[dict]] = defaultdict(list)
        for row in merged:
            by_op[row.get("funcionarioCodigo")].append(row)
            by_pdv[row.get("pdvCodigo")].append(row)
            by_turn[row.get("turnoCodigo") or row.get("turno")].append(row)

        op_scores = [self._dimension_score(rows) for rows in by_op.values()]
        pdv_scores = [self._pdv_dimension_score(rows) for rows in by_pdv.values()]
        turn_scores = [self._dimension_score(rows) for rows in by_turn.values()]

        avg_op = statistics.mean(op_scores) if op_scores else 100.0
        avg_pdv = statistics.mean(pdv_scores) if pdv_scores else 100.0
        avg_turn = statistics.mean(turn_scores) if turn_scores else 100.0
        hist = self._history_score(merged, merged_90d)

        consolidated = (
            W_OPERATOR * avg_op + W_PDV * avg_pdv + W_TURN * avg_turn + W_HIST * hist
        )
        consolidated = _round2(consolidated)

        entity_scores = []
        for op, rows in by_op.items():
            score = (
                W_OPERATOR * self._dimension_score(rows)
                + W_PDV * statistics.mean([self._pdv_dimension_score(by_pdv[p]) for p in {r.get("pdvCodigo") for r in rows}])
                + W_TURN * statistics.mean([self._dimension_score(by_turn[t]) for t in {r.get("turnoCodigo") or r.get("turno") for r in rows}])
                + W_HIST * hist
            )
            entity_scores.append(
                {
                    "funcionarioCodigo": op,
                    "score": _round2(score),
                    "band": _risk_band(score),
                    "critico": int(op) in CRITICAL_OPERATORS if op is not None else False,
                }
            )

        pdv_entity_scores = []
        for pdv, rows in by_pdv.items():
            score = W_PDV * self._pdv_dimension_score(rows) + (1 - W_PDV) * consolidated
            pdv_entity_scores.append(
                {
                    "pdvCodigo": pdv,
                    "score": _round2(score),
                    "band": _risk_band(score),
                    "critico": int(pdv) in CRITICAL_PDVS if pdv is not None else False,
                }
            )

        crit_ops = [e for e in entity_scores if e["band"] == "Critico" or e["critico"]]
        crit_pdvs = [e for e in pdv_entity_scores if e["band"] == "Critico" or e["critico"]]

        return {
            "consolidado": consolidated,
            "band": _risk_band(consolidated),
            "pesos": {
                "operador": W_OPERATOR,
                "pdv": W_PDV,
                "turno": W_TURN,
                "historicoFilial": W_HIST,
            },
            "subScores": {
                "operador": _round2(avg_op),
                "pdv": _round2(avg_pdv),
                "turno": _round2(avg_turn),
                "historicoFilial": _round2(hist),
            },
            "operadoresCriticos": len(crit_ops),
            "pdvsCriticos": len(crit_pdvs),
            "operadores": sorted(entity_scores, key=lambda x: x["score"])[:20],
            "pdvs": sorted(pdv_entity_scores, key=lambda x: x["score"])[:20],
        }

    def _operator_analytics(self, merged: list[dict[str, Any]], risk: dict[str, Any]) -> dict[str, Any]:
        risk_map = {r["funcionarioCodigo"]: r for r in risk.get("operadores", [])}
        by_op: dict[Any, list[dict]] = defaultdict(list)
        for row in merged:
            by_op[row.get("funcionarioCodigo")].append(row)

        items: list[dict[str, Any]] = []
        for op, rows in by_op.items():
            diffs = [_dec(r.get("diferenca")) for r in rows]
            vol = sum(_dec(r.get("apurado")) for r in rows)
            rec = sum(1 for d in diffs if d != 0)
            items.append(
                {
                    "funcionarioCodigo": op,
                    "fechamentos": len(rows),
                    "volumeApurado": _round2(vol),
                    "diferencaAcumulada": _round2(sum(diffs)),
                    "diferencaMedia": _round2(statistics.mean(diffs)) if diffs else 0.0,
                    "indiceRecorrencia": _round2(rec / len(rows)) if rows else 0.0,
                    "cashRiskScore": risk_map.get(op, {}).get("score"),
                    "band": risk_map.get(op, {}).get("band"),
                    "monitoramentoPrioritario": int(op) in CRITICAL_OPERATORS if op is not None else False,
                }
            )

        items.sort(key=lambda x: x["diferencaAcumulada"])
        best = sorted(items, key=lambda x: (-x.get("cashRiskScore") or 0, -x["fechamentos"]))[:20]
        worst = sorted(items, key=lambda x: (x.get("cashRiskScore") or 0, x["diferencaAcumulada"]))[:20]

        return {
            "totalOperadores": len(items),
            "rankingMelhores": best,
            "rankingPiores": worst,
            "todos": items,
        }

    def _pdv_analytics(self, merged: list[dict[str, Any]], risk: dict[str, Any]) -> dict[str, Any]:
        risk_map = {r["pdvCodigo"]: r for r in risk.get("pdvs", [])}
        by_pdv: dict[Any, list[dict]] = defaultdict(list)
        for row in merged:
            by_pdv[row.get("pdvCodigo")].append(row)

        global_mean = statistics.mean([abs(_dec(r.get("diferenca"))) for r in merged]) if merged else 0.0

        items: list[dict[str, Any]] = []
        for pdv, rows in by_pdv.items():
            diffs = [_dec(r.get("diferenca")) for r in rows]
            stdev = statistics.pstdev(diffs) if len(diffs) > 1 else (abs(diffs[0]) if diffs else 0.0)
            ops = Counter(r.get("funcionarioCodigo") for r in rows)
            turns = Counter(r.get("turno") or r.get("turnoCodigo") for r in rows)
            item = {
                "pdvCodigo": pdv,
                "fechamentos": len(rows),
                "diferencaAcumulada": _round2(sum(diffs)),
                "desvioPadrao": _round2(stdev),
                "diferencaMedia": _round2(statistics.mean(diffs)) if diffs else 0.0,
                "operadores": [{"funcionarioCodigo": k, "fechamentos": v} for k, v in ops.most_common()],
                "turnos": [{"turno": k, "fechamentos": v} for k, v in turns.most_common()],
                "cashRiskScore": risk_map.get(pdv, {}).get("score"),
                "band": risk_map.get(pdv, {}).get("band"),
                "vsMediaRede": _round2((statistics.mean([abs(d) for d in diffs]) if diffs else 0.0) - global_mean),
                "monitoramentoPrioritario": int(pdv) in CRITICAL_PDVS if pdv is not None else False,
            }
            items.append(item)

        items.sort(key=lambda x: x["diferencaAcumulada"])
        focus = {
            "54193": next((x for x in items if x["pdvCodigo"] == 54193), None),
            "15880": next((x for x in items if x["pdvCodigo"] == 15880), None),
            "mediaGlobalQuebra": _round2(global_mean),
        }
        return {"totalPdvs": len(items), "ranking": items, "alvosCriticos": focus}

    def _turn_analytics(self, merged: list[dict[str, Any]]) -> dict[str, Any]:
        by_turn: dict[Any, list[dict]] = defaultdict(list)
        for row in merged:
            key = (row.get("turnoCodigo"), row.get("turno"))
            by_turn[key].append(row)

        items: list[dict[str, Any]] = []
        total_vol = sum(_dec(r.get("apurado")) for r in merged)
        for (tc, tn), rows in by_turn.items():
            diffs = [_dec(r.get("diferenca")) for r in rows]
            vol = sum(_dec(r.get("apurado")) for r in rows)
            breaks = sum(1 for d in diffs if d != 0)
            items.append(
                {
                    "turnoCodigo": tc,
                    "turno": tn,
                    "fechamentos": len(rows),
                    "volumeFinanceiro": _round2(vol),
                    "participacaoVolumePct": _round2(100 * vol / total_vol) if total_vol else 0.0,
                    "desvioAcumulado": _round2(sum(diffs)),
                    "incidenciaQuebraPct": _round2(100 * breaks / len(rows)) if rows else 0.0,
                    "matrizRisco": _risk_band(self._dimension_score(rows)),
                }
            )

        items.sort(key=lambda x: abs(x["desvioAcumulado"]), reverse=True)
        return {"totalTurnos": len(items), "porTurno": items}

    @staticmethod
    def _heatmap(merged: list[dict[str, Any]]) -> dict[str, Any]:
        matrix: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for row in merged:
            turn = str(row.get("turno") or row.get("turnoCodigo") or "?")
            pdv = str(row.get("pdvCodigo") or "?")
            matrix[turn][pdv] += abs(_dec(row.get("diferenca")))
            counts[turn][pdv] += 1

        turns = sorted(matrix.keys())
        pdvs = sorted({pdv for row in matrix.values() for pdv in row.keys()})
        cells = []
        for turn in turns:
            for pdv in pdvs:
                if pdv in matrix[turn]:
                    cells.append(
                        {
                            "turno": turn,
                            "pdvCodigo": pdv,
                            "impactoAbsoluto": _round2(matrix[turn][pdv]),
                            "fechamentos": counts[turn][pdv],
                        }
                    )
        return {"turnos": turns, "pdvs": pdvs, "cells": cells}

    @staticmethod
    def _recovery_metrics(merged: list[dict[str, Any]], merged_90d: list[dict[str, Any]]) -> dict[str, Any]:
        abs_7 = sum(abs(_dec(r.get("diferenca"))) for r in merged)
        abs_90 = sum(abs(_dec(r.get("diferenca"))) for r in merged_90d)
        days_90 = max(len({str(r.get("dataMovimento") or "")[:10] for r in merged_90d}), 1)
        daily = abs_90 / days_90
        annual = _round2(daily * 365)
        recoverable = _round2(abs_90 * 0.30)
        baseline_stanched = _round2(max(0.0, abs_7 * 0.15))
        return {
            "diferencaTotalRede": _round2(sum(_dec(r.get("diferenca")) for r in merged)),
            "impactoAbsoluto7d": _round2(abs_7),
            "impactoAbsoluto90d": _round2(abs_90),
            "perdaObservada90d": _round2(abs_90),
            "projecaoAnual": annual,
            "potencialRecuperavel30pct": recoverable,
            "estancamentoInicial7d": baseline_stanched,
        }

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        filters = build_finance_center_filters(data_inicial, data_final, empresa_codigo)
        t0 = time.perf_counter()

        end_dt = datetime.fromisoformat(filters.data_final)
        start_30 = (end_dt - timedelta(days=29)).isoformat()[:10]
        start_90 = (end_dt - timedelta(days=89)).isoformat()[:10]

        merged_task = self._fetch_merged(filters)
        filters_30 = build_finance_center_filters(start_30, filters.data_final, empresa_codigo)
        filters_90 = build_finance_center_filters(start_90, filters.data_final, empresa_codigo)
        merged_30_task = self._fetch_merged(filters_30)
        merged_90_task = self._fetch_merged(filters_90)

        (merged, _ap, fetch_ms), (merged_30, _, _), (merged_90, _, _) = await asyncio.gather(
            merged_task, merged_30_task, merged_90_task
        )

        consecutive = self._consecutive_breaks(merged)
        pdv_30d = self._pdv_breaks_30d(merged_30)
        alerts = self._build_alerts(merged, consecutive, pdv_30d)
        risk = self._build_risk_score(merged, merged_90)
        operators = self._operator_analytics(merged, risk)
        pdvs = self._pdv_analytics(merged, risk)
        turns = self._turn_analytics(merged)
        heatmap = self._heatmap(merged)
        recovery = self._recovery_metrics(merged, merged_90)

        total_ms = round((time.perf_counter() - t0) * 1000, 1)

        payload = {
            "periodo": {"dataInicial": filters.data_inicial, "dataFinal": filters.data_final},
            "summary": {
                **recovery,
                "fechamentos": len(merged),
                "cashRiskScore": risk["consolidado"],
                "cashRiskBand": risk["band"],
                "alertasAtivos": alerts["total"],
                "operadoresCriticos": risk["operadoresCriticos"],
                "pdvsCriticos": risk["pdvsCriticos"],
            },
            "alerts": alerts,
            "riskScore": risk,
            "operators": operators,
            "pdvs": pdvs,
            "turns": turns,
            "heatmap": heatmap,
            "performanceMs": {"fetch": fetch_ms, "total": total_ms},
            "source": "CAIXA_REDE+CAIXA+CAIXA_APRESENTADO",
        }
        return WebPostoResponse.ok(payload)
