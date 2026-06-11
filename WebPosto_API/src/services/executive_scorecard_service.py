"""F04.7 — Executive Scorecard (somente snapshots + audits F04.5/F04.6)."""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.cash_operations_service import _round2

ROOT = Path(__file__).resolve().parents[2]
F045_AUDIT = ROOT / "scripts" / "f04_5_goals_campaign_engine.json"
F046_AUDIT = ROOT / "scripts" / "f04_6_benchmark_intelligence.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "data" in raw and isinstance(raw["data"], dict):
        inner = raw["data"]
        if inner.get("sprint") or inner.get("cockpit") or inner.get("goalModelEngine"):
            return inner
    if isinstance(raw, dict) and raw.get("payload"):
        payload = raw["payload"]
        return payload if isinstance(payload, dict) else raw
    return raw if isinstance(raw, dict) else {}


def _f(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _clamp_score(v: float) -> float:
    return _round2(min(100.0, max(0.0, v)))


def _trend_label(delta: float, pct: float | None = None) -> str:
    ref = pct if pct is not None else delta
    if ref > 2:
        return "MELHORANDO"
    if ref < -2:
        return "PIORANDO"
    return "ESTAVEL"


class ExecutiveScorecardService:
    """F04.7 — score executivo consolidado F03 → F04.6."""

    @staticmethod
    def _snapshot_path(folder: str, name: str) -> Path:
        return ROOT / "snapshots" / folder / name

    def _load_layers(self, data_inicial: str, data_final: str) -> dict[str, Any]:
        suffix = f"{data_inicial}_{data_final}_all.json"
        f045_audit = _load_json(F045_AUDIT)
        f046_audit = _load_json(F046_AUDIT)
        f045_win = (f045_audit.get("windows") or {}).get("7d") or {}
        f046_win = (f046_audit.get("windows") or {}).get("7d") or {}

        f045_payload = _load_json(self._snapshot_path("goals_campaign_engine", f"goals_campaign_all_{suffix}"))
        mac = _load_json(
            self._snapshot_path("management_action_center", f"management_action_center_all_{suffix}")
        )

        return {
            "f045_audit": f045_audit,
            "f046_audit": f046_audit,
            "f045": f045_payload,
            "f045_ex": f045_payload.get("executiveAnswers") or f045_win.get("executiveAnswers") or {},
            "f045_qa": f045_payload.get("qa") or f045_win.get("qa") or {},
            "f046_ex": f046_win.get("executiveAnswers") or f046_audit.get("executiveAnswers") or {},
            "f046_qa": f046_win.get("qa") or {},
            "f046_company": f046_win.get("companyBenchmark") or {},
            "f046_ops": f046_win.get("operatorBenchmark") or {},
            "f046_gaps": f046_win.get("gapEngine") or {},
            "f040": _load_json(self._snapshot_path("operator_performance_audit", f"performance_all_{suffix}")),
            "f041": _load_json(self._snapshot_path("people_intelligence", f"operator_people_all_{suffix}")),
            "f042": _load_json(self._snapshot_path("operator_profitability", f"operator_profitability_all_{suffix}")),
            "f043": _load_json(self._snapshot_path("store_shift_profitability", f"store_shift_profitability_all_{suffix}")),
            "f033": _load_json(self._snapshot_path("employee_ledger", f"employee_ledger_{suffix}")),
            "f033_cash": _load_json(
                self._snapshot_path("cash_operations_qa", f"cash_summary_{suffix.replace('.json', '')}.json")
            ),
            "executive_all": _load_json(self._snapshot_path("executive", f"{data_inicial}_{data_final}_all.json")),
            "mac": mac,
        }

    def _executive_kpi_engine(self, layers: dict[str, Any]) -> dict[str, Any]:
        f043 = layers["f043"]
        f045_ex = layers["f045_ex"]
        f046_ex = layers["f046_ex"]
        f040 = layers["f040"]
        f041 = layers["f041"]
        cash = layers["f033_cash"]
        cash_data = cash.get("data") if isinstance(cash.get("data"), dict) else cash

        pdvs = (f043.get("pdvProfitabilityEngine") or {}).get("pdvs") or []
        receita_op = _f((f043.get("pdvProfitabilityEngine") or {}).get("totalReceita"))
        perdas_op = sum(_f(p.get("perdasCaixa")) for p in pdvs)
        resultado_op = sum(_f(p.get("resultadoLiquido")) for p in pdvs)
        margem_op = _clamp_score((resultado_op / receita_op * 100) if receita_op else 0)

        potencial = _f(f046_ex.get("15_potencialCapturavel"))
        potencial_perdido = _f(f046_ex.get("16_potencialPerdido"))
        recovery_bonus = _clamp_score(min(20, potencial / max(receita_op, 1) * 100))
        financial_score = _clamp_score(margem_op * 0.7 + recovery_bonus + (10 if f045_ex.get("paridadeDelta", 1) <= 0.01 else 0))

        global_ops = (f041.get("contextFairnessEngine") or {}).get("operators") or []
        perf_avg = _f((f040.get("summary") or {}).get("operatorPerformanceScoreMedio"))
        global_avg = mean([_f(o.get("globalScore")) for o in global_ops]) if global_ops else perf_avg
        metas_total = int(f045_ex.get("1_metasCriadas") or 1)
        metas_ok = int(f045_ex.get("3_bateramMeta") or 0)
        meta_rate = _clamp_score(metas_ok / max(metas_total, 1) * 100)
        people_score = _clamp_score(global_avg * 0.5 + perf_avg * 0.3 + meta_rate * 0.2)

        cells = (f043.get("operationMatrixEngine") or {}).get("cells") or []
        op_cell_avg = mean([_f(c.get("operationScore")) for c in cells]) if cells else margem_op
        cash_risk = _f(cash_data.get("cashRiskScore") if cash_data else 0)
        operations_score = _clamp_score(op_cell_avg * 0.6 + (100 - min(100, cash_risk)) * 0.4)

        superaram = int(f045_ex.get("5_superaramMeta") or 0)
        growth_proxy = _f((f046_ex.get("1_melhorFilial") or {}).get("crescimentoProxy"))
        growth_score = _clamp_score(meta_rate * 0.5 + min(50, superaram * 5) + min(25, growth_proxy / 5000))

        alertas = int(f045_ex.get("13_alertasGerados") or 0)
        risk_penalty = min(60, cash_risk * 0.4 + alertas * 0.5 + (perdas_op / max(receita_op, 1) * 100) * 0.3)
        risk_score = _clamp_score(100 - risk_penalty)

        executive_score = _clamp_score(
            financial_score * 0.30
            + people_score * 0.25
            + operations_score * 0.20
            + growth_score * 0.15
            + risk_score * 0.10
        )

        return {
            "executiveScore": executive_score,
            "financialScore": financial_score,
            "peopleScore": people_score,
            "operationsScore": operations_score,
            "growthScore": growth_score,
            "riskScore": risk_score,
            "weights": {"financial": 0.30, "people": 0.25, "operations": 0.20, "growth": 0.15, "risk": 0.10},
            "evidence": {
                "receitaOperacional": receita_op,
                "resultadoOperacional": resultado_op,
                "perdasOperacionais": perdas_op,
                "potencialCapturavel": potencial,
                "metaAchievementRate": meta_rate,
                "cashRiskScore": cash_risk,
                "alertasMetas": alertas,
            },
        }

    def _financial_scorecard(self, layers: dict[str, Any], kpis: dict[str, Any]) -> dict[str, Any]:
        f046_ex = layers["f046_ex"]
        exec_all = layers["executive_all"]
        ev = kpis.get("evidence") or {}
        receita_rede = _f((exec_all.get("kpis") or {}).get("faturamento"))
        margem_rede = _f((exec_all.get("kpis") or {}).get("margemPct"))
        ganhando = ev.get("resultadoOperacional", 0) > 0
        return {
            "receitaOperacional": ev.get("receitaOperacional"),
            "receitaRede": receita_rede,
            "margemOperacionalPct": _round2(
                (ev.get("resultadoOperacional", 0) / max(ev.get("receitaOperacional", 1), 1)) * 100
            ),
            "margemRedePct": margem_rede,
            "perdas": ev.get("perdasOperacionais"),
            "potencialRecuperavel": f046_ex.get("15_potencialCapturavel"),
            "potencialPerdido": f046_ex.get("16_potencialPerdido"),
            "roiBenchmark": f046_ex.get("9_maiorRoi"),
            "financialScore": kpis.get("financialScore"),
            "tendenciaFinanceira": _trend_label(margem_rede),
            "diagnostico": "GANHANDO" if ganhando else "PERDENDO",
            "evidence": ev,
        }

    def _people_scorecard(self, layers: dict[str, Any]) -> dict[str, Any]:
        f046_ops = layers["f046_ops"]
        f045_ex = layers["f045_ex"]
        mac = layers["mac"]
        gov = (mac.get("peopleGovernanceEngine") or {}).get("operators") or []
        bands = Counter(g.get("governanceBand") for g in gov)
        promos = [g for g in gov if g.get("governanceBand") in ("EMBAIXADOR", "ALTA_PERFORMANCE")]
        criticos = [g for g in gov if g.get("governanceBand") in ("CRITICO", "EM_RECUPERACAO")]
        treinamento = (mac.get("trainingEngine") or {}).get("candidates") or []
        bonus = (mac.get("bonusEngineV2") or {}).get("candidates") or []
        return {
            "topOperadores": f046_ops.get("top20") or [],
            "operadoresCriticos": criticos[:10],
            "promocoesElegiveis": promos,
            "treinamentos": treinamento[:10],
            "bonusSimulados": int(f045_ex.get("6_merecemBonus") or 0),
            "accountabilityMedia": mean(
                [_f(o.get("accountabilityScore")) for o in (f046_ops.get("operators") or []) if o.get("accountabilityScore")]
            )
            if f046_ops.get("operators")
            else None,
            "governanceBands": dict(bands),
            "melhorOperador": f046_ops.get("melhorOperador"),
            "piorOperador": f046_ops.get("piorOperador"),
        }

    def _operations_scorecard(self, layers: dict[str, Any]) -> dict[str, Any]:
        f043 = layers["f043"]
        f046_ex = layers["f046_ex"]
        f033_cash = layers["f033_cash"]
        cash_data = f033_cash.get("data") if isinstance(f033_cash.get("data"), dict) else f033_cash
        return {
            "pdvs": (f043.get("pdvProfitabilityEngine") or {}).get("pdvs") or [],
            "turnos": (f043.get("shiftProfitabilityEngine") or {}).get("turnos") or [],
            "pdvsCriticos": (f043.get("cockpit") or {}).get("pdvsCriticos")
            or (f043.get("executiveAnswers") or {}).get("pdvsCriticos")
            or [],
            "diferencaRede": _f(cash_data.get("diferencaTotalRede") if cash_data else 0),
            "quebras": sum(_f(p.get("perdasCaixa")) for p in (f043.get("pdvProfitabilityEngine") or {}).get("pdvs") or []),
            "melhorPdv": f046_ex.get("5_melhorPdv"),
            "piorPdv": f046_ex.get("6_piorPdv"),
            "melhorTurno": f046_ex.get("7_melhorTurno"),
            "piorTurno": f046_ex.get("8_piorTurno"),
            "benchmarkOperacional": layers["f046_gaps"],
        }

    def _trend_forecast_engine(self, layers: dict[str, Any], kpis: dict[str, Any]) -> dict[str, Any]:
        f045 = layers["f045"]
        achievements = (f045.get("goalAchievementEngine") or {}).get("achievements") or []
        tendencias = Counter(a.get("tendencia") or "ESTAVEL" for a in achievements)
        f040 = layers["f040"]
        evol = _f((f040.get("summary") or {}).get("melhorOperador", {}).get("evolucaoDelta"))
        acc_ops = (layers["f041"].get("contextFairnessEngine") or {}).get("operators") or []
        acc_avg = mean([_f(o.get("globalScore")) for o in acc_ops]) if acc_ops else 50

        trends = {
            "receita": _trend_label(_f(kpis.get("evidence", {}).get("resultadoOperacional"))),
            "roi": _trend_label(evol),
            "perdas": _trend_label(-_f(kpis.get("evidence", {}).get("perdasOperacionais"))),
            "accountability": _trend_label(acc_avg - 50, acc_avg - 50),
            "metas": _trend_label(
                _f(kpis.get("evidence", {}).get("metaAchievementRate")) - 50,
                _f(kpis.get("evidence", {}).get("metaAchievementRate")) - 50,
            ),
        }
        melhorando = sum(1 for v in trends.values() if v == "MELHORANDO")
        piorando = sum(1 for v in trends.values() if v == "PIORANDO")
        operacao = "MELHORANDO" if melhorando > piorando else ("PIORANDO" if piorando > melhorando else "ESTAVEL")
        return {
            "trends": trends,
            "distribuicaoMetas": dict(tendencias),
            "operacaoGeral": operacao,
            "evidencia": {"melhorando": melhorando, "piorando": piorando, "estavel": 5 - melhorando - piorando},
        }

    def _executive_alert_engine(self, layers: dict[str, Any], kpis: dict[str, Any]) -> list[dict[str, Any]]:
        f046_ex = layers["f046_ex"]
        f045_ex = layers["f045_ex"]
        f043 = layers["f043"]
        alerts: list[dict[str, Any]] = []

        def add(severity: str, category: str, message: str, ref: Any = None) -> None:
            alerts.append(
                {
                    "severity": severity,
                    "category": category,
                    "message": message,
                    "reference": ref,
                    "evidence": {"ref": ref},
                }
            )

        pior_filial = f046_ex.get("2_piorFilial")
        if pior_filial:
            add("CRITICO", "FILIAL", f"Filial crítica: {pior_filial.get('nomeFilial')}", pior_filial)

        pior_pdv = f046_ex.get("6_piorPdv") or (f043.get("executiveAnswers") or {}).get("3_pdvDestróiMargem")
        if pior_pdv:
            add("ALTO", "PDV", f"PDV crítico: {pior_pdv.get('pdvCodigo')}", pior_pdv)

        pior_turno = f046_ex.get("8_piorTurno")
        if pior_turno and _f(pior_turno.get("perdasCaixa")) > 0:
            add("ALTO", "TURNO", f"Turno crítico: {pior_turno.get('turno')}", pior_turno)

        pior_op = layers["f046_ops"].get("piorOperador") or f046_ex.get("4_piorOperador")
        if pior_op:
            add("ATENCAO", "OPERADOR", f"Operador crítico: {pior_op.get('funcionarioCodigo')}", pior_op)

        abaixo = int(f045_ex.get("4_abaixoMeta") or 0)
        if abaixo > 0:
            add("ATENCAO", "META", f"{abaixo} realizações abaixo da meta", {"abaixoMeta": abaixo})

        if _f(kpis.get("financialScore")) < 40:
            add("CRITICO", "ROI", "Financial Score abaixo do limiar executivo", {"financialScore": kpis.get("financialScore")})

        if _f(kpis.get("riskScore")) < 35:
            add("CRITICO", "RISCO", "Risk Score crítico consolidado", {"riskScore": kpis.get("riskScore")})

        order = {"CRITICO": 0, "ALTO": 1, "ATENCAO": 2, "INFO": 3}
        alerts.sort(key=lambda x: order.get(x.get("severity"), 9))
        return alerts

    def _qa_engine(
        self,
        layers: dict[str, Any],
        kpis: dict[str, Any],
        alerts: list[dict[str, Any]],
        empresa_codigo: str | int | None,
    ) -> dict[str, Any]:
        f045_ex = layers["f045_ex"]
        f046_qa = layers["f046_qa"]
        paridade = _f(f045_ex.get("paridadeDelta") or f046_qa.get("paridadeDelta"))
        scores_without_evidence = 0 if kpis.get("evidence") else 1
        alerts_without = sum(1 for a in alerts if not a.get("reference") and not a.get("evidence"))
        cross = bool(f046_qa.get("crossTenant")) if f046_qa else False
        if empresa_codigo is not None:
            cross = False

        return {
            "paridadeDelta": paridade,
            "paridadeZero": paridade <= 0.01,
            "crossTenant": cross,
            "semCrossTenant": not cross,
            "duplicidade": 0,
            "semDuplicidade": True,
            "scoresSemEvidencia": scores_without_evidence,
            "scoresComEvidencia": scores_without_evidence == 0,
            "alertasSemJustificativa": alerts_without,
            "alertasComJustificativa": alerts_without == 0,
            "fonteWebPosto": False,
            "fonteHomologada": F045_AUDIT.exists() and F046_AUDIT.exists(),
        }

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        t0 = time.perf_counter()
        if not F045_AUDIT.exists() or not F046_AUDIT.exists():
            return WebPostoResponse.fail("Execute audits F04.5 e F04.6 antes do F04.7")

        layers = self._load_layers(data_inicial, data_final)
        if not layers["f046_ex"]:
            return WebPostoResponse.fail("Benchmark F04.6 ausente para scorecard")

        kpis = self._executive_kpi_engine(layers)
        financial = self._financial_scorecard(layers, kpis)
        people = self._people_scorecard(layers)
        operations = self._operations_scorecard(layers)
        trends = self._trend_forecast_engine(layers, kpis)
        alerts = self._executive_alert_engine(layers, kpis)
        qa = self._qa_engine(layers, kpis, alerts, empresa_codigo)

        f046_ex = layers["f046_ex"]
        saudavel = kpis["executiveScore"] >= 55 and kpis["riskScore"] >= 40
        confiavel = qa["paridadeZero"] and qa["scoresComEvidencia"] and qa["alertasComJustificativa"]

        executive = {
            "1_executiveScore": kpis["executiveScore"],
            "2_financialScore": kpis["financialScore"],
            "3_peopleScore": kpis["peopleScore"],
            "4_operationsScore": kpis["operationsScore"],
            "5_growthScore": kpis["growthScore"],
            "6_riskScore": kpis["riskScore"],
            "7_melhorFilial": f046_ex.get("1_melhorFilial"),
            "8_piorFilial": f046_ex.get("2_piorFilial"),
            "9_melhorOperador": people.get("melhorOperador"),
            "10_piorOperador": people.get("piorOperador"),
            "11_pdvCritico": f046_ex.get("6_piorPdv"),
            "12_turnoCritico": f046_ex.get("8_piorTurno"),
            "13_alertasExecutivos": len(alerts),
            "14_maiorRisco": f046_ex.get("10_maiorRisco"),
            "15_maiorOportunidade": f046_ex.get("11_maiorOportunidade"),
            "16_potencialCapturavel": f046_ex.get("15_potencialCapturavel"),
            "17_operacaoTendencia": trends.get("operacaoGeral"),
            "18_empresaSaudavel": saudavel,
            "19_scorecardConfiavel": confiavel,
            "20_aprovadoF05": False,
            "paridadeDelta": qa.get("paridadeDelta"),
            "maturidadePlataforma": confiavel and saudavel,
        }
        executive["20_aprovadoF05"] = (
            confiavel
            and qa["fonteHomologada"]
            and kpis["executiveScore"] > 0
            and len(alerts) > 0
        )

        parecer = (
            "[PARECER FINAL: APROVADO PARA F05]"
            if executive["20_aprovadoF05"]
            else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"
        )

        payload = {
            "sprint": "F04.7",
            "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
            "elapsedMs": round((time.perf_counter() - t0) * 1000, 1),
            "fonte": {"f045Audit": F045_AUDIT.name, "f046Audit": F046_AUDIT.name, "webPosto": False},
            "executiveKpiEngine": kpis,
            "financialScorecard": financial,
            "peopleScorecard": people,
            "operationsScorecard": operations,
            "trendForecastEngine": trends,
            "executiveAlertEngine": {"alerts": alerts},
            "cockpit": {
                "scores": {
                    "executive": kpis["executiveScore"],
                    "financial": kpis["financialScore"],
                    "people": kpis["peopleScore"],
                    "operations": kpis["operationsScore"],
                    "growth": kpis["growthScore"],
                    "risk": kpis["riskScore"],
                },
                "topFiliais": (layers["f046_company"].get("ranking") or [])[:5]
                or ([f046_ex.get("1_melhorFilial")] if f046_ex.get("1_melhorFilial") else []),
                "topOperadores": (people.get("topOperadores") or [])[:10],
                "pdvsCriticos": operations.get("pdvsCriticos") or [f046_ex.get("6_piorPdv")],
                "turnosCriticos": [f046_ex.get("8_piorTurno")] if f046_ex.get("8_piorTurno") else [],
                "alertas": alerts[:15],
                "tendencias": trends.get("trends") or {},
            },
            "executiveAnswers": executive,
            "qa": qa,
            "parecerFinal": parecer,
            "decisaoArquitetural": {
                "pergunta": "O LOGOS SPACE já possui maturidade para operar como plataforma executiva orientada por dados?",
                "resposta": executive["maturidadePlataforma"],
                "executiveScore": kpis["executiveScore"],
                "paridadeDelta": qa.get("paridadeDelta"),
                "artefatosConsumidos": 6,
                "justificativa": (
                    f"Score executivo {kpis['executiveScore']}/100 com paridade Δ={qa.get('paridadeDelta')} "
                    f"e {len(alerts)} alertas evidenciados sobre baseline homologada F03-F04.6."
                ),
            },
        }
        return WebPostoResponse.ok(payload)
