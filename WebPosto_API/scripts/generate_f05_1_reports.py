#!/usr/bin/env python3
"""Gera relatórios F05.1 Executive Decision Engine."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f05_1_executive_decision_engine.json"


def _load() -> dict:
    if not AUDIT.exists():
        return {}
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def _write(name: str, body: str) -> None:
    path = ROOT / name
    path.write_text(body, encoding="utf-8")
    print(f"Wrote {path}")


def main() -> None:
    audit = _load()
    w = audit.get("windows", {}).get("7d", {})
    ex = w.get("executiveAnswers") or audit.get("executiveAnswers") or {}
    qa = w.get("qa") or {}
    cockpit = w.get("cockpit") or {}

    _write(
        "OPPORTUNITY_DECISION_ENGINE_REPORT.md",
        f"# Opportunity Decision Engine\n\n"
        f"- Trust Executivo: {ex.get('trustExecutivo')}\n"
        f"- Decisão #1: {ex.get('1_decisaoNumero1', {}).get('acao') if isinstance(ex.get('1_decisaoNumero1'), dict) else ex.get('1_decisaoNumero1')}\n"
        f"- Maior ROI: {ex.get('2_acaoMaiorRoi', {}).get('acao') if isinstance(ex.get('2_acaoMaiorRoi'), dict) else '—'}\n",
    )
    _write(
        "RISK_DECISION_ENGINE_REPORT.md",
        f"# Risk Decision Engine\n\n"
        f"- Estratégias: ACEITAR, MITIGAR, TRANSFERIR, ELIMINAR\n"
        f"- Top riscos no cockpit: {len(cockpit.get('topRiscos') or [])}\n"
        f"- Sem risco sem classificação: {qa.get('semRiscoSemClassificacao')}\n",
    )
    _write(
        "FINANCIAL_ACTION_ENGINE_REPORT.md",
        f"# Financial Action Engine\n\n"
        f"- Plano financeiro consolidado: {ex.get('15_planoFinanceiroConsolidado')}\n"
        f"- Ação reduz perdas: {ex.get('3_acaoReduzPerdas', {}).get('acao') if isinstance(ex.get('3_acaoReduzPerdas'), dict) else '—'}\n"
        f"- Ação aumenta receita: {ex.get('4_acaoAumentaReceita', {}).get('acao') if isinstance(ex.get('4_acaoAumentaReceita'), dict) else '—'}\n",
    )
    _write(
        "PEOPLE_ACTION_ENGINE_REPORT.md",
        f"# People Action Engine\n\n"
        f"- Plano pessoas consolidado: {ex.get('17_planoPessoasConsolidado')}\n"
        f"- Auditoria: {ex.get('8_operadorAuditoria', {}).get('acao') if isinstance(ex.get('8_operadorAuditoria'), dict) else '—'}\n"
        f"- Promoção: {ex.get('9_operadorPromocao', {}).get('acao') if isinstance(ex.get('9_operadorPromocao'), dict) else '—'}\n"
        f"- Bônus: {ex.get('10_operadorBonus', {}).get('acao') if isinstance(ex.get('10_operadorBonus'), dict) else '—'}\n"
        f"- Treinamento: {ex.get('11_operadorTreinamento', {}).get('acao') if isinstance(ex.get('11_operadorTreinamento'), dict) else '—'}\n",
    )
    _write(
        "OPERATIONS_ACTION_ENGINE_REPORT.md",
        f"# Operations Action Engine\n\n"
        f"- Plano operacional consolidado: {ex.get('16_planoOperacionalConsolidado')}\n"
        f"- Filial intervenção: {ex.get('5_filialIntervencaoImediata', {}).get('acao') if isinstance(ex.get('5_filialIntervencaoImediata'), dict) else '—'}\n"
        f"- PDV intervenção: {ex.get('6_pdvIntervencaoImediata', {}).get('acao') if isinstance(ex.get('6_pdvIntervencaoImediata'), dict) else '—'}\n"
        f"- Turno intervenção: {ex.get('7_turnoIntervencao', {}).get('acao') if isinstance(ex.get('7_turnoIntervencao'), dict) else '—'}\n",
    )
    _write(
        "ROI_PRIORITIZATION_REPORT.md",
        f"# ROI Prioritization\n\n"
        f"- Prioridade 1: {(w.get('roiPrioritizationEngine') or {}).get('prioridade1', '—')}\n"
        f"- Total ações: {(w.get('roiPrioritizationEngine') or {}).get('total', '—')}\n"
        f"- Impacto esperado P1: {cockpit.get('impactoEsperado')}\n",
    )
    _write(
        "DECISION_COCKPIT_REPORT.md",
        f"# Decision Cockpit\n\n"
        f"- view=decision-engine\n"
        f"- Top decisões: {len(cockpit.get('topDecisoes') or [])}\n"
        f"- Plano ação: {len(cockpit.get('planoAcao') or [])}\n"
        f"- Corporate Score: {cockpit.get('corporateScore')}\n"
        f"- Executive Score: {cockpit.get('executiveScore')}\n",
    )
    _write(
        "DW_DECISION_ENGINE_MODEL.md",
        "# DW Decision Engine Model\n\n"
        "Tabelas: `fact_decision`, `fact_action`, `fact_roi_priority`, `fact_decision_snapshot`\n\n"
        "Dimensões: `dim_decision`, `dim_action`, `dim_priority`, `dim_owner`\n\n"
        "DDL: `dw/ddl/fact_decision_engine.sql`\n",
    )
    _write(
        "DECISION_ENGINE_QA_REPORT.md",
        f"# Decision Engine QA\n\n"
        f"- Auditável: {qa.get('auditavel')}\n"
        f"- Trust Executivo OK: {qa.get('trustExecutivoOk')} ({qa.get('trustExecutivo')})\n"
        f"- Paridade Δ: {qa.get('paridadeDelta')}\n"
        f"- Sem decisão sem evidência: {qa.get('semDecisaoSemEvidencia')}\n"
        f"- Sem ROI sem cálculo: {qa.get('semRoiSemCalculo')}\n"
        f"- Fonte WebPosto: {qa.get('fonteWebPosto')}\n",
    )
    _write(
        "F05_1_EXECUTIVE_DECISION_ENGINE_REPORT.md",
        f"# F05.1 Executive Decision Engine\n\n"
        f"## Baseline\n\n"
        f"- Trust Executivo: {ex.get('trustExecutivo')}\n"
        f"- Corporate Score: {ex.get('corporateScore')}\n"
        f"- Executive Score: {ex.get('executiveScore')}\n\n"
        f"## Respostas Executivas\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()) if k[0].isdigit())
        + f"\n\n## Parecer\n\n{audit.get('parecerFinal', w.get('parecerFinal', ''))}\n",
    )


if __name__ == "__main__":
    main()
