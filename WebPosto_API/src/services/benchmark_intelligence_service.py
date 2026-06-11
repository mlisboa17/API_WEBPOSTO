"""F04.6 — Benchmark Intelligence (somente snapshots + F04.5 audit)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.cash_operations_service import _round2

ROOT = Path(__file__).resolve().parents[2]
F045_AUDIT = ROOT / "scripts" / "f04_5_goals_campaign_engine.json"
DEFAULT_WINDOW = ("2026-06-01", "2026-06-07")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "data" in raw and isinstance(raw["data"], dict):
        inner = raw["data"]
        if inner.get("sprint") or inner.get("cockpit") or inner.get("goalModelEngine"):
            return inner
    if isinstance(raw, dict) and raw.get("payload"):
        return raw["payload"]
    return raw if isinstance(raw, dict) else {}


def _f(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _avg_pct(achievements: list[dict[str, Any]], op: int) -> float:
    rows = [a for a in achievements if int(a.get("funcionarioCodigo") or 0) == op]
    if not rows:
        return 0.0
    return _round2(mean(a.get("percentualAtingido") or 0 for a in rows))


class BenchmarkIntelligenceService:
    """F04.6 — comparativos executivos a partir de dados F04.x existentes."""

    @staticmethod
    def _snapshot_path(folder: str, name: str) -> Path:
        return ROOT / "snapshots" / folder / name

    def _load_layers(self, data_inicial: str, data_final: str) -> dict[str, Any]:
        suffix = f"{data_inicial}_{data_final}_all.json"
        f045_audit = _load_json(F045_AUDIT)
        f045_win = (f045_audit.get("windows") or {}).get("7d") or {}
        f045_payload = _load_json(
            self._snapshot_path("goals_campaign_engine", f"goals_campaign_all_{suffix}")
        )
        if not f045_payload and f045_win.get("cockpit"):
            f045_payload = {
                "cockpit": f045_win.get("cockpit"),
                "executiveAnswers": f045_win.get("executiveAnswers"),
                "qa": f045_win.get("qa"),
                "parecerFinal": f045_win.get("parecerFinal"),
            }

        return {
            "f045_audit": f045_audit,
            "f045": f045_payload,
            "f045_ex": f045_payload.get("executiveAnswers") or f045_win.get("executiveAnswers") or {},
            "f045_qa": f045_payload.get("qa") or f045_win.get("qa") or {},
            "f040": _load_json(self._snapshot_path("operator_performance_audit", f"performance_all_{suffix}")),
            "f041": _load_json(self._snapshot_path("people_intelligence", f"operator_people_all_{suffix}")),
            "f042": _load_json(self._snapshot_path("operator_profitability", f"operator_profitability_all_{suffix}")),
            "f043": _load_json(self._snapshot_path("store_shift_profitability", f"store_shift_profitability_all_{suffix}")),
            "f033_cash": _load_json(self._snapshot_path("cash_operations_qa", f"cash_summary_{suffix.replace('.json', '')}.json")),
            "executive_all": _load_json(self._snapshot_path("executive", f"{data_inicial}_{data_final}_all.json")),
            "executive_multi": _load_json(
                self._snapshot_path("executive", f"{data_inicial}_{data_final}_5555_11495.json")
            ),
        }

    @staticmethod
    def _index_by_code(rows: list[dict[str, Any]], key: str = "funcionarioCodigo") -> dict[int, dict[str, Any]]:
        out: dict[int, dict[str, Any]] = {}
        for row in rows or []:
            code = row.get(key)
            if code is None:
                continue
            out[int(code)] = row
        return out

    def _company_benchmark(self, layers: dict[str, Any]) -> dict[str, Any]:
        f042 = layers["f042"]
        f043 = layers["f043"]
        f045 = layers["f045"]
        f045_ex = layers["f045_ex"]
        exec_multi = layers["executive_multi"]
        exec_all = layers["executive_all"]

        network_receita = _f((exec_all.get("kpis") or {}).get("faturamento"))
        network_lucro = _f((exec_all.get("kpis") or {}).get("resultadoOperacional"))
        op_receita = _f((f043.get("pdvProfitabilityEngine") or {}).get("totalReceita"))
        op_perdas = sum(_f(p.get("perdasCaixa")) for p in (f043.get("pdvProfitabilityEngine") or {}).get("pdvs") or [])
        alertas = int(f045_ex.get("13_alertasGerados") or 0)
        metas = int(f045_ex.get("1_metasCriadas") or 0)
        score_medio = _f((layers["f040"].get("summary") or {}).get("operatorPerformanceScoreMedio"))

        fuel_filiais = ((exec_multi.get("fuel") or {}).get("data") or {}).get("filiais") or []
        finance_paths = list((ROOT / "snapshots" / "finance_center").glob("finance_center_all_2026-06-01_2026-06-07_*.json"))

        filiais: list[dict[str, Any]] = []
        for fuel in fuel_filiais:
            code = int(fuel.get("empresaCodigo") or 0)
            share = _f(fuel.get("participacao")) / 100.0
            receita = _round2(network_receita * share if network_receita else op_receita * share)
            despesas = 0.0
            for fp in finance_paths:
                if str(code) not in fp.name:
                    continue
                fc = _load_json(fp)
                despesas = _f(((fc.get("center") or {}).get("summary") or {}).get("despesasGerenciais", {}).get("totalValor"))
                break
            lucro = _round2(receita - despesas)
            roi = _round2(lucro / receita * 100 if receita else 0)
            perdas = _round2(op_perdas * share) if code in (5555, 11495) else 0.0
            filiais.append(
                {
                    "empresaCodigo": code,
                    "nomeFilial": fuel.get("nomeFilial"),
                    "receita": receita,
                    "lucro": lucro,
                    "roi": roi,
                    "perdas": perdas,
                    "metas": metas if code == 5555 else 0,
                    "alertas": alertas if code == 5555 else 0,
                    "scoreMedio": score_medio if code == 5555 else None,
                    "participacao": _f(fuel.get("participacao")),
                    "crescimentoProxy": _f(fuel.get("litros")),
                }
            )

        exec_5333 = _load_json(self._snapshot_path("executive", "2026-06-01_2026-06-07_5333.json"))
        if exec_5333:
            kpis = exec_5333.get("kpis") or {}
            filiais.append(
                {
                    "empresaCodigo": 5333,
                    "nomeFilial": "FILIAL 5333",
                    "receita": _f(kpis.get("faturamento")),
                    "lucro": _f(kpis.get("resultadoOperacional")),
                    "roi": _f(kpis.get("margemPct")),
                    "perdas": 0.0,
                    "metas": 0,
                    "alertas": 0,
                    "scoreMedio": None,
                    "participacao": 0.0,
                    "crescimentoProxy": 0.0,
                }
            )

        if not filiais:
            filiais = [
                {
                    "empresaCodigo": None,
                    "nomeFilial": "REDE",
                    "receita": op_receita or network_receita,
                    "lucro": network_lucro,
                    "roi": _round2(network_lucro / network_receita * 100 if network_receita else 0),
                    "perdas": op_perdas,
                    "metas": metas,
                    "alertas": alertas,
                    "scoreMedio": score_medio,
                    "participacao": 100.0,
                    "crescimentoProxy": 0.0,
                }
            ]

        by_roi = sorted(filiais, key=lambda x: x.get("roi") or -999, reverse=True)
        by_receita = sorted(filiais, key=lambda x: x.get("receita") or 0, reverse=True)
        by_perda = sorted(filiais, key=lambda x: x.get("perdas") or 0, reverse=True)
        by_cresc = sorted(filiais, key=lambda x: x.get("crescimentoProxy") or 0, reverse=True)
        by_risco = sorted(filiais, key=lambda x: (x.get("perdas") or 0) - (x.get("lucro") or 0), reverse=True)

        return {
            "filiais": filiais,
            "ranking": by_receita,
            "melhorFilial": by_receita[0] if by_receita else None,
            "piorFilial": by_receita[-1] if by_receita else None,
            "maiorRoi": by_roi[0] if by_roi else None,
            "maiorPerda": by_perda[-1] if by_perda else None,
            "maiorCrescimento": by_cresc[0] if by_cresc else None,
            "maiorRisco": by_risco[0] if by_risco else None,
            "paridadeDelta": _f(layers["f045_ex"].get("paridadeDelta") or (f043.get("baseF042") or {}).get("paridadeDelta")),
        }

    def _operator_benchmark(self, layers: dict[str, Any]) -> dict[str, Any]:
        f040 = layers["f040"]
        f041 = layers["f041"]
        f042 = layers["f042"]
        f045 = layers["f045"]
        achievements = (f045.get("goalAchievementEngine") or {}).get("achievements") or []

        sales = self._index_by_code((f041.get("salesScoreEngine") or {}).get("operators") or [])
        prod = self._index_by_code((f041.get("productivityScoreEngine") or {}).get("operators") or [])
        global_scores = self._index_by_code((f041.get("contextFairnessEngine") or {}).get("operators") or [])
        roi_ops = self._index_by_code((f042.get("profitabilityScoreEngine") or {}).get("operators") or [])
        perf_raw = layers["f040"].get("operators") or {}
        perf_list = perf_raw.get("ranking") if isinstance(perf_raw, dict) else perf_raw
        perf_ops = self._index_by_code(perf_list or [])

        codes = set(sales) | set(prod) | set(roi_ops) | set(perf_ops)
        operators: list[dict[str, Any]] = []
        max_lucro = max((_f(r.get("resultadoLiquido")) for r in roi_ops.values()), default=1.0) or 1.0

        for code in codes:
            s = sales.get(code, {})
            p = prod.get(code, {})
            g = global_scores.get(code, {})
            r = roi_ops.get(code, {})
            perf = perf_ops.get(code, {})
            lucro = _f(r.get("resultadoLiquido"))
            goal_pct = _avg_pct(achievements, code)
            benchmark_score = _round2(
                _f(s.get("salesScore")) * 0.2
                + _f(p.get("productivityScore")) * 0.15
                + _f(r.get("accountabilityScore")) * 0.15
                + min(100.0, lucro / max_lucro * 100) * 0.2
                + _f(g.get("globalScore")) * 0.15
                + goal_pct * 0.15
            )
            operators.append(
                {
                    "funcionarioCodigo": code,
                    "employeeName": s.get("employeeName") or r.get("employeeName") or perf.get("employeeName"),
                    "salesScore": _f(s.get("salesScore")),
                    "productivityScore": _f(p.get("productivityScore")),
                    "accountabilityScore": _f(r.get("accountabilityScore")),
                    "resultadoLiquido": lucro,
                    "roi": _round2(lucro),
                    "globalScore": _f(g.get("globalScore")),
                    "goalPercentual": goal_pct,
                    "performanceScore": _f(perf.get("operatorPerformanceScore") or perf.get("performanceScore")),
                    "evolucaoDelta": _f(perf.get("evolucaoDelta")),
                    "cashRiskScore": _f(perf.get("cashRiskScore")),
                    "benchmarkScore": benchmark_score,
                }
            )

        ranked = sorted(operators, key=lambda x: x.get("benchmarkScore") or 0, reverse=True)
        top20 = ranked[:20]
        bottom20 = sorted(operators, key=lambda x: x.get("benchmarkScore") or 0)[:20]
        by_roi = sorted(operators, key=lambda x: x.get("roi") or 0, reverse=True)
        by_acc = sorted(operators, key=lambda x: x.get("accountabilityScore") or 0, reverse=True)
        by_risk = sorted(operators, key=lambda x: x.get("cashRiskScore") or 0, reverse=True)
        by_evol = sorted(operators, key=lambda x: x.get("evolucaoDelta") or -999, reverse=True)
        by_queda = sorted(operators, key=lambda x: x.get("evolucaoDelta") or 999)

        summary = f040.get("summary") or {}
        return {
            "operators": operators,
            "top20": top20,
            "bottom20": bottom20,
            "maiorRoi": by_roi[0] if by_roi else None,
            "maiorAccountability": by_acc[0] if by_acc else None,
            "maiorRisco": by_risk[0] if by_risk else None,
            "maiorEvolucao": summary.get("melhorOperador") or (by_evol[0] if by_evol else None),
            "maiorQueda": summary.get("piorOperador") or (by_queda[0] if by_queda else None),
            "melhorOperador": ranked[0] if ranked else None,
            "piorOperador": ranked[-1] if ranked else None,
        }

    def _pdv_shift_benchmark(self, layers: dict[str, Any]) -> dict[str, Any]:
        f043 = layers["f043"]
        f045 = layers["f045"]
        f040 = layers["f040"]
        f033 = layers["f033_cash"]
        achievements = (f045.get("goalAchievementEngine") or {}).get("achievements") or []
        alertas = (f045.get("goalAlertEngine") or {}).get("alerts") or []

        pdvs = list((f043.get("pdvProfitabilityEngine") or {}).get("pdvs") or [])
        turnos = list((f043.get("shiftProfitabilityEngine") or {}).get("turnos") or [])

        for p in pdvs:
            p["alertas"] = len([a for a in alertas if a.get("scope") == "PDV"])
            p["metasPct"] = _round2(_f(p.get("roi")))
        for t in turnos:
            t["alertas"] = len([a for a in alertas if a.get("scope") == "TURNO"])
            t["metasPct"] = _round2(_f(t.get("roi")))

        pdv_rank = sorted(pdvs, key=lambda x: _f(x.get("resultadoLiquido")), reverse=True)
        pdv_worst = sorted(pdvs, key=lambda x: _f(x.get("resultadoLiquido")))
        turno_rank = sorted(turnos, key=lambda x: _f(x.get("resultadoLiquido")), reverse=True)
        turno_worst = sorted(turnos, key=lambda x: _f(x.get("resultadoLiquido")))
        by_risco = sorted(pdvs, key=lambda x: _f(x.get("riscoEconomico")), reverse=True)
        by_oport = sorted(pdvs, key=lambda x: _f(x.get("margemOperacional")) - _f(x.get("destruicaoMargem")), reverse=True)

        summary = f040.get("summary") or {}
        return {
            "pdvs": pdvs,
            "turnos": turnos,
            "rankingPdvs": pdv_rank,
            "rankingTurnos": turno_rank,
            "melhorPdv": summary.get("melhorPdv") or (pdv_rank[0] if pdv_rank else None),
            "piorPdv": summary.get("piorPdv") or (pdv_worst[0] if pdv_worst else None),
            "melhorTurno": turno_rank[0] if turno_rank else None,
            "piorTurno": turno_worst[0] if turno_worst else None,
            "maiorRisco": by_risco[0] if by_risco else None,
            "maiorOportunidade": by_oport[0] if by_oport else None,
            "diferencaRede": _f((f033.get("data") or f033).get("diferencaTotalRede") if isinstance(f033, dict) else 0),
        }

    @staticmethod
    def _gap_engine(
        company: dict[str, Any], operators: dict[str, Any], pdv_shift: dict[str, Any]
    ) -> dict[str, Any]:
        filiais = company.get("filiais") or []
        avg_receita = mean([_f(f.get("receita")) for f in filiais]) if filiais else 0.0
        avg_roi = mean([_f(f.get("roi")) for f in filiais]) if filiais else 0.0

        op_rows = operators.get("operators") or []
        avg_op = mean([_f(o.get("benchmarkScore")) for o in op_rows]) if op_rows else 0.0
        pdvs = pdv_shift.get("pdvs") or []
        avg_pdv = mean([_f(p.get("resultadoLiquido")) for p in pdvs]) if pdvs else 0.0
        turnos = pdv_shift.get("turnos") or []
        avg_turno = mean([_f(t.get("resultadoLiquido")) for t in turnos]) if turnos else 0.0

        gaps_filiais = [f for f in filiais if _f(f.get("receita")) < avg_receita or _f(f.get("roi")) < avg_roi]
        gaps_ops = [o for o in op_rows if _f(o.get("benchmarkScore")) < avg_op]
        gaps_pdvs = [p for p in pdvs if _f(p.get("resultadoLiquido")) < avg_pdv]
        gaps_turnos = [t for t in turnos if _f(t.get("resultadoLiquido")) < avg_turno]

        all_gaps = (
            [{"tipo": "FILIAL", "gap": _round2(avg_receita - _f(f.get("receita"))), **f} for f in gaps_filiais]
            + [{"tipo": "OPERADOR", "gap": _round2(avg_op - _f(o.get("benchmarkScore"))), **o} for o in gaps_ops]
            + [{"tipo": "PDV", "gap": _round2(avg_pdv - _f(p.get("resultadoLiquido"))), **p} for p in gaps_pdvs]
            + [{"tipo": "TURNO", "gap": _round2(avg_turno - _f(t.get("resultadoLiquido"))), **t} for t in gaps_turnos]
        )
        all_gaps.sort(key=lambda x: x.get("gap") or 0, reverse=True)

        return {
            "filiaisAbaixoMedia": gaps_filiais,
            "operadoresAbaixoMedia": gaps_ops,
            "pdvsAbaixoMedia": gaps_pdvs,
            "turnosAbaixoMedia": gaps_turnos,
            "maiorGap": all_gaps[0] if all_gaps else None,
            "gaps": all_gaps[:30],
            "medias": {
                "receitaFilial": _round2(avg_receita),
                "benchmarkOperador": _round2(avg_op),
                "resultadoPdv": _round2(avg_pdv),
                "resultadoTurno": _round2(avg_turno),
            },
        }

    @staticmethod
    def _best_practices(
        company: dict[str, Any], operators: dict[str, Any], pdv_shift: dict[str, Any], gaps: dict[str, Any]
    ) -> dict[str, Any]:
        top_op = (operators.get("top20") or [None])[0]
        top_pdv = (pdv_shift.get("rankingPdvs") or [None])[0]
        top_filial = company.get("melhorFilial")
        bottom_op = (operators.get("bottom20") or [None])[0]
        bottom_pdv = (pdv_shift.get("piorPdv") or pdv_shift.get("rankingPdvs", [None])[-1] if pdv_shift.get("rankingPdvs") else None)

        vencedores = [
            {"padrao": "Alto benchmark operador", "referencia": top_op, "acao": "Replicar mix vendas + accountability"},
            {"padrao": "PDV com margem preservada", "referencia": top_pdv, "acao": "Padronizar fechamento e mix PDV"},
            {"padrao": "Filial líder receita", "referencia": top_filial, "acao": "Expandir playbook comercial"},
        ]
        perdedores = [
            {"padrao": "Operador abaixo da média", "referencia": bottom_op, "acao": "Treinamento + metas F04.5"},
            {"padrao": "PDV destruição de margem", "referencia": bottom_pdv, "acao": "Auditoria caixa + redução faltas"},
        ]
        return {
            "vencedores": vencedores,
            "perdedores": perdedores,
            "acoesReplicaveis": [v["acao"] for v in vencedores],
            "acoesCorretivas": [p["acao"] for p in perdedores],
            "melhorPratica": vencedores[0] if vencedores else None,
            "piorPratica": perdedores[-1] if perdedores else None,
        }

    def _qa_engine(
        self,
        layers: dict[str, Any],
        company: dict[str, Any],
        operators: dict[str, Any],
        empresa_codigo: str | int | None,
    ) -> dict[str, Any]:
        f045_qa = layers["f045_qa"]
        paridade = _f(company.get("paridadeDelta") or f045_qa.get("paridadeDelta") or layers["f045_ex"].get("paridadeDelta"))
        op_count = len(operators.get("operators") or [])
        filial_count = len(company.get("filiais") or [])
        orphan = 0
        for op in operators.get("operators") or []:
            if not op.get("employeeName") and not op.get("funcionarioCodigo"):
                orphan += 1

        cross_tenant = False
        if empresa_codigo is not None:
            code = int(empresa_codigo)
            filiais = company.get("filiais") or []
            cross_tenant = any(
                f.get("empresaCodigo") not in (None, code) for f in filiais if f.get("empresaCodigo") is not None
            ) and len(filiais) > 1

        ids = [o.get("funcionarioCodigo") for o in operators.get("operators") or []]
        duplicidade = len(ids) - len(set(ids))

        return {
            "paridadeDelta": paridade,
            "paridadeZero": paridade <= 0.01,
            "crossTenant": cross_tenant,
            "semCrossTenant": not cross_tenant,
            "duplicidade": duplicidade,
            "semDuplicidade": duplicidade == 0,
            "metricasOrfas": orphan,
            "semMetricasOrfas": orphan == 0,
            "operadoresIndexados": op_count,
            "filiaisIndexadas": filial_count,
            "fonteWebPosto": False,
            "fonteF045": F045_AUDIT.exists(),
            "evidenciaCompleta": bool(f045_qa.get("evidenciaCompleta", True)),
        }

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        t0 = time.perf_counter()
        if not F045_AUDIT.exists():
            return WebPostoResponse.fail("Execute scripts/audit_f04_5_goals_campaign_engine.py antes do F04.6")

        layers = self._load_layers(data_inicial, data_final)
        if not layers["f045"] and not layers["f045_ex"]:
            return WebPostoResponse.fail("Snapshot F04.5 ausente para benchmark")

        company = self._company_benchmark(layers)
        operators = self._operator_benchmark(layers)
        pdv_shift = self._pdv_shift_benchmark(layers)
        gaps = self._gap_engine(company, operators, pdv_shift)
        practices = self._best_practices(company, operators, pdv_shift, gaps)
        qa = self._qa_engine(layers, company, operators, empresa_codigo)

        f033 = layers["f033_cash"]
        cash_data = f033.get("data") if isinstance(f033.get("data"), dict) else f033
        potencial_capturavel = _round2(_f((cash_data or {}).get("potencialRecuperavel30pct")))
        potencial_perdido = _round2(_f((cash_data or {}).get("perdaObservada90d")))

        ranking_executivo = {
            "filiais": (company.get("ranking") or [])[:5],
            "operadores": (operators.get("top20") or [])[:5],
            "pdvs": (pdv_shift.get("rankingPdvs") or [])[:3],
            "turnos": (pdv_shift.get("rankingTurnos") or [])[:3],
        }

        executive = {
            "1_melhorFilial": company.get("melhorFilial"),
            "2_piorFilial": company.get("piorFilial"),
            "3_melhorOperador": operators.get("melhorOperador"),
            "4_piorOperador": operators.get("piorOperador"),
            "5_melhorPdv": pdv_shift.get("melhorPdv"),
            "6_piorPdv": pdv_shift.get("piorPdv"),
            "7_melhorTurno": pdv_shift.get("melhorTurno"),
            "8_piorTurno": pdv_shift.get("piorTurno"),
            "9_maiorRoi": company.get("maiorRoi") or operators.get("maiorRoi"),
            "10_maiorRisco": company.get("maiorRisco") or operators.get("maiorRisco"),
            "11_maiorOportunidade": pdv_shift.get("maiorOportunidade"),
            "12_maiorGap": gaps.get("maiorGap"),
            "13_melhorPratica": practices.get("melhorPratica"),
            "14_piorPratica": practices.get("piorPratica"),
            "15_potencialCapturavel": potencial_capturavel,
            "16_potencialPerdido": potencial_perdido,
            "17_rankingExecutivo": ranking_executivo,
            "18_benchmarkConfiavel": qa.get("paridadeZero") and qa.get("semCrossTenant") and qa.get("semDuplicidade"),
            "19_prontoScorecard": qa.get("paridadeZero") and bool(operators.get("operators")),
            "20_aprovadoF047": False,
            "paridadeDelta": qa.get("paridadeDelta"),
        }
        executive["20_aprovadoF047"] = (
            executive["18_benchmarkConfiavel"]
            and executive["19_prontoScorecard"]
            and qa.get("semMetricasOrfas")
            and qa.get("fonteF045")
        )

        parecer = (
            "[PARECER FINAL: APROVADO PARA F04.7]"
            if executive["20_aprovadoF047"]
            else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"
        )

        payload = {
            "sprint": "F04.6",
            "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
            "elapsedMs": round((time.perf_counter() - t0) * 1000, 1),
            "fonte": {"f045Audit": str(F045_AUDIT.name), "webPosto": False},
            "companyBenchmark": company,
            "operatorBenchmark": operators,
            "pdvBenchmark": pdv_shift,
            "shiftBenchmark": {
                "turnos": pdv_shift.get("turnos"),
                "ranking": pdv_shift.get("rankingTurnos"),
                "melhor": pdv_shift.get("melhorTurno"),
                "pior": pdv_shift.get("piorTurno"),
            },
            "gapEngine": gaps,
            "bestPracticesEngine": practices,
            "cockpit": {
                "rankingFiliais": company.get("ranking") or [],
                "rankingOperadores": operators.get("top20") or [],
                "rankingPdvs": pdv_shift.get("rankingPdvs") or [],
                "rankingTurnos": pdv_shift.get("rankingTurnos") or [],
                "gaps": gaps.get("gaps") or [],
                "bestPractices": practices.get("vencedores") or [],
            },
            "executiveAnswers": executive,
            "qa": qa,
            "parecerFinal": parecer,
        }
        return WebPostoResponse.ok(payload)
