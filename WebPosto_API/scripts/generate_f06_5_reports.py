#!/usr/bin/env python3
"""Gera relatórios F06.5 Fuel Governance."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f06_5_fuel_governance_and_lmc_compliance.json"


def _load() -> dict:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def _w(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def main() -> None:
    data = _load()
    w = data.get("windows", {}).get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    qa = w.get("qa") or {}
    comp = w.get("lmcComplianceAudit") or {}
    routine = w.get("routineAdherenceAudit") or {}
    disc = w.get("operationalDisciplineAudit") or {}
    delay = w.get("delayAnalysisEngine") or {}
    rank = w.get("branchComplianceRanking") or {}
    intel = w.get("fuelGovernanceIntelligence") or {}
    cockpit = w.get("cockpit") or {}
    parecer = w.get("parecerFinal") or ""

    _w(
        "LMC_COMPLIANCE_AUDIT_REPORT.md",
        f"# LMC Compliance Audit\n\n"
        f"- Classificação: **{comp.get('classificacaoGeral')}**\n"
        f"- Dias com LMC: **{comp.get('diasComLmc')}**\n"
        f"- Dias sem LMC: **{comp.get('diasSemLmc')}**\n"
        f"- Branch-days com LMC: **{comp.get('branchDaysWithLmc')}** / **{comp.get('branchDaysExpected')}**\n"
        f"- Taxa conformidade: **{comp.get('taxaConformidadePct')}%**\n",
    )
    _w(
        "ROUTINE_ADHERENCE_REPORT.md",
        f"# Routine Adherence\n\n"
        f"- Periodicidade: **{routine.get('periodicidade')}**\n"
        f"- Rotina diária: **{routine.get('rotinaDiaria')}**\n"
        f"- Regularidade: **{routine.get('regularidadePct')}%**\n"
        f"- Lacunas consecutivas: **{routine.get('lacunasConsecutivas')}**\n",
    )
    fil_rows = "\n".join(
        f"| {f.get('empresaCodigo')} | {f.get('disciplina')} | {f.get('conformidadePct')}% | {', '.join(f.get('preenchidoPor') or [])} |"
        for f in (disc.get("filiais") or [])
    )
    _w(
        "OPERATIONAL_DISCIPLINE_REPORT.md",
        f"# Operational Discipline\n\n| Filial | Disciplina | Conformidade | Preenche |\n|---|---|---|---|\n{fil_rows}\n",
    )
    _w(
        "LMC_DELAY_ANALYSIS_REPORT.md",
        f"# LMC Delay Analysis\n\n"
        f"- Média atraso: **{delay.get('mediaAtrasoDias')} dias**\n"
        f"- Maior atraso: **{delay.get('maiorAtrasoDias')} dias**\n"
        f"- Menor atraso: **{delay.get('menorAtrasoDias')} dias**\n"
        f"- Retroativo: **{delay.get('lmcRetroativo')}** ({delay.get('registrosRetroativos')} registros)\n"
        f"- Acúmulo operacional: **{delay.get('lmcAcumulado')}**\n",
    )
    rank_rows = "\n".join(
        f"| #{r.get('rank')} | {r.get('empresaCodigo')} | {r.get('conformidadePct')}% | {r.get('disciplina')} |"
        for r in (rank.get("ranking") or [])
    )
    _w(
        "BRANCH_COMPLIANCE_RANKING_REPORT.md",
        f"# Branch Compliance Ranking\n\n| Rank | Filial | Conformidade | Disciplina |\n|---|---|---|---|\n{rank_rows}\n",
    )
    causa_rows = "\n".join(f"- **{c.get('causa')}**: {c.get('pesoPct')}% — {c.get('evidencia')}" for c in (intel.get("causasQuantificadas") or []))
    _w(
        "FUEL_GOVERNANCE_INTELLIGENCE_REPORT.md",
        f"# Fuel Governance Intelligence\n\n"
        f"- Problema principal: **{intel.get('problemaPrincipal')}**\n"
        f"- Falta rotina: **{intel.get('problemaFaltaRotina')}**\n"
        f"- Falta processo: **{intel.get('problemaFaltaProcesso')}**\n"
        f"- Tecnologia vs rotina: **{intel.get('tecnologiaVsRotina')}**\n"
        f"- Sem fraude presumida: **{intel.get('semFraudePresumida')}**\n\n"
        f"## Causas quantificadas\n\n{causa_rows}\n",
    )
    _w(
        "FUEL_GOVERNANCE_COCKPIT_REPORT.md",
        f"# Fuel Governance Cockpit\n\n"
        f"- View: **`fuel-governance`**\n"
        f"- API: `/api/v1/fuel-governance/cockpit`\n"
        f"- Conformidade: **{cockpit.get('conformidadeLmc')}** ({cockpit.get('taxaConformidadePct')}%)\n"
        f"- Periodicidade: **{cockpit.get('periodicidade')}**\n",
    )
    _w(
        "DW_FUEL_GOVERNANCE_MODEL.md",
        f"# DW Fuel Governance\n\n"
        f"- `fact_lmc_compliance`\n"
        f"- `fact_lmc_delay`\n"
        f"- `fact_fuel_governance`\n"
        f"- `fact_branch_compliance`\n"
        f"- DDL: `dw/ddl/fact_fuel_governance.sql`\n",
    )
    _w(
        "FUEL_GOVERNANCE_QA_REPORT.md",
        f"# Fuel Governance QA\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| READ ONLY | {qa.get('readOnly')} |\n"
        f"| Sem fraude presumida | {qa.get('semFraudePresumida')} |\n"
        f"| Sem perdas presumidas | {qa.get('semPerdasPresumidas')} |\n"
        f"| Sem score executivo | {qa.get('semScoreExecutivoNovo')} |\n"
        f"| Sem IA autônoma | {qa.get('semIaAutonoma')} |\n"
        f"| Motor auditável | {qa.get('motorAuditavel')} |\n\n"
        f"{parecer}\n",
    )
    _w(
        "F06_5_FUEL_GOVERNANCE_AND_LMC_COMPLIANCE_REPORT.md",
        f"# F06.5 — Fuel Governance & LMC Compliance\n\n"
        f"## Respostas executivas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n## Processo operacional suficiente para conciliação\n\n"
        f"**{w.get('processoOperacionalSuficiente')}** (conformidade {comp.get('taxaConformidadePct')}%)\n\n"
        f"{parecer}\n",
    )


if __name__ == "__main__":
    main()
