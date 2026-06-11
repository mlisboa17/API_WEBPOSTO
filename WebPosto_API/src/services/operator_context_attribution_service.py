"""F03.4-B — Context vs Operator Attribution (camada aditiva)."""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from typing import Any

from src.services.cash_operations_service import CRITICAL_OPERATORS, CRITICAL_PDVS, _dec, _round2

CLASS_INDEPENDENTE = "INDEPENDENTE_DO_CONTEXTO"
CLASS_PDV = "DEPENDENTE_DO_PDV"
CLASS_TURNO = "DEPENDENTE_DO_TURNO"
CLASS_FILIAL = "DEPENDENTE_DA_FILIAL"
CLASS_INCONCLUSIVO = "INCONCLUSIVO"

MANDATORY_OPERATORS = (276288, 294273)
MANDATORY_PDVS = (54193, 15880)


def _diversity_score(counts: Counter) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    if len(counts) <= 1:
        return 0.0
    shares = [c / total for c in counts.values()]
    hhi = sum(s * s for s in shares)
    n = len(counts)
    if n <= 1:
        return 0.0
    min_hhi = 1.0 / n
    if hhi <= min_hhi:
        return 100.0
    return _round2(100.0 * (1.0 - (hhi - min_hhi) / (1.0 - min_hhi)))


def _dominant_share(counts: Counter) -> tuple[Any, float]:
    if not counts:
        return None, 0.0
    total = sum(counts.values())
    key, val = counts.most_common(1)[0]
    return key, val / total if total else 0.0


def _local_closure_score(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 50.0
    diffs = [abs(_dec(r.get("diferenca"))) for r in rows]
    mx = max(diffs) if diffs else 1.0
    mx = mx or 1.0
    avg = statistics.mean(diffs) if diffs else 0.0
    return _round2(100.0 * (1.0 - min(avg / mx, 1.0)))


class OperatorContextAttributionService:
    """Determina se performance é do operador ou explicada pelo contexto operacional."""

    @staticmethod
    def reconstruct_merged_from_rankings(
        pdv_ranking: list[dict[str, Any]],
        operators: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Reconstrói linhas aproximadas quando `_merged` não está disponível (relatórios offline)."""
        op_diff: dict[Any, float] = {}
        if operators:
            for op in operators:
                code = op.get("funcionarioCodigo")
                fech = op.get("fechamentos") or 1
                op_diff[code] = float(op.get("diferencaAcumulada") or 0) / fech

        rows: list[dict[str, Any]] = []
        for pdv in pdv_ranking:
            pdv_code = pdv.get("pdvCodigo")
            turn_label = None
            turns = pdv.get("turnos") or []
            if turns:
                turn_label = turns[0].get("turno") or turns[0].get("turnoCodigo")
            per_closure = float(pdv.get("diferencaAcumulada") or 0) / max(pdv.get("fechamentos") or 1, 1)
            for op_info in pdv.get("operadores") or []:
                op_code = op_info.get("funcionarioCodigo")
                diff = op_diff.get(op_code, per_closure)
                for _ in range(max(op_info.get("fechamentos") or 1, 1)):
                    rows.append(
                        {
                            "funcionarioCodigo": op_code,
                            "pdvCodigo": pdv_code,
                            "turno": turn_label,
                            "turnoCodigo": turn_label,
                            "empresaCodigo": pdv.get("empresaCodigo"),
                            "diferenca": diff,
                        }
                    )
        return rows

    @classmethod
    def build(
        cls,
        merged: list[dict[str, Any]],
        operators: list[dict[str, Any]],
        pdvs: list[dict[str, Any]],
        turns: list[dict[str, Any]],
        filiais: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        pdv_scores = {p.get("pdvCodigo"): float(p.get("performanceScore") or 50) for p in pdvs}
        turn_scores = {
            (t.get("turnoCodigo") or t.get("turno")): float(t.get("performanceScore") or 50) for t in turns
        }
        filial_scores = {
            f.get("empresaCodigo"): max(
                0.0,
                min(100.0, 100.0 - abs(float(f.get("diferencaMedia") or 0)) * 0.5),
            )
            for f in (filiais or [])
        }

        by_op: dict[Any, dict[str, Any]] = defaultdict(
            lambda: {"pdv": Counter(), "turn": Counter(), "filial": Counter(), "rows": []}
        )
        for row in merged:
            op = row.get("funcionarioCodigo")
            if op is None:
                continue
            bucket = by_op[op]
            bucket["pdv"][row.get("pdvCodigo")] += 1
            turn_key = row.get("turno") or row.get("turnoCodigo") or "?"
            bucket["turn"][turn_key] += 1
            bucket["filial"][row.get("empresaCodigo")] += 1
            bucket["rows"].append(row)

        op_score_map = {o.get("funcionarioCodigo"): float(o.get("performanceScore") or 0) for o in operators}
        network_avg = statistics.mean(op_score_map.values()) if op_score_map else 50.0

        per_operator: list[dict[str, Any]] = []
        for op, ctx in by_op.items():
            base_score = op_score_map.get(op, 50.0)
            pdv_div = _diversity_score(ctx["pdv"])
            turn_div = _diversity_score(ctx["turn"])
            dom_pdv, pdv_share = _dominant_share(ctx["pdv"])
            dom_turn, turn_share = _dominant_share(ctx["turn"])
            dom_filial, filial_share = _dominant_share(ctx["filial"])
            fechamentos = len(ctx["rows"])

            expected_parts: list[float] = []
            for row in ctx["rows"]:
                pdv = row.get("pdvCodigo")
                turn = row.get("turno") or row.get("turnoCodigo")
                filial = row.get("empresaCodigo")
                part = (
                    pdv_scores.get(pdv, 50.0) * 0.45
                    + turn_scores.get(turn, 50.0) * 0.35
                    + filial_scores.get(filial, 50.0) * 0.20
                )
                expected_parts.append(part)
            expected_score = _round2(statistics.mean(expected_parts)) if expected_parts else 50.0

            context_risk_penalty = 0.0
            if pdv_share >= 0.75 and dom_pdv in pdv_scores:
                pdv_ctx = pdv_scores[dom_pdv]
                if base_score > pdv_ctx + 8 and pdv_ctx >= 55:
                    context_risk_penalty += min(12.0, (base_score - pdv_ctx) * 0.45)
                elif base_score < pdv_ctx - 8 and pdv_ctx <= 45:
                    context_risk_penalty -= min(8.0, (pdv_ctx - base_score) * 0.35)

            if turn_share >= 0.85 and dom_turn in turn_scores:
                turn_ctx = turn_scores[dom_turn]
                if base_score > turn_ctx + 8 and turn_ctx >= 55:
                    context_risk_penalty += min(8.0, (base_score - turn_ctx) * 0.35)

            multi_context_bonus = 0.0
            if len(ctx["pdv"]) >= 2:
                local = []
                for pdv_code in ctx["pdv"]:
                    pdv_rows = [r for r in ctx["rows"] if r.get("pdvCodigo") == pdv_code]
                    local.append(_local_closure_score(pdv_rows))
                if local and min(local) >= 55 and statistics.stdev(local) <= 20:
                    multi_context_bonus += 8.0
                elif len(ctx["pdv"]) >= 2:
                    multi_context_bonus += 3.0
            if pdv_div >= 50 and turn_div >= 40:
                multi_context_bonus += 4.0

            adjusted = _round2(max(0.0, min(100.0, base_score - context_risk_penalty + multi_context_bonus)))
            alignment_gap = abs(base_score - expected_score)
            context_dependency = _round2(
                min(
                    100.0,
                    pdv_share * 35
                    + turn_share * 25
                    + filial_share * 10
                    + alignment_gap * 0.35
                    + max(0.0, 40.0 - pdv_div) * 0.25
                    + max(0.0, 40.0 - turn_div) * 0.15,
                )
            )

            classification = cls._classify(
                fechamentos=fechamentos,
                pdv_div=pdv_div,
                turn_div=turn_div,
                pdv_share=pdv_share,
                turn_share=turn_share,
                filial_count=len(ctx["filial"]),
                alignment_gap=alignment_gap,
                unique_pdvs=len(ctx["pdv"]),
            )

            per_operator.append(
                {
                    "funcionarioCodigo": op,
                    "operatorPerformanceScore": _round2(base_score),
                    "contextAdjustedPerformanceScore": adjusted,
                    "contextExpectedScore": expected_score,
                    "contextRiskPenalty": _round2(context_risk_penalty),
                    "multiContextBonus": _round2(multi_context_bonus),
                    "pdvDiversityScore": pdv_div,
                    "turnDiversityScore": turn_div,
                    "contextDependencyLevel": context_dependency,
                    "contextClassification": classification,
                    "dominantPdv": dom_pdv,
                    "dominantPdvShare": _round2(pdv_share * 100),
                    "dominantTurn": dom_turn,
                    "dominantTurnShare": _round2(turn_share * 100),
                    "dominantFilial": dom_filial,
                    "pdvsTrabalhados": sorted(ctx["pdv"].keys(), key=lambda x: str(x)),
                    "turnosTrabalhados": sorted(ctx["turn"].keys(), key=lambda x: str(x)),
                    "fechamentos": fechamentos,
                }
            )

        per_operator.sort(key=lambda x: x.get("contextAdjustedPerformanceScore") or 0, reverse=True)

        pdv_operator_perf: dict[Any, list[float]] = defaultdict(list)
        for item in per_operator:
            op = item["funcionarioCodigo"]
            ctx = by_op.get(op, {})
            for pdv_code in ctx.get("pdv", {}):
                pdv_operator_perf[pdv_code].append(item["operatorPerformanceScore"])

        turn_operator_perf: dict[Any, list[float]] = defaultdict(list)
        for item in per_operator:
            op = item["funcionarioCodigo"]
            ctx = by_op.get(op, {})
            for turn_code in ctx.get("turn", {}):
                turn_operator_perf[turn_code].append(item["operatorPerformanceScore"])

        harmful_pdvs = [
            p.get("pdvCodigo")
            for p in pdvs
            if float(p.get("performanceScore") or 0) < 45
            and len(pdv_operator_perf.get(p.get("pdvCodigo"), [])) >= 2
            and statistics.mean(pdv_operator_perf[p.get("pdvCodigo")]) < network_avg - 5
        ]
        harmful_turns = [
            t.get("turnoCodigo") or t.get("turno")
            for t in turns
            if float(t.get("performanceScore") or 0) < 45
            and len(turn_operator_perf.get(t.get("turnoCodigo") or t.get("turno"), [])) >= 2
        ]

        top_ops = sorted(operators, key=lambda x: x.get("performanceScore") or 0, reverse=True)[:5]
        bottom_ops = sorted(operators, key=lambda x: x.get("performanceScore") or 0)[:5]
        top_att = {o["funcionarioCodigo"]: o for o in per_operator if o["funcionarioCodigo"] in [t.get("funcionarioCodigo") for t in top_ops]}
        bottom_att = {o["funcionarioCodigo"]: o for o in per_operator if o["funcionarioCodigo"] in [t.get("funcionarioCodigo") for t in bottom_ops]}

        mandatory = cls._mandatory_cases(per_operator, pdv_scores, harmful_pdvs, harmful_turns)
        questions = cls._mandatory_questions(
            per_operator,
            top_att,
            bottom_att,
            pdv_scores,
            harmful_pdvs,
            harmful_turns,
            network_avg,
        )
        executive = cls._executive_extension(questions, per_operator, harmful_pdvs, harmful_turns)

        return {
            "operators": per_operator,
            "rankingAjustado": per_operator[:20],
            "mandatoryCases": mandatory,
            "mandatoryQuestions": questions,
            "executiveAnswers": executive,
            "harmfulPdvs": harmful_pdvs,
            "harmfulTurns": harmful_turns,
            "multiContextOperators": [
                o for o in per_operator if o.get("contextClassification") == CLASS_INDEPENDENTE
            ],
            "contextDependentOperators": [
                o
                for o in per_operator
                if o.get("contextClassification")
                in (CLASS_PDV, CLASS_TURNO, CLASS_FILIAL)
            ],
            "formula": {
                "contextAdjustedPerformanceScore": "operatorPerformanceScore - contextRiskPenalty + multiContextBonus",
                "pdvDiversityScore": "1 - HHI normalizado (0=mono-PDV, 100=distribuído)",
                "turnDiversityScore": "1 - HHI normalizado",
                "contextDependencyLevel": "concentração de contexto + gap vs score esperado",
            },
        }

    @staticmethod
    def _classify(
        fechamentos: int,
        pdv_div: float,
        turn_div: float,
        pdv_share: float,
        turn_share: float,
        filial_count: int,
        alignment_gap: float,
        unique_pdvs: int,
    ) -> str:
        if fechamentos < 2:
            return CLASS_INCONCLUSIVO
        if unique_pdvs >= 2 and pdv_div >= 45 and alignment_gap < 18:
            return CLASS_INDEPENDENTE
        if pdv_share >= 0.75 and pdv_div < 40:
            return CLASS_PDV
        if turn_share >= 0.85 and turn_div < 35:
            return CLASS_TURNO
        if filial_count <= 1 and pdv_div < 30 and turn_div < 30:
            return CLASS_FILIAL
        if unique_pdvs >= 2 or pdv_div >= 40:
            return CLASS_INDEPENDENTE
        return CLASS_INCONCLUSIVO

    @staticmethod
    def _mandatory_cases(
        per_operator: list[dict[str, Any]],
        pdv_scores: dict[Any, float],
        harmful_pdvs: list[Any],
        harmful_turns: list[Any],
    ) -> dict[str, Any]:
        by_op = {o["funcionarioCodigo"]: o for o in per_operator}
        return {
            "operador276288": by_op.get(276288),
            "operador294273": by_op.get(294273),
            "pdv54193": {
                "pdvCodigo": 54193,
                "performanceScore": pdv_scores.get(54193),
                "prejudicaOperadores": 54193 in harmful_pdvs,
            },
            "pdv15880": {
                "pdvCodigo": 15880,
                "performanceScore": pdv_scores.get(15880),
                "prejudicaOperadores": 15880 in harmful_pdvs,
            },
            "turnosPrejudiciais": harmful_turns,
        }

    @staticmethod
    def _mandatory_questions(
        per_operator: list[dict[str, Any]],
        top_att: dict[Any, dict],
        bottom_att: dict[Any, dict],
        pdv_scores: dict[Any, float],
        harmful_pdvs: list[Any],
        harmful_turns: list[Any],
        network_avg: float,
    ) -> dict[str, Any]:
        def same_pdv_concentration(items: dict[Any, dict], threshold: float = 75.0) -> bool:
            if not items:
                return False
            shares = [i.get("dominantPdvShare") or 0 for i in items.values()]
            return statistics.mean(shares) >= threshold

        def same_turn_concentration(items: dict[Any, dict], threshold: float = 85.0) -> bool:
            if not items:
                return False
            shares = [i.get("dominantTurnShare") or 0 for i in items.values()]
            return statistics.mean(shares) >= threshold

        good_on_bad_pdv = []
        bad_on_good_pdv = []
        for item in per_operator:
            op = item["funcionarioCodigo"]
            for pdv in item.get("pdvsTrabalhados") or []:
                pdv_score = pdv_scores.get(pdv, 50)
                op_score = item.get("operatorPerformanceScore") or 0
                if pdv in MANDATORY_PDVS or pdv_score < 45:
                    if op_score >= 60:
                        good_on_bad_pdv.append({"funcionarioCodigo": op, "pdvCodigo": pdv, "score": op_score})
                if pdv_score >= 70 and op_score < 45:
                    bad_on_good_pdv.append({"funcionarioCodigo": op, "pdvCodigo": pdv, "score": op_score})

        consistent = [
            o
            for o in per_operator
            if o.get("contextClassification") == CLASS_INDEPENDENTE and (o.get("fechamentos") or 0) >= 3
        ]
        dependent = sorted(
            [o for o in per_operator if (o.get("contextDependencyLevel") or 0) >= 55],
            key=lambda x: x.get("contextDependencyLevel") or 0,
            reverse=True,
        )

        return {
            "1_melhoresMesmosPdvs": same_pdv_concentration(top_att),
            "2_pioresMesmosPdvs": same_pdv_concentration(bottom_att),
            "3_melhoresMesmosTurnos": same_turn_concentration(top_att),
            "4_pioresMesmosTurnos": same_turn_concentration(bottom_att),
            "5_operadorBomEmPdvRuim": good_on_bad_pdv[:10],
            "6_operadorRuimEmPdvBom": bad_on_good_pdv[:10],
            "7_pdvPrejudicaOperadores": harmful_pdvs,
            "8_turnoPrejudicaOperadores": harmful_turns,
            "9_operadorConsistenteMultiContexto": consistent[:10],
            "10_operadorDependenteDeContexto": dependent[:10],
            "networkAvgScore": _round2(network_avg),
        }

    @staticmethod
    def _executive_extension(
        questions: dict[str, Any],
        per_operator: list[dict[str, Any]],
        harmful_pdvs: list[Any],
        harmful_turns: list[Any],
    ) -> dict[str, Any]:
        dependent_count = sum(
            1
            for o in per_operator
            if o.get("contextClassification") in (CLASS_PDV, CLASS_TURNO, CLASS_FILIAL)
        )
        independent_count = sum(
            1 for o in per_operator if o.get("contextClassification") == CLASS_INDEPENDENTE
        )
        mostly_context = dependent_count > independent_count
        multi = questions.get("9_operadorConsistenteMultiContexto") or []
        specific = questions.get("10_operadorDependenteDeContexto") or []

        ranking_recommendation = "AJUSTADO_POR_CONTEXTO"
        if mostly_context and len(harmful_pdvs) >= 2:
            ranking_recommendation = "DUAL_BRUTO_E_AJUSTADO"
        elif independent_count >= dependent_count:
            ranking_recommendation = "BRUTO_COM_FLAG_CONTEXTO"

        return {
            "21_performanceIndividualOuContexto": "MISTA"
            if mostly_context
            else "PREDOMINANTEMENTE_INDIVIDUAL",
            "22_operadoresBonsMultiContexto": [o.get("funcionarioCodigo") for o in multi[:5]],
            "23_operadoresSóContextoEspecifico": [o.get("funcionarioCodigo") for o in specific[:5]],
            "24_pdvsPrejudicamOperadores": harmful_pdvs,
            "25_turnosPrejudicamOperadores": harmful_turns,
            "26_rankingFinalRecomendado": ranking_recommendation,
            "dependentesDeContexto": dependent_count,
            "independentesDeContexto": independent_count,
        }
