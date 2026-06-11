#!/usr/bin/env python3
"""Gera relatórios F05.2 Action Center."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f05_2_action_center.json"


def _load() -> dict:
    return json.loads(AUDIT.read_text(encoding="utf-8")) if AUDIT.exists() else {}


def _w(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def main() -> None:
    audit = _load()
    w = audit.get("windows", {}).get("7d", {})
    ex = w.get("executiveAnswers") or audit.get("executiveAnswers") or {}
    qa = w.get("qa") or {}
    tr = w.get("executionTrackingEngine") or {}
    roi = w.get("roiRealizationEngine") or {}

    _w("ACTION_LIFECYCLE_REPORT.md", f"# Action Lifecycle\n\nEstados: RECOMENDADA→VALIDADA\n\nPor status: {tr.get('porStatus')}\n")
    _w("ACTION_OWNERSHIP_REPORT.md", f"# Action Ownership\n\nDono nominal: **{ex.get('2_donoNominal')}/{ex.get('1_totalAcoes')}**\n")
    _w("ACTION_EXECUTION_TRACKING_REPORT.md", f"# Execution Tracking\n\n{json.dumps(tr, ensure_ascii=False, indent=2)}\n")
    _w("ACTION_EVIDENCE_REPORT.md", f"# Action Evidence\n\nSem evidência execução: **{ex.get('4_semEvidenciaExecucao')}**\nValidadas sem evidência (QA): **{qa.get('validadasSemEvidencia', 0)}**\n")
    _w("ROI_REALIZATION_REPORT.md", f"# ROI Realization\n\nEsperado: {ex.get('7_roiEsperado')}\nRealizado: {ex.get('8_roiRealizado')}\nDelta: {ex.get('9_deltaRoi')}\n")
    _w("ACTION_ESCALATION_REPORT.md", f"# Action Escalation\n\nEscalonadas: **{len((w.get('cockpit') or {}).get('vencidas') or [])}**\n")
    _w("ACTION_CENTER_COCKPIT_REPORT.md", f"# Action Center Cockpit\n\nview=action-center\nTotal: {ex.get('1_totalAcoes')}\n")
    _w("DW_ACTION_CENTER_MODEL.md", "# DW Action Center\n\n`fact_action`, `fact_action_status`, `fact_action_evidence`, `fact_action_roi`\n\nDDL: `dw/ddl/fact_action_center.sql`\n")
    _w("ACTION_CENTER_QA_REPORT.md", f"# Action Center QA\n\n{json.dumps(qa, ensure_ascii=False, indent=2)}\n\n{audit.get('parecerFinal', '')}\n")
    _w(
        "F05_2_ACTION_CENTER_REPORT.md",
        f"# F05.2 Action Center\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()) if str(k)[0].isdigit())
        + f"\n\n{audit.get('parecerFinal', w.get('parecerFinal', ''))}\n",
    )


if __name__ == "__main__":
    main()
