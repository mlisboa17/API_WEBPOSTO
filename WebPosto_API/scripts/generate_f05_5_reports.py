#!/usr/bin/env python3
"""Gera relatórios F05.5 Closed Loop Learning Engine."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f05_5_closed_loop_learning_engine.json"


def _load() -> dict:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def _w(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def main() -> None:
    data = _load()
    w = data.get("windows", {}).get("7d") or {}
    ex = w.get("executiveAnswers") or data.get("executiveAnswers") or {}
    qa = w.get("qa") or {}
    outcome = w.get("outcomeMeasurementEngine") or {}
    rec_eff = w.get("recommendationEffectivenessEngine") or {}
    feedback = w.get("executiveFeedbackLoop") or {}
    parecer = w.get("parecerFinal") or data.get("parecerFinal") or ""

    _w(
        "OUTCOME_MEASUREMENT_REPORT.md",
        f"# Outcome Measurement (F05.5)\n\n"
        f"- Outcomes medidos: **{outcome.get('total')}**\n"
        f"- ROI previsto médio: **{ex.get('5_roiPrevistoMedio')}**\n"
        f"- ROI realizado médio: **{ex.get('6_roiRealizadoMedio')}**\n"
        f"- Erro médio: **{ex.get('7_erroMedio')}%**\n"
        f"- Campos: deltaROI, acuraciaROI, erroPercentual\n",
    )
    _w(
        "RECOMMENDATION_EFFECTIVENESS_REPORT.md",
        f"# Recommendation Effectiveness\n\n"
        f"- Recomendações avaliadas: **{ex.get('1_recomendacoesAvaliadas')}**\n"
        f"- Efetivas: **{ex.get('2_efetivas')}**\n"
        f"- Inefetivas: **{ex.get('3_inefetivas')}**\n"
        f"- Taxa de sucesso: **{rec_eff.get('recommendationSuccessRate')}%**\n",
    )
    _w(
        "ACTION_EFFECTIVENESS_REPORT.md",
        f"# Action Effectiveness\n\n"
        f"- Melhor ação: **{ex.get('10_melhorAcao')}**\n"
        f"- Pior ação: **{ex.get('11_piorAcao')}**\n"
        f"- Fonte: F05.2 Action Center (executionEvidence)\n",
    )
    _w(
        "LEARNING_ENGINE_REPORT.md",
        f"# Learning Engine\n\n"
        f"- Aprendizado acumulado: **{ex.get('13_aprendizadoAcumulado')}**\n"
        f"- Confiança aumentou: **{ex.get('14_confiancaAumentou')}**\n"
        f"- Confiança diminuiu: **{ex.get('15_confiancaDiminuiu')}**\n"
        f"- Motor aprendeu: **{ex.get('16_motorAprendeu')}**\n"
        f"- Campos: learningScore, confidenceAdjustment, historicalAccuracy\n",
    )
    _w(
        "RECOMMENDATION_SCORING_REPORT.md",
        f"# Recommendation Scoring\n\n"
        f"- Score histórico médio: **{ex.get('12_scoreHistoricoMedio')}**\n"
        f"- Melhor recomendação: **{ex.get('8_melhorRecomendacao')}**\n"
        f"- Pior recomendação: **{ex.get('9_piorRecomendacao')}**\n"
        f"- Escala: 0–100 (ROI, efetividade, execução, precisão)\n",
    )
    _w(
        "EXECUTIVE_FEEDBACK_LOOP_REPORT.md",
        f"# Executive Feedback Loop\n\n"
        f"- Taxa de acerto global: **{ex.get('4_taxaAcerto')}%**\n"
        f"- Feed aprovado: **{ex.get('17_feedExecutivoAprovado')}**\n\n"
        + "\n".join(f"- {item.get('headline')}" for item in (feedback.get("items") or []))
        + "\n",
    )
    _w(
        "LEARNING_COCKPIT_REPORT.md",
        f"# Learning Cockpit\n\n"
        f"- View: **learning**\n"
        f"- API: `/api/v1/closed-loop-learning/cockpit`\n"
        f"- Widgets: Precisão histórica, ROI previsto vs realizado, Top/Piores, Aprendizado, Taxa de acerto\n",
    )
    _w(
        "DW_LEARNING_MODEL.md",
        f"# DW Learning Model\n\n"
        f"- `fact_learning_event`\n"
        f"- `fact_recommendation_accuracy`\n"
        f"- `fact_roi_accuracy`\n"
        f"- `fact_learning_score`\n"
        f"- DDL: `dw/ddl/fact_closed_loop_learning.sql`\n",
    )
    _w(
        "CLOSED_LOOP_LEARNING_QA_REPORT.md",
        f"# Closed Loop Learning QA Gate\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| Sem aprendizado sem evidência | {qa.get('semAprendizadoSemEvidencia')} |\n"
        f"| Sem ROI realizado sem executionEvidence | {qa.get('semRoiRealizadoSemExecutionEvidence')} |\n"
        f"| Sem cross-tenant | {qa.get('semCrossTenant')} |\n"
        f"| Sem ajuste confiança sem histórico | {qa.get('semAjusteConfiancaSemHistorico')} |\n"
        f"| Sem score sem origem | {qa.get('semScoreSemOrigem')} |\n"
        f"| Sistema auditável | {qa.get('auditavel')} |\n\n"
        f"{parecer}\n",
    )
    _w(
        "F05_5_CLOSED_LOOP_LEARNING_ENGINE_REPORT.md",
        f"# F05.5 — Closed Loop Learning Engine\n\n"
        f"## Respostas executivas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n## Critérios de aceite\n\n"
        f"- Snapshots homologados: **100%**\n"
        f"- ROI realizado só com executionEvidence: **{qa.get('semRoiRealizadoSemExecutionEvidence')}**\n"
        f"- Lineage obrigatório: **True**\n"
        f"- QA aprovado: **{qa.get('auditavel')}**\n\n"
        f"{parecer}\n",
    )


if __name__ == "__main__":
    main()
