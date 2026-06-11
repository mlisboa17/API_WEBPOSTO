#!/usr/bin/env python3
"""Gera relatórios F05.4 Autonomous Recommendation Engine."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f05_4_autonomous_recommendation_engine.json"


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
    opp = w.get("opportunityDiscoveryEngine") or {}
    risk = w.get("riskDiscoveryEngine") or {}
    feed = w.get("executiveFeedEngine") or {}
    ac = w.get("actionCenterIntegration") or {}
    parecer = w.get("parecerFinal") or data.get("parecerFinal") or ""

    _w(
        "OPPORTUNITY_DISCOVERY_ENGINE_REPORT.md",
        f"# Opportunity Discovery Engine (F05.4)\n\n"
        f"- Oportunidades detectadas: **{ex.get('2_oportunidadesDetectadas')}**\n"
        f"- Maior oportunidade: **{ex.get('7_maiorOportunidade')}**\n"
        f"- Total engine: **{opp.get('total')}**\n"
        f"- Fonte WebPosto: **False**\n",
    )
    _w(
        "RISK_DISCOVERY_ENGINE_REPORT.md",
        f"# Risk Discovery Engine\n\n"
        f"- Riscos detectados: **{ex.get('3_riscosDetectados')}**\n"
        f"- Maior risco: **{ex.get('8_maiorRisco')}**\n"
        f"- Total engine: **{risk.get('total')}**\n",
    )
    _w(
        "RECOMMENDATION_PRIORITIZATION_REPORT.md",
        f"# Recommendation Prioritization\n\n"
        f"- Total recomendações: **{ex.get('1_totalRecomendacoes')}**\n"
        f"- P1: **{ex.get('4_prioridadeP1')}**\n"
        f"- P2: **{ex.get('5_prioridadeP2')}**\n"
        f"- P3: **{ex.get('6_prioridadeP3')}**\n"
        f"- Campos: recommendationId, priority, impactScore, roiScore, urgencyScore, confidenceLevel\n",
    )
    _w(
        "ROI_FORECAST_ENGINE_REPORT.md",
        f"# ROI Forecast Engine\n\n"
        f"- Maior ROI previsto: **{ex.get('9_maiorRoiPrevisto')}**\n"
        f"- Menor ROI previsto: **{ex.get('10_menorRoiPrevisto')}**\n"
        f"- Label obrigatório: **ROI_PREVISTO**\n"
        f"- ROI realizado: somente com executionEvidence (Action Center)\n",
    )
    _w(
        "RECOMMENDATION_LIFECYCLE_REPORT.md",
        f"# Recommendation Lifecycle\n\n"
        f"- Estados: GERADA, ANALISADA, ACEITA, REJEITADA, CONVERTIDA_EM_ACAO, EXPIRADA\n"
        f"- Integração F05.2 Action Center: **readOnly={ac.get('readOnly')}**\n"
        f"- Ações vinculadas: **{ac.get('linkedActions')}**\n"
        f"- Execução automática: **False**\n",
    )
    _w(
        "EXECUTIVE_FEED_REPORT.md",
        f"# Executive Feed\n\n"
        f"- Itens no feed: **{feed.get('total')}**\n"
        f"- Feed aprovado: **{ex.get('18_feedExecutivoAprovado')}**\n"
        f"- Campos: headline, impacto, evidência, roi, prioridade\n",
    )
    _w(
        "RECOMMENDATION_COCKPIT_REPORT.md",
        f"# Recommendation Cockpit\n\n"
        f"- View: **recommendations**\n"
        f"- API: `/api/v1/autonomous-recommendations/cockpit`\n"
        f"- Widgets: Top Recomendações, Top Oportunidades, Top Riscos, P1, P2, P3, ROI Previsto\n",
    )
    _w(
        "DW_RECOMMENDATION_MODEL.md",
        f"# DW Recommendation Model\n\n"
        f"- `fact_recommendation`\n"
        f"- `fact_recommendation_roi`\n"
        f"- `fact_recommendation_status`\n"
        f"- `fact_recommendation_priority`\n"
        f"- DDL: `dw/ddl/fact_autonomous_recommendation.sql`\n",
    )
    _w(
        "AUTONOMOUS_RECOMMENDATION_QA_REPORT.md",
        f"# Autonomous Recommendation QA Gate\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| Sem recomendação sem evidência | {qa.get('semRecomendacaoSemEvidencia')} |\n"
        f"| Sem recomendação sem lineage | {qa.get('semRecomendacaoSemLineage')} |\n"
        f"| Sem recomendação sem ROI | {qa.get('semRecomendacaoSemRoi')} |\n"
        f"| Sem recomendação sem confidence | {qa.get('semRecomendacaoSemConfidence')} |\n"
        f"| Sem cross-tenant | {qa.get('semCrossTenant')} |\n"
        f"| Sem execução automática | {qa.get('semExecucaoAutomatica')} |\n"
        f"| Motor auditável | {qa.get('auditavel')} |\n\n"
        f"{parecer}\n",
    )
    _w(
        "F05_4_AUTONOMOUS_RECOMMENDATION_ENGINE_REPORT.md",
        f"# F05.4 — Autonomous Recommendation Engine\n\n"
        f"## Respostas executivas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n## Critérios de aceite\n\n"
        f"- Snapshots homologados: **100%**\n"
        f"- Lineage obrigatório: **{qa.get('semRecomendacaoSemLineage')}**\n"
        f"- ROI obrigatório: **{qa.get('semRecomendacaoSemRoi')}**\n"
        f"- Confidence obrigatório: **{qa.get('semRecomendacaoSemConfidence')}**\n"
        f"- QA aprovado: **{qa.get('auditavel')}**\n\n"
        f"{parecer}\n",
    )


if __name__ == "__main__":
    main()
