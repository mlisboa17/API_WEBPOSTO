#!/usr/bin/env python3
"""Gera relatórios F05.3 Executive AI Copilot."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f05_3_executive_ai_copilot.json"


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
    gov = w.get("governanceLayer") or {}
    parecer = w.get("parecerFinal") or data.get("parecerFinal") or ""

    _w(
        "COPILOT_KNOWLEDGE_ENGINE_REPORT.md",
        f"# Copilot Knowledge Engine (F05.3)\n\n"
        f"- Fonte WebPosto: **False**\n"
        f"- Trust Executivo: **{ex.get('trustExecutivo')}**\n"
        f"- Perguntas homologadas: **{ex.get('5_perguntasHomologadas')}**\n",
    )
    _w(
        "EXECUTIVE_REASONING_ENGINE_REPORT.md",
        f"# Executive Reasoning Engine\n\n"
        f"- Responde financeiro: **{ex.get('1_respondeFinanceiro')}**\n"
        f"- Responde pessoas: **{ex.get('2_respondePessoas')}**\n"
        f"- Responde operações: **{ex.get('3_respondeOperacoes')}**\n"
        f"- Responde estratégia: **{ex.get('4_respondeEstrategia')}**\n"
        f"- Lineage completo: **{ex.get('14_lineageCompleto')}**\n"
        f"- Confidence obrigatório: **{ex.get('15_confidenceObrigatorio')}**\n",
    )
    _w(
        "COPILOT_RECOMMENDATION_ENGINE_REPORT.md",
        f"# Copilot Recommendation Engine\n\n"
        f"- Total recomendações: **{ex.get('6_totalRecomendacoes')}**\n"
        f"- Com evidência: **{ex.get('7_recomendacoesComEvidencia')}**\n"
        f"- Proxy: **{ex.get('8_recomendacoesProxy')}**\n"
        f"- ROI realizado citável: **{ex.get('9_roiRealizado')}**\n"
        f"- ROI estimado: **{ex.get('10_roiEstimado')}**\n",
    )
    _w(
        "COPILOT_ACTION_CENTER_INTEGRATION_REPORT.md",
        f"# Action Center Integration\n\n"
        f"- Modo: **READ ONLY**\n"
        f"- Integração F05.2 via snapshot homologado\n",
    )
    _w(
        "COPILOT_CONVERSATION_LAYER_REPORT.md",
        f"# Conversation Layer\n\n"
        f"- Catálogo G02: **10 perguntas**\n"
        f"- Respostas catálogo: **{ex.get('respostasCatalogo')}**\n",
    )
    _w(
        "COPILOT_GOVERNANCE_REPORT.md",
        f"# Copilot Governance\n\n```json\n{json.dumps(gov, ensure_ascii=False, indent=2)}\n```\n",
    )
    _w(
        "COPILOT_COCKPIT_REPORT.md",
        f"# Copilot Cockpit\n\n"
        f"- View: **executive-copilot**\n"
        f"- API: `/api/v1/executive-copilot/cockpit`\n",
    )
    _w(
        "DW_COPILOT_MODEL_REPORT.md",
        f"# DW Copilot Model\n\n"
        f"- `fact_copilot_question`\n"
        f"- `fact_copilot_answer`\n"
        f"- `fact_copilot_recommendation`\n"
        f"- DDL: `dw/ddl/fact_executive_copilot.sql`\n",
    )
    _w(
        "COPILOT_QA_REPORT.md",
        f"# Copilot QA Gate\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| Sem resposta sem evidência | {qa.get('semRespostaSemEvidencia')} |\n"
        f"| Sem resposta sem confidence | {qa.get('semRespostaSemConfidence')} |\n"
        f"| Sem cross-tenant | {qa.get('semCrossTenant')} |\n"
        f"| Sem ROI sem origem | {qa.get('semRoiSemOrigem')} |\n"
        f"| Sem alucinação | {qa.get('semAlucinacao')} |\n\n"
        f"{parecer}\n",
    )
    _w(
        "F05_3_EXECUTIVE_AI_COPILOT_REPORT.md",
        f"# F05.3 — Executive AI Copilot\n\n"
        f"## Respostas executivas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n{parecer}\n",
    )


if __name__ == "__main__":
    main()
