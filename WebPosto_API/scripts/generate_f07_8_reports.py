#!/usr/bin/env python3
"""Gera relatórios F07.8 Commercial Learning & Recommendation Calibration."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f07_8_commercial_learning.json"


def _load() -> dict:
    if not AUDIT.exists():
        raise SystemExit(f"Execute primeiro: python scripts/audit_f07_8_commercial_learning.py\nArquivo ausente: {AUDIT}")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def _w(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def main() -> None:
    data = _load()
    w = data.get("windows", {}).get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    eff = w.get("recommendationEffectivenessEngine") or {}
    resp = w.get("responsiblePerformanceEngine") or {}
    branch = w.get("branchLearningEngine") or {}
    cal = w.get("recommendationCalibrationEngine") or {}
    ol = w.get("outcomeLearningEngine") or {}
    exec_rep = w.get("executiveLearningReport") or {}
    qa = w.get("qa") or {}
    parecer = w.get("parecerFinal") or ""

    _w(
        "COMMERCIAL_LEARNING_ENGINE_REPORT.md",
        f"# IA-1 — Commercial Learning Engine\n\n"
        f"- Tipos avaliados: **{eff.get('totalTipos')}**\n"
        f"- Fonte: **{w.get('fonte', {}).get('modo')}**\n"
        f"- webPostoLive: **{w.get('fonte', {}).get('webPostoLive')}**\n",
    )
    _w(
        "RECOMMENDATION_EFFECTIVENESS_REPORT.md",
        f"# IA-1 — Recommendation Effectiveness\n\n"
        f"- Tipos: **{eff.get('totalTipos')}**\n"
        f"- Top tipo ROI: **{(eff.get('porTipo') or [{}])[0].get('tipo') if eff.get('porTipo') else '—'}**\n",
    )
    _w(
        "RESPONSIBLE_PERFORMANCE_REPORT.md",
        f"# IA-2 — Responsible Performance\n\n"
        f"- Melhor responsável: **{(resp.get('melhorResponsavel') or {}).get('responsavel')}**\n"
        f"- Ranking: **{len(resp.get('porResponsavel') or [])}** responsáveis\n",
    )
    _w(
        "BRANCH_LEARNING_REPORT.md",
        f"# IA-3 — Branch Learning\n\n"
        f"- Melhor filial: **{(branch.get('melhorFilial') or {}).get('empresaCodigo')}**\n"
        f"- Filiais sem execução: **{len(branch.get('filiaisSemExecucao') or [])}**\n",
    )
    _w(
        "RECOMMENDATION_CALIBRATION_REPORT.md",
        f"# IA-4 — Recommendation Calibration\n\n"
        f"- Calibradas: **{cal.get('totalCalibradas')}**\n"
        f"- Erro médio: **{cal.get('erroMedioPct')}%**\n"
        f"- Distribuição: `{exec_rep.get('confidenceDistribuicao')}`\n",
    )
    _w(
        "OUTCOME_LEARNING_REPORT.md",
        f"# IA-5 — Outcome Learning\n\n"
        f"- Sistema aprendendo: **{ol.get('sistemaAprendendo')}**\n"
        f"- Acurácia média: **{ol.get('acuraciaMediaPct')}%**\n"
        f"- Melhora ao longo do tempo: **{ol.get('melhoraAoLongoDoTempoPct')}%**\n",
    )
    _w(
        "COMMERCIAL_LEARNING_COCKPIT_REPORT.md",
        f"# IA-7 — Cockpit\n\n"
        f"- View: `commercial-learning`\n"
        f"- API: `/api/v1/commercial-learning/cockpit`\n",
    )
    _w(
        "COMMERCIAL_LEARNING_QA_REPORT.md",
        f"# IA-9 — QA Gate\n\n"
        f"- Sem lineage: **{qa.get('zeroAcaoSemLineage')}**\n"
        f"- Sem aprendizado sem evidência: **{qa.get('zeroAprendizadoSemEvidencia')}**\n"
        f"- Sem ROI sem origem: **{qa.get('zeroRoiSemOrigem')}**\n"
        f"- Sem recomendação inventada: **{qa.get('zeroRecomendacaoInventada')}**\n"
        f"- Motor auditável: **{qa.get('motorAuditavel')}**\n",
    )
    ex_lines = "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
    _w(
        "F07_8_COMMERCIAL_LEARNING_REPORT.md",
        f"# F07.8 — Commercial Learning & Recommendation Calibration\n\n"
        f"Fonte: **{w.get('fonte', {}).get('modo')}** · webPostoLive: **{w.get('fonte', {}).get('webPostoLive')}**\n\n"
        f"## Respostas executivas 1–20\n\n{ex_lines}\n\n"
        f"## Aprendizado observável\n\n"
        f"Sistema aprendeu: **{ex.get('17_sistemaAprendeu')}**\n\n"
        f"{parecer}\n",
    )


if __name__ == "__main__":
    main()
