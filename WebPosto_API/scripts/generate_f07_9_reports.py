#!/usr/bin/env python3
"""Gera relatórios F07.9 Commercial Copilot & Executive Advisor."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f07_9_commercial_copilot.json"


def _load() -> dict:
    if not AUDIT.exists():
        raise SystemExit(f"Execute primeiro: python scripts/audit_f07_9_commercial_copilot.py\nArquivo ausente: {AUDIT}")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def _w(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def main() -> None:
    data = _load()
    w = data.get("windows", {}).get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    knowledge = w.get("commercialKnowledgeEngine") or {}
    reasoning = w.get("commercialReasoningEngine") or {}
    rec = w.get("commercialRecommendationEngine") or {}
    ac = w.get("commercialActionCenterIntegration") or {}
    conv = w.get("commercialConversationLayer") or {}
    gov = w.get("commercialGovernanceLayer") or {}
    qa = w.get("qa") or {}
    parecer = w.get("parecerFinal") or ""

    _w(
        "COMMERCIAL_KNOWLEDGE_ENGINE_REPORT.md",
        f"# IA-1 — Commercial Knowledge Engine\n\n"
        f"- Fontes: `{knowledge.get('sources')}`\n"
        f"- webPostoLive: **False**\n"
        f"- Oportunidades: **{len(knowledge.get('oportunidades') or [])}**\n",
    )
    _w(
        "COMMERCIAL_REASONING_ENGINE_REPORT.md",
        f"# IA-2 — Commercial Reasoning Engine\n\n"
        f"- Respostas catálogo: **{reasoning.get('total')}**\n"
        f"- Domínios: PRODUTO, ACAO, FILIAL, MARGEM, OPORTUNIDADE, APRENDIZADO\n",
    )
    _w(
        "COMMERCIAL_RECOMMENDATION_ENGINE_REPORT.md",
        f"# IA-3 — Recommendation Engine\n\n"
        f"- Total: **{rec.get('total')}**\n"
        f"- Por nível: `{rec.get('byLevel')}`\n",
    )
    _w(
        "COMMERCIAL_ACTION_CENTER_INTEGRATION_REPORT.md",
        f"# IA-4 — Action Center Integration\n\n"
        f"- Abertas: **{ac.get('acoesAbertas')}**\n"
        f"- Executadas: **{ac.get('acoesExecutadas')}**\n"
        f"- Validadas: **{ac.get('acoesValidadas')}**\n"
        f"- ROI real: **{ac.get('acoesComRoiReal')}**\n"
        f"- READ ONLY: **{ac.get('readOnly')}**\n",
    )
    _w(
        "COMMERCIAL_CONVERSATION_LAYER_REPORT.md",
        f"# IA-5 — Conversation Layer\n\n"
        f"- Endpoint: `POST /api/v1/commercial-copilot/ask`\n"
        f"- Perguntas homologadas: **{conv.get('totalHomologadas')}**\n",
    )
    _w(
        "COMMERCIAL_GOVERNANCE_REPORT.md",
        f"# IA-6 — Governance Layer\n\n"
        f"- Lineage obrigatório: **{gov.get('lineageObrigatorio')}**\n"
        f"- Evidence obrigatório: **{gov.get('evidenceObrigatorio')}**\n"
        f"- Cross-tenant: **{gov.get('semCrossTenant')}**\n"
        f"- Trust: **{gov.get('trustExecutivo')}**\n",
    )
    _w(
        "COMMERCIAL_COPILOT_COCKPIT_REPORT.md",
        f"# IA-7 — Cockpit\n\n"
        f"- View: `commercial-copilot`\n"
        f"- API: `/api/v1/commercial-copilot/cockpit`\n",
    )
    _w(
        "DW_COMMERCIAL_COPILOT_MODEL.md",
        f"# IA-8 — DW Model\n\n"
        f"- `fact_commercial_copilot`\n"
        f"- `fact_commercial_questions`\n"
        f"- Lineage: empresaCodigo, questionId, actionId, executionId, outcomeId\n",
    )
    _w(
        "COMMERCIAL_COPILOT_QA_REPORT.md",
        f"# IA-9 — QA Gate\n\n"
        f"- Sem lineage: **{qa.get('zeroRespostaSemLineage')}**\n"
        f"- Sem evidência: **{qa.get('zeroRespostaSemEvidencia')}**\n"
        f"- Sem recomendação inventada: **{qa.get('zeroRecomendacaoInventada')}**\n"
        f"- Sem ROI sem origem: **{qa.get('zeroRoiSemOrigem')}**\n"
        f"- Sem cross-tenant: **{qa.get('semCrossTenant')}**\n"
        f"- Fora catálogo: **{qa.get('zeroRespostaForaCatalogoHomologado')}**\n",
    )

    lines = "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
    _w(
        "F07_9_COMMERCIAL_COPILOT_REPORT.md",
        f"# F07.9 — Commercial Copilot & Executive Advisor\n\n"
        f"Fonte: **{w.get('fonte', {}).get('modo')}** · webPostoLive: **False**\n\n"
        f"## Respostas executivas\n\n{lines}\n\n"
        f"{parecer}\n",
    )


if __name__ == "__main__":
    main()
