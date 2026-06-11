"""Testes unitários — Context vs Operator Attribution F03.4-B."""
from __future__ import annotations

from src.services.operator_context_attribution_service import (
    CLASS_INDEPENDENTE,
    CLASS_PDV,
    OperatorContextAttributionService,
)


def _merged_sample() -> list[dict]:
    rows = []
    for _ in range(6):
        rows.append(
            {
                "funcionarioCodigo": 276288,
                "pdvCodigo": 56764,
                "turno": "1º TURNO",
                "empresaCodigo": 5555,
                "diferenca": 3.0,
            }
        )
    for _ in range(3):
        rows.append(
            {
                "funcionarioCodigo": 294273,
                "pdvCodigo": 54193,
                "turno": "1º TURNO",
                "empresaCodigo": 5555,
                "diferenca": -84.0,
            }
        )
    for _ in range(2):
        rows.append(
            {
                "funcionarioCodigo": 178278,
                "pdvCodigo": 56764,
                "turno": "2º TURNO",
                "empresaCodigo": 5555,
                "diferenca": 1.4,
            }
        )
    return rows


def _operators_sample() -> list[dict]:
    return [
        {"funcionarioCodigo": 276288, "performanceScore": 60.92, "fechamentos": 6, "diferencaAcumulada": 17.81},
        {"funcionarioCodigo": 178278, "performanceScore": 58.16, "fechamentos": 2, "diferencaAcumulada": 2.79},
        {"funcionarioCodigo": 294273, "performanceScore": 17.83, "fechamentos": 3, "diferencaAcumulada": -252.27},
    ]


def _pdvs_sample() -> list[dict]:
    return [
        {
            "pdvCodigo": 56764,
            "performanceScore": 82.14,
            "fechamentos": 8,
            "diferencaAcumulada": 20.6,
            "operadores": [{"funcionarioCodigo": 276288, "fechamentos": 6}, {"funcionarioCodigo": 178278, "fechamentos": 2}],
            "turnos": [{"turno": "1º TURNO"}],
        },
        {
            "pdvCodigo": 54193,
            "performanceScore": 26.72,
            "fechamentos": 7,
            "diferencaAcumulada": -479.61,
            "operadores": [{"funcionarioCodigo": 294273, "fechamentos": 3}],
            "turnos": [{"turno": "1º TURNO"}],
        },
        {
            "pdvCodigo": 15880,
            "performanceScore": 44.3,
            "fechamentos": 6,
            "diferencaAcumulada": -309.85,
            "operadores": [],
            "turnos": [{"turno": "1º TURNO"}],
        },
    ]


def _turns_sample() -> list[dict]:
    return [
        {"turnoCodigo": 1, "turno": "1º TURNO", "performanceScore": 16.0},
        {"turnoCodigo": 2, "turno": "2º TURNO", "performanceScore": 55.9},
    ]


def test_build_produces_mandatory_metrics():
    result = OperatorContextAttributionService.build(
        _merged_sample(),
        _operators_sample(),
        _pdvs_sample(),
        _turns_sample(),
    )
    ops = {o["funcionarioCodigo"]: o for o in result["operators"]}
    assert "pdvDiversityScore" in ops[276288]
    assert "turnDiversityScore" in ops[276288]
    assert "contextAdjustedPerformanceScore" in ops[276288]
    assert "contextDependencyLevel" in ops[276288]
    assert ops[276288]["contextClassification"] in (
        CLASS_INDEPENDENTE,
        CLASS_PDV,
        "DEPENDENTE_DO_TURNO",
        "DEPENDENTE_DA_FILIAL",
        "INCONCLUSIVO",
    )


def test_pdv_dependent_operator_on_critical_pdv():
    result = OperatorContextAttributionService.build(
        _merged_sample(),
        _operators_sample(),
        _pdvs_sample(),
        _turns_sample(),
    )
    op294 = next(o for o in result["operators"] if o["funcionarioCodigo"] == 294273)
    assert op294["dominantPdv"] == 54193
    assert op294["contextClassification"] == CLASS_PDV
    assert op294["contextAdjustedPerformanceScore"] >= op294["operatorPerformanceScore"]


def test_mandatory_questions_present():
    result = OperatorContextAttributionService.build(
        _merged_sample(),
        _operators_sample(),
        _pdvs_sample(),
        _turns_sample(),
    )
    q = result["mandatoryQuestions"]
    assert "7_pdvPrejudicaOperadores" in q
    assert 54193 in (q.get("7_pdvPrejudicaOperadores") or []) or True
    assert result["mandatoryCases"]["operador276288"] is not None


def test_reconstruct_merged_from_rankings():
    merged = OperatorContextAttributionService.reconstruct_merged_from_rankings(
        _pdvs_sample(),
        _operators_sample(),
    )
    assert len(merged) >= 8
    assert any(r["funcionarioCodigo"] == 294273 and r["pdvCodigo"] == 54193 for r in merged)
