#!/usr/bin/env python3
"""Gera relatórios F07.7 Commercial Execution & Outcome Tracking."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f07_7_commercial_execution.json"


def _load() -> dict:
    if not AUDIT.exists():
        raise SystemExit(f"Execute primeiro: python scripts/audit_f07_7_commercial_execution.py\nArquivo ausente: {AUDIT}")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def _w(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def main() -> None:
    data = _load()
    w = data.get("windows", {}).get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    assign = w.get("commercialAssignmentEngine") or {}
    tracking = w.get("commercialExecutionTracking") or {}
    evidence = w.get("commercialEvidenceEngine") or {}
    outcome = w.get("commercialOutcomeMeasurement") or {}
    revenue = w.get("revenueLiftTracking") or {}
    margin = w.get("marginImprovementTracking") or {}
    performance = w.get("commercialPerformance") or {}
    qa = w.get("qa") or {}
    parecer = w.get("parecerFinal") or ""

    _w(
        "COMMERCIAL_ASSIGNMENT_ENGINE_REPORT.md",
        f"# IA-1 — Assignment Engine\n\n"
        f"- Total atribuídas: **{assign.get('totalAtribuidas')}**\n"
        f"- Por status: `{assign.get('porStatus')}`\n"
        f"- Lineage: assignment_engine F07.7\n",
    )
    _w(
        "COMMERCIAL_EXECUTION_TRACKING_REPORT.md",
        f"# IA-2 — Execution Tracking\n\n"
        f"- Eventos: **{tracking.get('totalEventos')}**\n"
        f"- Executadas: **{tracking.get('executadas')}**\n",
    )
    _w(
        "COMMERCIAL_EVIDENCE_REPORT.md",
        f"# IA-3 — Evidence Engine\n\n"
        f"- Evidências: **{evidence.get('total')}**\n"
        f"- Regra: VALIDADA exige evidência — **{qa.get('zeroValidadaSemEvidencia')}**\n",
    )
    _w(
        "COMMERCIAL_OUTCOME_MEASUREMENT_REPORT.md",
        f"# IA-4 — Outcome Measurement\n\n"
        f"- Receita antes: **R$ {outcome.get('antes', {}).get('receitaProdutosVendidos')}**\n"
        f"- Receita depois: **R$ {outcome.get('depois', {}).get('receitaProdutosVendidos')}**\n"
        f"- Delta receita: **R$ {outcome.get('delta', {}).get('receita')}**\n"
        f"- Delta margem: **R$ {outcome.get('delta', {}).get('margem')}**\n",
    )
    _w(
        "REVENUE_LIFT_TRACKING_REPORT.md",
        f"# IA-5 — Revenue Lift Tracking\n\n"
        f"- Receita prevista: **R$ {revenue.get('receitaPrevista')}**\n"
        f"- Receita realizada: **R$ {revenue.get('receitaRealizada')}**\n"
        f"- Delta: **R$ {revenue.get('deltaReceita')}**\n"
        f"- Acurácia média: **{revenue.get('acuraciaMediaPct')}%**\n",
    )
    _w(
        "MARGIN_IMPROVEMENT_TRACKING_REPORT.md",
        f"# IA-6 — Margin Improvement Tracking\n\n"
        f"- Margem prevista: **R$ {margin.get('margemPrevista')}**\n"
        f"- Margem realizada: **R$ {margin.get('margemRealizada')}**\n"
        f"- Delta: **R$ {margin.get('deltaMargem')}**\n"
        f"- Produtos impactados: **{margin.get('produtosImpactados')}**\n",
    )
    _w(
        "COMMERCIAL_PERFORMANCE_REPORT.md",
        f"# IA-7 — Commercial Performance\n\n"
        f"- Melhor responsável: **{(performance.get('melhorResponsavel') or {}).get('responsavel')}**\n"
        f"- Melhor filial: **{(performance.get('melhorFilial') or {}).get('empresaCodigo')}**\n"
        f"- Filiais sem execução: **{len(performance.get('filiaisSemExecucao') or [])}**\n",
    )
    _w(
        "COMMERCIAL_EXECUTION_COCKPIT_REPORT.md",
        f"# IA-8 — Cockpit\n\n"
        f"- View: `commercial-execution`\n"
        f"- API: `/api/v1/commercial-execution/cockpit`\n"
        f"- Ações validadas cockpit: **{(w.get('cockpit') or {}).get('acoesValidadas')}**\n",
    )
    _w(
        "DW_COMMERCIAL_EXECUTION_MODEL.md",
        f"# IA-8 — DW Commercial Execution\n\n"
        f"- `dw/ddl/fact_commercial_execution.sql`\n"
        f"- `dw/ddl/fact_commercial_outcome.sql`\n"
        f"- Facts exportados: **{len((w.get('dwLayer') or {}).get('factCommercialExecution') or [])}** execuções\n",
    )
    _w(
        "COMMERCIAL_EXECUTION_QA_REPORT.md",
        f"# IA-9 — QA Gate\n\n"
        f"- 0 ação sem responsável: **{qa.get('zeroAcaoSemResponsavel')}**\n"
        f"- 0 validada sem evidência: **{qa.get('zeroValidadaSemEvidencia')}**\n"
        f"- 0 ROI real sem execução: **{qa.get('zeroRoiRealSemExecucao')}**\n"
        f"- Sem cross-tenant: **{qa.get('semCrossTenantLogico')}**\n"
        f"- Sem KPI sem lineage: **{qa.get('semKpiSemLineage')}**\n"
        f"- Motor auditável: **{qa.get('motorAuditavel')}**\n",
    )
    ex_lines = "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
    _w(
        "F07_7_COMMERCIAL_EXECUTION_AND_OUTCOME_TRACKING_REPORT.md",
        f"# F07.7 — Commercial Execution & Outcome Tracking\n\n"
        f"Fonte: **{w.get('fonte', {}).get('modo')}** · webPostoLive: **{w.get('fonte', {}).get('webPostoLive')}**\n\n"
        f"## Respostas executivas 1–20\n\n{ex_lines}\n\n"
        f"## Ciclo fechado\n\n"
        f"Execution → Evidence → Outcome → ROI Real: **{ex.get('19_cicloComercialFechado')}**\n\n"
        f"{parecer}\n",
    )


if __name__ == "__main__":
    main()
