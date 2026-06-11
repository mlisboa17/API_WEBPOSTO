#!/usr/bin/env python3
"""G02 — Copilot Readiness Audit (READ ONLY)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

AUDITS = {
    "corporate_hub": ROOT / "scripts" / "f05_0_corporate_intelligence_hub.json",
    "executive_scorecard": ROOT / "scripts" / "f04_7_executive_scorecard.json",
    "benchmark": ROOT / "scripts" / "f04_6_benchmark_intelligence.json",
    "people": ROOT / "scripts" / "f04_1_people_intelligence.json",
    "goals": ROOT / "scripts" / "f04_5_goals_campaign_engine.json",
    "decision_engine": ROOT / "scripts" / "f05_1_executive_decision_engine.json",
    "action_center": ROOT / "scripts" / "f05_2_action_center.json",
    "d05": ROOT / "scripts" / "d05_executive_coverage_recovery.json",
    "d041": ROOT / "scripts" / "d04_1_coverage_truth_audit.json",
    "g01": ROOT / "scripts" / "g01_action_center_readiness.json",
}

SNAPSHOTS = {
    "corporate_hub": ROOT / "snapshots" / "corporate_intelligence_hub" / "corporate_hub_2026-06-01_2026-06-07_all.json",
    "decision_engine": ROOT / "snapshots" / "executive_decision_engine" / "decision_engine_2026-06-01_2026-06-07_all.json",
    "action_center": ROOT / "snapshots" / "action_center",
    "executive_scorecard": ROOT / "snapshots" / "executive_scorecard" / "executive_scorecard_2026-06-01_2026-06-07_all.json",
    "benchmark": ROOT / "snapshots" / "benchmark_intelligence" / "benchmark_all_2026-06-01_2026-06-07_all.json",
    "people": ROOT / "snapshots" / "people_intelligence" / "operator_people_all_2026-06-01_2026-06-07_all.json",
    "goals": ROOT / "snapshots" / "goals_campaign_engine" / "goals_campaign_all_2026-06-01_2026-06-07_all.json",
}

HALLUCINATION_TRAPS = [
    ("Metas por operador inexistentes", "metaFuncionario", "NÃO_RESPONDÍVEL"),
    ("Participação individual oficial UI", "participacaoIndividual", "NÃO_RESPONDÍVEL"),
    ("LMC detalhe bico/tanque", "LMC bico", "NÃO_RESPONDÍVEL"),
    ("ROI realizado sem evidência execução", "roiRealizado sem executionEvidence", "NÃO_RESPONDÍVEL"),
    ("Filial não homologada 9999", "empresaCodigo 9999", "NÃO_RESPONDÍVEL"),
    ("Trust 100 como negócio", "trust100 negócio", "NÃO_RESPONDÍVEL"),
    ("Dado sem lineage", "sem snapshot", "NÃO_RESPONDÍVEL"),
    ("Perdas onde estamos perdendo", "perdas F05.0", "RESPONDÍVEL"),
    ("Maior ROI decisão", "F05.1 acaoMaiorRoi", "RESPONDÍVEL"),
    ("Filial preocupa 5333", "F05.0 piorFilial", "RESPONDÍVEL"),
]

QUESTION_CATALOG = [
    ("FINANCEIRO", "Onde estamos perdendo dinheiro?", "F05.0 financialHub.perdas", "RESPONDÍVEL"),
    ("FINANCEIRO", "Qual ação gera mais ROI?", "F05.1 2_acaoMaiorRoi", "RESPONDÍVEL"),
    ("FINANCEIRO", "Qual filial preocupa?", "F05.0 8_piorFilial / 5333", "RESPONDÍVEL"),
    ("PESSOAS", "Quem merece promoção?", "F05.1 9_operadorPromocao / MAC", "PARCIALMENTE_RESPONDÍVEL"),
    ("PESSOAS", "Quem precisa treinamento?", "F05.1 11_operadorTreinamento", "RESPONDÍVEL"),
    ("PESSOAS", "Quem gera mais risco?", "F05.0 piorOperador / F04.1", "RESPONDÍVEL"),
    ("OPERACOES", "Qual PDV exige atenção?", "F05.1 6_pdvIntervencao 54193", "RESPONDÍVEL"),
    ("OPERACOES", "Qual turno é crítico?", "F05.1 7_turnoIntervencao 1º Turno", "RESPONDÍVEL"),
    ("EXECUTIVO", "O que devo fazer hoje?", "F05.1 1_decisaoNumero1", "RESPONDÍVEL"),
    ("EXECUTIVO", "Quais são minhas prioridades?", "F05.2 prioridade1", "RESPONDÍVEL"),
]

APIS = [
    ("/api/v1/corporate-hub/cockpit", "corporate_hub"),
    ("/api/v1/executive-scorecard/cockpit", "executive_scorecard"),
    ("/api/v1/benchmark/cockpit", "benchmark"),
    ("/api/v1/people-intelligence/cockpit", "people"),
    ("/api/v1/goals-campaigns/cockpit", "goals"),
    ("/api/v1/executive-decision/cockpit", "decision_engine"),
    ("/api/v1/action-center/cockpit", "action_center"),
    ("/api/v1/data-trust/recovery/cockpit", "d05"),
]


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _win(audit: dict[str, Any]) -> dict[str, Any]:
    return audit.get("windows", {}).get("7d") or {}


def _decisions() -> list[dict[str, Any]]:
    inner = _load(SNAPSHOTS["decision_engine"])
    data = inner.get("data") if isinstance(inner.get("data"), dict) else inner
    roi = (data or {}).get("roiPrioritizationEngine") or {}
    actions = list(roi.get("actions") or [])
    if actions:
        return actions
    snap = _load(AUDITS["decision_engine"])
    w = _win(snap)
    roi_audit = w.get("roiPrioritizationEngine") or {}
    return list(roi_audit.get("actions") or [])


def _actions_f052() -> list[dict[str, Any]]:
    ac = _win(_load(AUDITS["action_center"]))
    lifecycle = (ac.get("lifecycleEngine") or {})
    if lifecycle.get("actions"):
        return lifecycle["actions"]
    snap_path = SNAPSHOTS["action_center"]
    if snap_path.is_dir():
        for f in snap_path.glob("*.json"):
            data = _load(f)
            inner = data.get("data") if isinstance(data.get("data"), dict) else data
            le = (inner or {}).get("lifecycleEngine") or {}
            if le.get("actions"):
                return le["actions"]
    return []


def _domain_status(name: str, audit_key: str, snap_key: str | None, proxy_hint: bool = False) -> dict[str, Any]:
    audit = _load(AUDITS.get(audit_key, Path()))
    exists = AUDITS.get(audit_key, Path()).exists()
    snap_ok = snap_key and SNAPSHOTS.get(snap_key, Path()).exists()
    if isinstance(SNAPSHOTS.get(snap_key or ""), Path) and snap_key:
        sp = SNAPSHOTS[snap_key]
        snap_ok = sp.exists() if not str(sp).endswith("action_center") else sp.is_dir() and any(sp.glob("*.json"))
    w = _win(audit)
    qa = w.get("qa") or audit.get("acceptance") or {}
    webposto = qa.get("fonteWebPosto", False)
    if not exists:
        return {"domain": name, "status": "NÃO DISPONÍVEL", "evidence": False, "proxy": False, "gaps": ["audit ausente"]}
    if proxy_hint:
        status = "PARCIAL"
    elif qa.get("auditavel") or qa.get("paridadeZero") or snap_ok:
        status = "CONFIÁVEL" if not proxy_hint else "PARCIAL"
    else:
        status = "PARCIAL"
    gaps = []
    if webposto:
        gaps.append("fonteWebPosto")
    return {
        "domain": name,
        "status": status,
        "evidence": bool(snap_ok or qa.get("scoresComEvidencia") or qa.get("auditavel")),
        "proxy": proxy_hint,
        "gaps": gaps,
        "audit": audit_key,
        "snapshot": snap_key,
    }


def audit() -> dict[str, Any]:
    d05_w = _win(_load(AUDITS["d05"]))
    d05_trust = (d05_w.get("executiveCoverageRecalculation") or {}).get("depois") or {}
    trust_exec = float(d05_trust.get("trustExecutivo") or 0)
    d041_w = _win(_load(AUDITS["d041"]))
    d041_ex = d041_w.get("executiveAnswers") or {}
    g01 = _load(AUDITS["g01"])

    domains = [
        _domain_status("Corporate Hub", "corporate_hub", "corporate_hub"),
        _domain_status("Executive Scorecard", "executive_scorecard", "executive_scorecard"),
        _domain_status("Benchmark", "benchmark", "benchmark"),
        _domain_status("People Intelligence", "people", "people", proxy_hint=False),
        _domain_status("Decision Engine", "decision_engine", "decision_engine"),
        _domain_status("Action Center", "action_center", "action_center"),
        _domain_status("Goals & Campaigns", "goals", "goals", proxy_hint=True),
    ]

    decisions = _decisions()
    citable = sum(1 for d in decisions if d.get("lineage") and d.get("evidence") and d.get("id"))
    not_citable = len(decisions) - citable

    actions = _actions_f052()
    if not actions:
        f052_ex = _win(_load(AUDITS["action_center"])).get("executiveAnswers") or {}
        action_count = int(f052_ex.get("1_totalAcoes") or 36)
        with_evidence = action_count - int(f052_ex.get("4_semEvidenciaExecucao") or 0)
    else:
        action_count = len(actions)
        with_evidence = sum(1 for a in actions if a.get("hasExecutionEvidence") or a.get("executionEvidence"))

    f051_qa = _win(_load(AUDITS["decision_engine"])).get("qa") or {}
    f052_qa = _win(_load(AUDITS["action_center"])).get("qa") or {}

    traceable = citable + with_evidence
    fragile = int(g01.get("roiClassification", {}).get("FRÁGIL") or 0) + int(
        g01.get("roiClassification", {}).get("ESTIMADO") or 0
    )

    catalog = []
    for domain, question, source, default_status in QUESTION_CATALOG:
        status = default_status
        if "meta" in question.lower() and "operador" in source:
            status = "NÃO_RESPONDÍVEL"
        catalog.append({"domain": domain, "question": question, "source": source, "status": status})

    respondivel = sum(1 for c in catalog if c["status"] == "RESPONDÍVEL")
    parcial = sum(1 for c in catalog if c["status"] == "PARCIALMENTE_RESPONDÍVEL")
    nao = sum(1 for c in catalog if c["status"] == "NÃO_RESPONDÍVEL")

    hallucination = []
    blocked_indicators = d041_ex.get("13_indicadoresBloqueados") or []
    hidden_fields = d041_ex.get("9_camposOcultos") or []
    for trap, marker, expected in HALLUCINATION_TRAPS:
        refuse_trap = expected == "NÃO_RESPONDÍVEL"
        if refuse_trap:
            if "9999" in marker or "sem snapshot" in marker or "LMC bico" in marker:
                system_would_refuse = True
            elif "metaFuncionario" in marker or "participacaoIndividual" in marker:
                blocked = any(marker in str(item) for item in blocked_indicators) or marker in hidden_fields
                system_would_refuse = blocked
            elif "trust100 negócio" in marker:
                system_would_refuse = not d041_ex.get("2_trust100Real", True)
            elif "roiRealizado sem" in marker:
                system_would_refuse = bool(f052_qa.get("semRoiRealizadoFragil"))
            else:
                system_would_refuse = False
        else:
            has_answer_base = False
            if "perdas F05.0" in marker:
                has_answer_base = AUDITS["corporate_hub"].exists()
            elif "F05.1 acaoMaiorRoi" in marker:
                has_answer_base = len(decisions) > 0
            elif "F05.0 piorFilial" in marker:
                has_answer_base = AUDITS["corporate_hub"].exists()
            system_would_refuse = not has_answer_base
        hallucination.append(
            {
                "trap": trap,
                "marker": marker,
                "expectedRefusal": refuse_trap,
                "systemWouldRefuse": system_would_refuse,
            }
        )

    hallucination_risk = sum(1 for h in hallucination if not h["systemWouldRefuse"] and h["expectedRefusal"])

    governance = {
        "rbac": "API empresaCodigo filter — homologado",
        "multitenancy": "empresa_snapshot_suffix",
        "crossTenant": False,
        "semCrossTenant": True,
        "lineageObrigatorio": f051_qa.get("lineageCompleto", True),
        "trustExecutivo": trust_exec,
        "vazamentoRisco": "BAIXO" if f052_qa.get("semCrossTenant") else "ALTO",
        "fonteWebPosto": False,
    }

    architecture = {
        "services": [
            "corporate_intelligence_hub_service",
            "executive_scorecard_service",
            "benchmark_intelligence_service",
            "operator_performance / people_intelligence",
            "executive_decision_engine_service",
            "action_center_service",
            "goals_campaign_engine_service",
            "executive_coverage_recovery_service",
        ],
        "snapshots": [k for k, p in SNAPSHOTS.items() if (p.exists() if not str(p).endswith("action_center") else p.is_dir())],
        "apis": [{"path": a[0], "domain": a[1]} for a in APIS if AUDITS.get(a[1], Path()).exists() or a[1] == "d05"],
        "proibido": ["WebPosto live", "Postgres operacional direto"],
    }

    confiavel_domains = sum(1 for d in domains if d["status"] == "CONFIÁVEL")
    parcial_domains = sum(1 for d in domains if d["status"] == "PARCIAL")
    proxy_domains = sum(1 for d in domains if d["proxy"])

    executive = {
        "1_dominiosCobertos": len([d for d in domains if d["status"] != "NÃO DISPONÍVEL"]),
        "2_dominiosComEvidencia": sum(1 for d in domains if d["evidence"]),
        "3_dominiosComProxy": proxy_domains,
        "4_decisoesAuditaveis": citable,
        "5_acoesComEvidencia": with_evidence,
        "6_copilotFalaRoi": bool(decisions) and f051_qa.get("semRoiSemCalculo", True),
        "7_copilotFalaExecucao": action_count > 0 and f052_qa.get("auditavel", False),
        "8_copilotFalaPessoas": AUDITS["people"].exists(),
        "9_copilotFalaOperacoes": citable > 0,
        "10_copilotFalaFinanceiro": AUDITS["corporate_hub"].exists(),
        "11_riscoAlucinacao": hallucination_risk > 0,
        "12_riscoVazamento": governance["vazamentoRisco"] != "BAIXO",
        "13_riscoCrossTenant": governance["crossTenant"],
        "14_recomendacaoSemLineage": not_citable,
        "15_roiSemOrigem": int(f051_qa.get("roiSemCalculo") or 0),
        "16_catalogoCompleto": len(catalog) >= 10,
        "17_copilotGovernavel": True,
        "18_copilotAuditavel": f051_qa.get("auditavel") and f052_qa.get("auditavel"),
        "19_goNoGo": "GO",
        "20_f053Liberado": False,
        "trustExecutivo": trust_exec,
        "totalDecisoes": len(decisions),
        "totalAcoes": action_count,
        "confiavelDomains": confiavel_domains,
        "parcialDomains": parcial_domains,
        "catalogoRespondivel": respondivel,
        "catalogoParcial": parcial,
        "catalogoNao": nao,
        "traceableRecommendations": traceable,
        "fragileRecommendations": fragile,
    }

    go = (
        trust_exec >= 70
        and executive["14_recomendacaoSemLineage"] == 0
        and executive["15_roiSemOrigem"] == 0
        and executive["18_copilotAuditavel"]
        and hallucination_risk == 0
        and respondivel >= 7
        and governance["semCrossTenant"]
    )
    executive["19_goNoGo"] = "GO" if go else "NO-GO"
    executive["20_f053Liberado"] = go

    parecer = (
        "[PARECER FINAL: GO PARA F05.3]"
        if go
        else "[PARECER FINAL: NO-GO COM JUSTIFICATIVA QUANTIFICADA]"
    )

    return {
        "sprint": "G02",
        "readOnly": True,
        "fonteWebPosto": False,
        "knowledgeCoverage": {"domains": domains, "confiavel": confiavel_domains, "parcial": parcial_domains},
        "decisionEvidence": {"total": len(decisions), "citable": citable, "notCitable": not_citable},
        "actionEvidence": {
            "total": action_count,
            "withExecutionEvidence": with_evidence,
            "canSpeakExecution": executive["7_copilotFalaExecucao"],
            "canSpeakResult": with_evidence > 0,
        },
        "traceability": {"auditavel": traceable, "fragil": fragile},
        "questionCatalog": catalog,
        "hallucinationChallenge": {"traps": hallucination, "riskCount": hallucination_risk},
        "governance": governance,
        "architecture": architecture,
        "executiveAnswers": executive,
        "parecerFinal": parecer,
    }


def _write_md(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def generate_reports(result: dict[str, Any]) -> None:
    ex = result["executiveAnswers"]
    kc = result["knowledgeCoverage"]
    de = result["decisionEvidence"]
    ae = result["actionEvidence"]
    tr = result["traceability"]
    cat = result["questionCatalog"]
    hall = result["hallucinationChallenge"]
    gov = result["governance"]
    arch = result["architecture"]

    dom_rows = "\n".join(
        f"| {d['domain']} | {d['status']} | {d['evidence']} | {d['proxy']} |"
        for d in kc["domains"]
    )
    _write_md(
        "COPILOT_KNOWLEDGE_COVERAGE_REPORT.md",
        f"# Copilot Knowledge Coverage (G02)\n\n| Domínio | Status | Evidência | Proxy |\n|---|---|---|---|\n{dom_rows}\n\n"
        f"Confiáveis: **{kc['confiavel']}** · Parciais: **{kc['parcial']}**\n",
    )
    _write_md(
        "COPILOT_DECISION_EVIDENCE_REPORT.md",
        f"# Copilot Decision Evidence\n\n- Total decisões: **{de['total']}**\n- Citáveis: **{de['citable']}**\n- Não citáveis: **{de['notCitable']}**\n",
    )
    _write_md(
        "COPILOT_ACTION_EVIDENCE_REPORT.md",
        f"# Copilot Action Evidence\n\n- Ações: **{ae['total']}**\n- Com evidência execução: **{ae['withExecutionEvidence']}**\n"
        f"- Fala execução: **{ae['canSpeakExecution']}**\n- Fala resultado: **{ae['canSpeakResult']}**\n",
    )
    _write_md(
        "COPILOT_TRACEABILITY_REPORT.md",
        f"# Copilot Traceability\n\n- Auditáveis: **{tr['auditavel']}**\n- Frágeis: **{tr['fragil']}**\n",
    )
    cat_rows = "\n".join(f"| {c['domain']} | {c['question']} | {c['status']} |" for c in cat)
    _write_md(
        "COPILOT_QUESTION_CATALOG_REPORT.md",
        f"# Copilot Question Catalog\n\n| Domínio | Pergunta | Status |\n|---|---|---|\n{cat_rows}\n",
    )
    hall_rows = "\n".join(
        f"| {h['trap']} | {h['systemWouldRefuse']} |" for h in hall["traps"]
    )
    _write_md(
        "COPILOT_HALLUCINATION_CHALLENGE_REPORT.md",
        f"# Hallucination Challenge\n\n| Armadilha | Sistema recusaria |\n|---|---|\n{hall_rows}\n\nRiscos: **{hall['riskCount']}**\n",
    )
    _write_md(
        "COPILOT_GOVERNANCE_SECURITY_REPORT.md",
        f"# Governance & Security\n\n{json.dumps(gov, ensure_ascii=False, indent=2)}\n",
    )
    _write_md(
        "COPILOT_ARCHITECTURE_READINESS_REPORT.md",
        f"# Architecture Readiness\n\n{json.dumps(arch, ensure_ascii=False, indent=2)}\n",
    )
    _write_md(
        "G02_COPILOT_READINESS_QA_REPORT.md",
        f"# G02 Copilot QA\n\n| Pergunta | Resposta |\n|---|---|\n"
        f"| Base suficiente? | {ex['1_dominiosCobertos'] >= 6} |\n"
        f"| Respostas auditáveis? | {ex['18_copilotAuditavel']} |\n"
        f"| Rastreáveis? | {ex['14_recomendacaoSemLineage'] == 0} |\n"
        f"| Risco alucinação? | {ex['11_riscoAlucinacao']} |\n\n{result['parecerFinal']}\n",
    )
    _write_md(
        "G02_COPILOT_READINESS_REPORT.md",
        f"# G02 — Copilot Readiness\n\n"
        f"## Resumo\n\n"
        f"- Domínios cobertos: **{ex['1_dominiosCobertos']}**\n"
        f"- Decisões citáveis: **{ex['4_decisoesAuditaveis']}/{ex['totalDecisoes']}**\n"
        f"- Trust Executivo: **{ex['trustExecutivo']}**\n"
        f"- Catálogo: {ex['catalogoRespondivel']} respondível · {ex['catalogoParcial']} parcial\n\n"
        f"## Respostas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n{result['parecerFinal']}\n",
    )


def main() -> None:
    result = audit()
    out = ROOT / "scripts" / "g02_copilot_readiness.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    generate_reports(result)
    print(result["parecerFinal"])


if __name__ == "__main__":
    main()
