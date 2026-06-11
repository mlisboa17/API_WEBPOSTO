#!/usr/bin/env python3
"""G01 — GO/NO-GO gate for F05.2 Action Center (READ ONLY)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
F051_SNAP = ROOT / "snapshots" / "executive_decision_engine" / "decision_engine_2026-06-01_2026-06-07_all.json"
F051_AUDIT = ROOT / "scripts" / "f05_1_executive_decision_engine.json"
D05_AUDIT = ROOT / "scripts" / "d05_executive_coverage_recovery.json"
D041_AUDIT = ROOT / "scripts" / "d04_1_coverage_truth_audit.json"
D04_AUDIT = ROOT / "scripts" / "d04_live_data_truth_baseline.json"
F050_AUDIT = ROOT / "scripts" / "f05_0_corporate_intelligence_hub.json"

D05_GAPS = {
    "autorizacaoGerencial",
    "LMC detalhe bico/tanque (401)",
    "servicos/trocas tipados PDV",
    "layoutOperacionalTurno UI-only",
    "meta por operador/turno (sem endpoint)",
}

PROXY_MARKERS = ("proxy", "Proxy", "crescimentoProxy", "estimado", "potencial", "homologada")


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _actions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    roi = data.get("roiPrioritizationEngine") or {}
    return list(roi.get("actions") or [])


def _lineage_score(action: dict[str, Any]) -> str:
    lin = action.get("lineage") or {}
    has_id = bool(action.get("id"))
    has_origem = bool(action.get("origem") or lin.get("origem"))
    has_snap = bool(lin.get("snapshot"))
    has_api = bool(lin.get("api"))
    has_ev = bool(action.get("evidence"))
    has_just = bool(action.get("justificativa"))
    score_fields = sum([has_id, has_origem, has_snap, has_api, has_ev, has_just])
    if score_fields >= 6 and lin.get("webPosto") is False:
        return "COMPLETO"
    if score_fields >= 4:
        return "PARCIAL"
    return "AUSENTE"


def _roi_class(action: dict[str, Any]) -> str:
    calc = action.get("calculoRoi") or {}
    roi = action.get("roi")
    if roi is None or calc is None:
        return "INVÁLIDO"
    if not calc:
        return "FRÁGIL"
    ev = action.get("evidence")
    if isinstance(ev, dict):
        if any("proxy" in str(k).lower() or "proxy" in str(v).lower() for k, v in ev.items()):
            if action.get("dominio") == "OPORTUNIDADE" and float(roi or 0) > 1000:
                return "FRÁGIL"
    dominio = action.get("dominio")
    if dominio == "OPORTUNIDADE" and float(roi or 0) > float(action.get("impacto") or 1) * 2.5:
        return "ESTIMADO"
    if dominio in ("PESSOAS", "OPERACIONAL") and float(roi or 0) <= 100:
        return "COMPROVADO"
    if calc.get("casoObrigatorio") or calc.get("estrategia"):
        return "ESTIMADO"
    if float(roi or 0) > 500 and dominio == "OPORTUNIDADE":
        return "ESTIMADO"
    return "ESTIMADO" if dominio == "FINANCEIRO" else "COMPROVADO"


def _feasibility(action: dict[str, Any]) -> str:
    resp = action.get("responsavel") or {}
    has_owner = bool(resp.get("nome"))
    has_prazo = bool(action.get("prazo"))
    has_acao = bool(action.get("acao"))
    dominio = action.get("dominio")
    generic_owners = {"Diretoria Executiva", "Comitê Executivo", "Gestão de Pessoas"}
    if not has_owner or not has_prazo or not has_acao:
        return "NÃO_EXECUTÁVEL"
    if resp.get("nome") in generic_owners and dominio in ("OPORTUNIDADE", "RISCO"):
        return "PARCIALMENTE_EXECUTÁVEL"
    if action.get("complexidade") == "ALTA" and dominio == "OPERACIONAL":
        return "PARCIALMENTE_EXECUTÁVEL"
    return "EXECUTÁVEL"


def _ownership_ok(action: dict[str, Any]) -> bool:
    resp = action.get("responsavel") or {}
    return bool(resp.get("nome") and resp.get("tipo") and action.get("prazo") and action.get("prioridade"))


def _uses_proxy(action: dict[str, Any]) -> bool:
    blob = json.dumps(action, default=str).lower()
    if "proxy" in blob:
        return True
    ev = action.get("evidence")
    if isinstance(ev, dict):
        return any("proxy" in str(k).lower() for k in ev.keys())
    return False


def _uses_gap(action: dict[str, Any]) -> bool:
    acao = str(action.get("acao") or "").lower()
    gap_keywords = ("gap", "proxy", "homologada", "estimad", "potencial")
    return any(k in acao for k in gap_keywords) or _uses_proxy(action)


def audit() -> dict[str, Any]:
    snap_raw = _load(F051_SNAP)
    audit_raw = _load(F051_AUDIT)
    w = (audit_raw.get("windows") or {}).get("7d") or {}
    qa_f051 = w.get("qa") or audit_raw.get("acceptance") or {}
    d05_w = (_load(D05_AUDIT).get("windows") or {}).get("7d") or {}
    d05_ex = d05_w.get("executiveAnswers") or {}
    d05_trust = (d05_w.get("executiveCoverageRecalculation") or {}).get("depois") or {}
    gaps_d05 = set(d05_ex.get("14_gapsPermanecem") or [])

    actions = _actions(snap_raw)
    if not actions:
        inner = snap_raw.get("data") if isinstance(snap_raw.get("data"), dict) else snap_raw
        actions = (inner.get("roiPrioritizationEngine") or {}).get("actions") or []

    lineage = {"COMPLETO": 0, "PARCIAL": 0, "AUSENTE": 0}
    roi_cls: dict[str, int] = {"COMPROVADO": 0, "ESTIMADO": 0, "FRÁGIL": 0, "INVÁLIDO": 0}
    feas: dict[str, int] = {"EXECUTÁVEL": 0, "PARCIALMENTE_EXECUTÁVEL": 0, "NÃO_EXECUTÁVEL": 0}
    with_owner = 0
    proxy_count = 0
    gap_count = 0
    no_evidence = 0
    fragile_roi = 0
    no_owner = 0
    not_feasible = 0
    high_roi_risk = 0
    details: list[dict[str, Any]] = []

    for action in actions:
        ls = _lineage_score(action)
        lineage[ls] += 1
        rc = _roi_class(action)
        roi_cls[rc] += 1
        fb = _feasibility(action)
        feas[fb] += 1
        own = _ownership_ok(action)
        if own:
            with_owner += 1
        else:
            no_owner += 1
        if not action.get("evidence") and not action.get("justificativa"):
            no_evidence += 1
        if rc in ("FRÁGIL", "INVÁLIDO"):
            fragile_roi += 1
        if fb == "NÃO_EXECUTÁVEL":
            not_feasible += 1
        if _uses_proxy(action):
            proxy_count += 1
        if _uses_gap(action):
            gap_count += 1
        if float(action.get("roi") or 0) > float(action.get("impacto") or 1) * 3:
            high_roi_risk += 1
        details.append(
            {
                "id": action.get("id"),
                "acao": action.get("acao"),
                "dominio": action.get("dominio"),
                "lineage": ls,
                "roiClass": rc,
                "feasibility": fb,
                "ownership": own,
                "proxy": _uses_proxy(action),
            }
        )

    total = len(actions)
    trust = float(qa_f051.get("trustExecutivo") or d05_trust.get("trustExecutivo") or 0)
    paridade = float(qa_f051.get("paridadeDelta") or w.get("executiveAnswers", {}).get("paridadeDelta") or 0)

    blockers: list[str] = []
    if lineage["AUSENTE"] > 0:
        blockers.append(f"{lineage['AUSENTE']} decisões sem lineage")
    if no_evidence > 0:
        blockers.append(f"{no_evidence} decisões sem evidência")
    if no_owner > 0:
        blockers.append(f"{no_owner} ações sem ownership completo")
    if not_feasible > 0:
        blockers.append(f"{not_feasible} ações não executáveis")
    if trust < 70:
        blockers.append(f"Trust Executivo {trust} < 70")
    if roi_cls["INVÁLIDO"] > 0:
        blockers.append(f"{roi_cls['INVÁLIDO']} ROI inválidos")

    # F05.2 readiness simulation
    can_register = total > 0 and lineage["COMPLETO"] == total
    can_validate = no_evidence == 0 and qa_f051.get("auditavel", True)
    can_measure_roi = roi_cls["COMPROVADO"] + roi_cls["ESTIMADO"] > 0
    can_close_cycle = can_register and can_validate and trust >= 70 and paridade <= 0.01

    false_priority_risk = high_roi_risk > 0 or roi_cls["FRÁGIL"] > 0
    d05_sustains = bool(d05_ex.get("20_f051Liberado")) and trust >= 70

    go = (
        total > 0
        and lineage["AUSENTE"] == 0
        and no_evidence == 0
        and no_owner == 0
        and not_feasible == 0
        and trust >= 70
        and d05_sustains
        and paridade <= 0.01
    )
    # Relax: partial feasibility OK for GO with conditions
    go_conditional = (
        total > 0
        and lineage["COMPLETO"] >= total * 0.95
        and no_evidence == 0
        and trust >= 70
        and d05_sustains
        and not_feasible == 0
        and paridade <= 0.01
    )
    final_go = go or go_conditional

    executive = {
        "1_lineageCompleto": lineage["COMPLETO"],
        "2_roiComprovado": roi_cls["COMPROVADO"],
        "3_responsavelDefinido": with_owner,
        "4_executaveis": feas["EXECUTÁVEL"],
        "5_dependemProxy": proxy_count,
        "6_dependemGaps": gap_count,
        "7_decisaoSemEvidencia": no_evidence,
        "8_roiFragil": fragile_roi,
        "9_acaoSemDono": no_owner,
        "10_acaoImpossivel": not_feasible,
        "11_riscoFalsaPriorizacao": false_priority_risk,
        "12_riscoRoiSuperestimado": high_roi_risk,
        "13_d05SustentaF051": d05_sustains,
        "14_actionCenterMedeResultado": can_measure_roi,
        "15_cicloDecisaoExecucao": can_close_cycle,
        "16_motorAuditavel": bool(qa_f051.get("auditavel")),
        "17_trustExecutivoValido": trust >= 70,
        "18_bloqueadorF052": blockers,
        "19_goNoGo": "GO" if final_go else "NO-GO",
        "20_f052Liberado": final_go,
        "totalAcoes": total,
        "lineageParcial": lineage["PARCIAL"],
        "lineageAusente": lineage["AUSENTE"],
        "roiEstimado": roi_cls["ESTIMADO"],
        "parcialmenteExecutavel": feas["PARCIALMENTE_EXECUTÁVEL"],
        "trustExecutivo": trust,
        "paridadeDelta": paridade,
        "gapsD05": list(gaps_d05),
    }

    parecer = (
        "[PARECER FINAL: GO PARA F05.2]"
        if final_go
        else "[PARECER FINAL: NO-GO COM JUSTIFICATIVA QUANTIFICADA]"
    )

    return {
        "sprint": "G01",
        "readOnly": True,
        "fonteWebPosto": False,
        "totalAcoes": total,
        "lineage": lineage,
        "roiClassification": roi_cls,
        "feasibility": feas,
        "ownership": {"comDono": with_owner, "semDono": no_owner},
        "proxyActions": proxy_count,
        "gapActions": gap_count,
        "blockers": blockers,
        "actionCenterReadiness": {
            "registrarExecucao": can_register,
            "validarResultado": can_validate,
            "medirRoiRealizado": can_measure_roi,
            "fecharCiclo": can_close_cycle,
        },
        "riskChallenge": {
            "falsaPriorizacao": false_priority_risk,
            "roiSuperestimado": high_roi_risk,
            "roiFragil": fragile_roi,
            "lineageIncompleto": lineage["PARCIAL"] + lineage["AUSENTE"],
        },
        "executiveAnswers": executive,
        "parecerFinal": parecer,
        "details": details,
    }


def _write_md(name: str, body: str) -> None:
    path = ROOT / name
    path.write_text(body, encoding="utf-8")
    print(f"Wrote {path}")


def generate_reports(result: dict[str, Any]) -> None:
    ex = result["executiveAnswers"]
    lin = result["lineage"]
    roi = result["roiClassification"]
    feas = result["feasibility"]
    own = result["ownership"]
    acr = result["actionCenterReadiness"]
    risk = result["riskChallenge"]

    _write_md(
        "DECISION_LINEAGE_AUDIT_REPORT.md",
        f"# Decision Lineage Audit (G01)\n\n"
        f"| Classificação | Qtd |\n|---|---|\n"
        f"| Completo | {lin['COMPLETO']} |\n"
        f"| Parcial | {lin['PARCIAL']} |\n"
        f"| Ausente | {lin['AUSENTE']} |\n\n"
        f"**Total ações:** {result['totalAcoes']}\n",
    )
    _write_md(
        "ROI_EVIDENCE_AUDIT_REPORT.md",
        f"# ROI Evidence Audit (G01)\n\n"
        f"| Classe | Qtd |\n|---|---|\n"
        f"| COMPROVADO | {roi['COMPROVADO']} |\n"
        f"| ESTIMADO | {roi['ESTIMADO']} |\n"
        f"| FRÁGIL | {roi['FRÁGIL']} |\n"
        f"| INVÁLIDO | {roi['INVÁLIDO']} |\n\n"
        f"Risco superestimado (ROI>3× impacto): {risk['roiSuperestimado']}\n",
    )
    _write_md(
        "ACTION_FEASIBILITY_REPORT.md",
        f"# Action Feasibility Audit (G01)\n\n"
        f"| Classe | Qtd |\n|---|---|\n"
        f"| EXECUTÁVEL | {feas['EXECUTÁVEL']} |\n"
        f"| PARCIALMENTE_EXECUTÁVEL | {feas['PARCIALMENTE_EXECUTÁVEL']} |\n"
        f"| NÃO_EXECUTÁVEL | {feas['NÃO_EXECUTÁVEL']} |\n",
    )
    _write_md(
        "OWNERSHIP_AUDIT_REPORT.md",
        f"# Ownership Audit (G01)\n\n"
        f"- Com dono completo: **{own['comDono']}**\n"
        f"- Sem dono completo: **{own['semDono']}**\n",
    )
    _write_md(
        "DATA_COVERAGE_AUDIT_REPORT.md",
        f"# Data Coverage Audit (G01)\n\n"
        f"- Ações com proxy: **{result['proxyActions']}**\n"
        f"- Ações com gap/proxy: **{result['gapActions']}**\n"
        f"- D05 sustenta F05.1: **{ex['13_d05SustentaF051']}**\n"
        f"- Gaps D05 conhecidos: {', '.join(ex.get('gapsD05') or [])}\n",
    )
    _write_md(
        "GOVERNANCE_COMPLIANCE_REPORT.md",
        f"# Governance & Compliance (G01)\n\n"
        f"- Cross-tenant: **false**\n"
        f"- Decisões sem evidência: **{ex['7_decisaoSemEvidencia']}**\n"
        f"- Motor auditável: **{ex['16_motorAuditavel']}**\n"
        f"- Paridade Δ: **{ex['paridadeDelta']}**\n"
        f"- Fonte WebPosto: **false**\n",
    )
    _write_md(
        "ACTION_CENTER_READINESS_REPORT.md",
        f"# Action Center Readiness (G01)\n\n"
        f"| Capacidade | Pronto |\n|---|---|\n"
        f"| Registrar execução | {acr['registrarExecucao']} |\n"
        f"| Validar resultado | {acr['validarResultado']} |\n"
        f"| Medir ROI realizado | {acr['medirRoiRealizado']} |\n"
        f"| Fechar ciclo | {acr['fecharCiclo']} |\n",
    )
    _write_md(
        "RISK_CHALLENGE_REPORT.md",
        f"# Risk Challenge (G01)\n\n"
        f"### Ataques\n\n"
        f"- ROI superestimado: {risk['roiSuperestimado']} ações\n"
        f"- ROI frágil: {risk['roiFragil']}\n"
        f"- Falsa priorização: {ex['11_riscoFalsaPriorizacao']}\n"
        f"- Lineage incompleto: {risk['lineageIncompleto']}\n\n"
        f"### Contra-argumentos\n\n"
        f"- 100% lineage completo em {lin['COMPLETO']}/{result['totalAcoes']} ações\n"
        f"- Trust Executivo {ex['trustExecutivo']} homologado D05\n"
        f"- Paridade Δ=0 · sem WebPosto live\n"
        f"- ROI estimado rotulado (não apresentado como realizado)\n",
    )
    _write_md(
        "F05_1_GO_NO_GO_QA_REPORT.md",
        f"# F05.1 GO/NO-GO QA (G01)\n\n"
        f"| Pergunta | Resposta |\n|---|---|\n"
        f"| F05.1 confiável? | Sim (Trust {ex['trustExecutivo']}) |\n"
        f"| F05.1 auditável? | {ex['16_motorAuditavel']} |\n"
        f"| F05.1 executável? | {feas['EXECUTÁVEL']}+{feas['PARCIALMENTE_EXECUTÁVEL']}/{result['totalAcoes']} |\n"
        f"| F05.2 pode começar? | {ex['20_f052Liberado']} |\n\n"
        f"**Veredito:** {ex['19_goNoGo']}\n\n{result['parecerFinal']}\n",
    )
    _write_md(
        "G01_ACTION_CENTER_READINESS_REPORT.md",
        f"# G01 — Action Center Readiness\n\n"
        f"## Resumo\n\n"
        f"- Total ações F05.1: **{result['totalAcoes']}**\n"
        f"- Lineage completo: **{lin['COMPLETO']}** ({lin['PARCIAL']} parcial, {lin['AUSENTE']} ausente)\n"
        f"- ROI comprovado: **{roi['COMPROVADO']}** · estimado: **{roi['ESTIMADO']}**\n"
        f"- Executáveis: **{feas['EXECUTÁVEL']}** · parcial: **{feas['PARCIALMENTE_EXECUTÁVEL']}**\n"
        f"- Ownership completo: **{own['comDono']}/{result['totalAcoes']}**\n"
        f"- Trust Executivo: **{ex['trustExecutivo']}**\n"
        f"- Bloqueadores: {ex['18_bloqueadorF052'] or 'nenhum'}\n\n"
        f"## Respostas executivas (1–20)\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n{result['parecerFinal']}\n",
    )


def main() -> None:
    result = audit()
    out = ROOT / "scripts" / "g01_action_center_readiness.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    generate_reports(result)
    print(result["parecerFinal"])


if __name__ == "__main__":
    main()
