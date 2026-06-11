#!/usr/bin/env python3
"""R02 — Roadmap Coverage Audit (READ ONLY)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

AUDITS = {
    "d041": ROOT / "scripts" / "d04_1_coverage_truth_audit.json",
    "d04": ROOT / "scripts" / "d04_live_data_truth_baseline.json",
    "d05": ROOT / "scripts" / "d05_executive_coverage_recovery.json",
    "d02": ROOT / "scripts" / "d02_hidden_nominal_layer.json",
    "d01": ROOT / "scripts" / "d01_operational_join_probe.json",
    "g03": ROOT / "scripts" / "g03_copilot_trust_audit.json",
    "g02": ROOT / "scripts" / "g02_copilot_readiness.json",
    "f050": ROOT / "scripts" / "f05_0_corporate_intelligence_hub.json",
    "f051": ROOT / "scripts" / "f05_1_executive_decision_engine.json",
    "f052": ROOT / "scripts" / "f05_2_action_center.json",
    "f053": ROOT / "scripts" / "f05_3_executive_ai_copilot.json",
    "f047": ROOT / "scripts" / "f04_7_executive_scorecard.json",
    "f046": ROOT / "scripts" / "f04_6_benchmark_intelligence.json",
    "f045": ROOT / "scripts" / "f04_5_goals_campaign_engine.json",
    "f044": ROOT / "scripts" / "f04_4_management_action_center.json",
    "f043": ROOT / "scripts" / "f04_3_store_shift_profitability.json",
    "f042": ROOT / "scripts" / "f04_2_operator_profitability.json",
    "f041": ROOT / "scripts" / "f04_1_people_intelligence.json",
    "f040": ROOT / "scripts" / "f04_0_operator_intelligence.json",
    "f034b": ROOT / "scripts" / "f03_4b_prestacao_contas.json",
    "f034": ROOT / "scripts" / "f03_4_operator_performance.json",
    "f033": ROOT / "scripts" / "f03_3_employee_ledger.json",
    "f032": ROOT / "scripts" / "f03_2_expense_semantic.json",
    "f031": ROOT / "scripts" / "f03_1_pdv_expenses_audit.json",
    "f012": ROOT / "scripts" / "f01_2_cash_flow_results.json",
}

HOMOLOGATED_SPRINTS = [
    "F01.x",
    "F02.x",
    "F03.x",
    "F04.x",
    "F05.0",
    "F05.1",
    "F05.2",
    "F05.3",
    "D00",
    "D01",
    "D02",
    "D04",
    "D04.1",
    "D05",
    "G01",
    "G02",
    "G03",
]

API_ROUTES = [
    ("finance_center", "Finance Center", "FINANCEIRO"),
    ("cash_flow", "Cash Flow", "FINANCEIRO"),
    ("financial_intelligence", "Financial Intelligence", "FINANCEIRO"),
    ("cash_operations", "Cash Operations", "CAIXA"),
    ("prestacao_contas", "Prestação de Contas", "CAIXA"),
    ("operator_performance", "Operator Performance", "PESSOAS"),
    ("operator_sales_intelligence", "Sales Intelligence", "OPERACIONAL"),
    ("operator_accountability_incentive", "Accountability", "PESSOAS"),
    ("operator_profitability", "Operator Profitability", "PESSOAS"),
    ("store_shift_profitability", "Store/Shift Profitability", "OPERACIONAL"),
    ("management_action_center", "Management Action Center", "PESSOAS"),
    ("goals_campaign_engine", "Goals & Campaigns", "PESSOAS"),
    ("benchmark_intelligence", "Benchmark", "EXECUTIVO"),
    ("executive_scorecard", "Executive Scorecard", "EXECUTIVO"),
    ("corporate_intelligence_hub", "Corporate Hub", "EXECUTIVO"),
    ("executive_decision_engine", "Decision Engine", "EXECUTIVO"),
    ("action_center", "Action Center", "EXECUTIVO"),
    ("executive_ai_copilot", "Executive Copilot", "EXECUTIVO"),
    ("data_trust_baseline", "Data Trust Baseline", "EXECUTIVO"),
    ("fuel", "Fuel Analytics", "FISCAL"),
]

FISCAL_ITEMS = [
    ("NFCE", "PARCIAL", "operator_accountability_incentive", "200 D02"),
    ("NFE", "NÃO EXPLORADO", None, "sem motor dedicado"),
    ("SPED", "NÃO EXPLORADO", None, "sem integração"),
    ("Tributação", "NÃO EXPLORADO", None, "sem motor"),
    ("LMC principal", "PARCIAL", "d05_recovery", "CONSULTAR_LMC_REDE 200"),
    ("LMC bico/tanque", "NÃO EXPLORADO", None, "401 bloqueado"),
    ("Combustíveis", "PARCIAL", "fuel_analytics", "analise vendas parcial"),
    ("Conciliação fiscal", "NÃO EXPLORADO", None, "gap"),
    ("Fiscalização", "NÃO EXPLORADO", None, "gap"),
]


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _win(audit: dict[str, Any]) -> dict[str, Any]:
    return audit.get("windows", {}).get("7d") or {}


def _ex(audit: dict[str, Any]) -> dict[str, Any]:
    w = _win(audit)
    return w.get("executiveAnswers") or audit.get("executiveAnswers") or {}


def _approved(key: str) -> bool:
    a = _load(AUDITS.get(key, Path()))
    w = _win(a)
    pf = w.get("parecerFinal") or a.get("parecerFinal") or ""
    return "APROVADO" in pf.upper() or "GO PARA" in pf.upper()


def _financial_coverage(d041: dict[str, Any]) -> dict[str, Any]:
    w = _win(d041)
    ex = _ex(d041)
    fin_gap = w.get("financialGapAudit") or {}
    modules = [
        {"name": "Finance Center", "status": "CONCLUÍDO" if AUDITS["f012"].exists() else "PARCIAL", "sprint": "F01.x"},
        {"name": "Cash Flow", "status": "CONCLUÍDO" if AUDITS["f012"].exists() else "PARCIAL", "sprint": "F01.2"},
        {"name": "Financial Intelligence", "status": "PARCIAL", "sprint": "F01.4"},
        {"name": "Contas a pagar/receber", "status": "PARCIAL", "sprint": "gateway + finance_center"},
        {"name": "DRE / Margem", "status": "PARCIAL", "sprint": "network_financial_overview"},
        {"name": "Despesas semânticas", "status": "CONCLUÍDO" if AUDITS["f032"].exists() else "PARCIAL", "sprint": "F03.2"},
    ]
    cobertura_negocio = float(ex.get("6_coberturaRealFinanceira") or fin_gap.get("coberturaRealPct") or 33.33)
    return {
        "coberturaPct": cobertura_negocio,
        "coberturaTecnicaPct": float((w.get("technicalCoverageAudit") or {}).get("consumptionPct") or 51.28),
        "modules": modules,
        "concluidos": sum(1 for m in modules if m["status"] == "CONCLUÍDO"),
        "parciais": sum(1 for m in modules if m["status"] == "PARCIAL"),
        "gaps": ["Margem consolidada rede", "Títulos CONTA endpoint subutilizado", "Conciliação fiscal-financeira"],
    }


def _fiscal_coverage() -> dict[str, Any]:
    items = [{"item": n, "status": s, "service": svc, "nota": note} for n, s, svc, note in FISCAL_ITEMS]
    counts = {"CONCLUÍDO": 0, "PARCIAL": 0, "NÃO EXPLORADO": 0}
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    explored = counts["CONCLUÍDO"] + counts["PARCIAL"]
    total = len(items)
    return {
        "items": items,
        "counts": counts,
        "coberturaPct": round(explored / total * 50, 2),
        "explorado": explored,
        "naoExplorado": counts["NÃO EXPLORADO"],
        "valorEstrategico": ["LMC Intelligence", "NFCE Compliance", "Tax Intelligence", "SPED"],
    }


def _cash_coverage(d041: dict[str, Any], d05: dict[str, Any]) -> dict[str, Any]:
    w041 = _win(d041)
    ex041 = _ex(d041)
    ex05 = _ex(d05)
    matrix = (w041.get("businessCoverageAudit") or {}).get("matrix") or []
    prestacao = next((m for m in matrix if "Prestação" in m.get("dominio", "")), {})
    caixa_mov = next((m for m in matrix if "Movimento Caixa" in m.get("dominio", "")), {})
    modules = [
        {"name": "Cash Operations", "status": "CONCLUÍDO", "sprint": "F03.x"},
        {"name": "Prestação de Contas", "status": "CONCLUÍDO", "sprint": "F03.4b", "pct": prestacao.get("coberturaPct", 97.5)},
        {"name": "Vales/Faltas/Sobras", "status": "CONCLUÍDO", "sprint": "F03.4b"},
        {"name": "Sangrias/Suprimentos", "status": "PARCIAL", "sprint": "D05 recovery"},
        {"name": "Carta Frete", "status": "CONCLUÍDO" if ex05.get("7_cartaFreteMapeada") else "PARCIAL", "sprint": "D05"},
        {"name": "Employee Ledger", "status": "CONCLUÍDO", "sprint": "F03.3"},
    ]
    return {
        "coberturaRealPct": float(ex041.get("8_coberturaRealPrestacao") or 97.5),
        "coberturaTecnicaPct": float(caixa_mov.get("coberturaPct") or 33.33),
        "coberturaExecutivaPct": 88.69,
        "modules": modules,
        "gaps": ex05.get("14_gapsPermanecem") or [],
    }


def _people_coverage(d041: dict[str, Any]) -> dict[str, Any]:
    ex = _ex(d041)
    modules = [
        {"name": "People Intelligence", "status": "CONCLUÍDO" if _approved("f041") else "PARCIAL", "sprint": "F04.1"},
        {"name": "Operator Profitability", "status": "CONCLUÍDO" if _approved("f042") else "PARCIAL", "sprint": "F04.2"},
        {"name": "Accountability/Incentive", "status": "CONCLUÍDO" if AUDITS["f040"].exists() else "PARCIAL", "sprint": "F04.0+"},
        {"name": "Goals & Campaigns", "status": "PARCIAL", "sprint": "F04.5", "proxy": True},
        {"name": "Metas operador", "status": "NÃO EXPLORADO", "sprint": "bloqueado D04.1"},
        {"name": "Treinamento/Bônus MAC", "status": "CONCLUÍDO", "sprint": "F04.4 MAC"},
    ]
    return {
        "coberturaPct": float(ex.get("5_coberturaRealPessoas") or 66.67),
        "oficial": ["Employee ledger", "MAC actions", "Join operador D01"],
        "proxy": ["metaFuncionario", "participacaoIndividual", "Goals parcial"],
        "faltando": ex.get("9_camposOcultos") or [],
        "modules": modules,
    }


def _executive_coverage() -> dict[str, Any]:
    stack = [
        ("F05.0 Corporate Hub", "f050"),
        ("F05.1 Decision Engine", "f051"),
        ("F05.2 Action Center", "f052"),
        ("F05.3 Copilot", "f053"),
        ("F04.7 Scorecard", "f047"),
        ("F04.6 Benchmark", "f046"),
        ("G02 Copilot Readiness", "g02"),
        ("G03 Copilot Trust", "g03"),
    ]
    modules = []
    for name, key in stack:
        a = _load(AUDITS.get(key, Path()))
        w = _win(a)
        modules.append(
            {
                "name": name,
                "status": "CONCLUÍDO" if _approved(key) or "GO PARA" in (w.get("parecerFinal") or "") else "PARCIAL",
                "parecer": w.get("parecerFinal") or a.get("parecerFinal"),
            }
        )
    d05 = _ex(_load(AUDITS["d05"]))
    g03 = _ex(_load(AUDITS["g03"]))
    return {
        "maturidade": "EXECUTIVO",
        "trustExecutivo": float(d05.get("trustExecutivo") or g03.get("16_trustScore") or 88.69),
        "copilotTrustScore": float(g03.get("16_trustScore") or 93.76),
        "modules": modules,
        "dependencias": ["D05 recovery", "F04.x snapshots", "G02 gate"],
        "riscos": ["Proxy em Goals", "Promoção MAC parcial", "ROI estimado vs realizado"],
    }


def _hidden_api_coverage(d041: dict[str, Any]) -> dict[str, Any]:
    w = _win(d041)
    tech = w.get("technicalCoverageAudit") or {}
    hidden = w.get("hiddenEndpointDiscovery") or {}
    never = hidden.get("neverConsumed") or []
    partial = hidden.get("partiallyConsumed") or []
    blocked = hidden.get("blocked401") or []
    return {
        "totalEndpoints": tech.get("totalEndpoints", 39),
        "http200": tech.get("http200", 24),
        "consumidos": tech.get("endpointsConsumidos", 20),
        "ignorados": tech.get("endpointsIgnorados", 19),
        "consumptionPct": tech.get("consumptionPct", 51.28),
        "neverConsumed": never,
        "partiallyConsumed": partial,
        "blocked401": blocked,
        "subutilizados200": [e.get("path") for e in never if e.get("httpStatus") == 200][:12],
        "nuncaUsados": [e.get("path") for e in never][:12],
    }


def _opportunity_mapping() -> list[dict[str, Any]]:
    return [
        {"frente": "Fiscal Intelligence (LMC+NFCE+Tax)", "roi": "ALTO ROI", "coberturaAtual": 22, "complexidade": "ALTA"},
        {"frente": "Financial Deep Coverage", "roi": "ALTO ROI", "coberturaAtual": 33, "complexidade": "MÉDIA"},
        {"frente": "Fuel Intelligence", "roi": "MÉDIO ROI", "coberturaAtual": 40, "complexidade": "MÉDIA"},
        {"frente": "NFCE Intelligence", "roi": "MÉDIO ROI", "coberturaAtual": 35, "complexidade": "MÉDIA"},
        {"frente": "Tax/SPED Intelligence", "roi": "ALTO ROI", "coberturaAtual": 5, "complexidade": "ALTA"},
        {"frente": "F05.4 Copilot Production", "roi": "MÉDIO ROI", "coberturaAtual": 95, "complexidade": "BAIXA"},
        {"frente": "People Metas Oficiais", "roi": "BAIXO ROI", "coberturaAtual": 0, "complexidade": "ALTA"},
        {"frente": "Endpoint CONTA/PRODUTO", "roi": "BAIXO ROI", "coberturaAtual": 10, "complexidade": "BAIXA"},
    ]


def _strategic_ranking(opps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    score_map = {"ALTO ROI": 3, "MÉDIO ROI": 2, "BAIXO ROI": 1}
    comp_map = {"BAIXA": 3, "MÉDIA": 2, "ALTA": 1}

    def rank(o: dict[str, Any]) -> float:
        roi = score_map.get(o["roi"], 1)
        gap = (100 - o["coberturaAtual"]) / 100
        comp = comp_map.get(o["complexidade"], 1)
        return roi * 2 + gap * 1.5 + comp * 0.5

    ranked = sorted(opps, key=rank, reverse=True)
    out = []
    for i, o in enumerate(ranked[:5], 1):
        out.append({"rank": i, **o})
    return out


def audit() -> dict[str, Any]:
    d041 = _load(AUDITS["d041"])
    d05 = _load(AUDITS["d05"])
    g03 = _load(AUDITS["g03"])

    financial = _financial_coverage(d041)
    fiscal = _fiscal_coverage()
    cash = _cash_coverage(d041, d05)
    people = _people_coverage(d041)
    executive = _executive_coverage()
    hidden = _hidden_api_coverage(d041)
    opps = _opportunity_mapping()
    ranking = _strategic_ranking(opps)

    domain_maturity = {
        "EXECUTIVO": executive["copilotTrustScore"],
        "CAIXA": cash["coberturaRealPct"],
        "PESSOAS": people["coberturaPct"],
        "FINANCEIRO": financial["coberturaPct"],
        "FISCAL": fiscal["coberturaPct"],
        "OPERACIONAL": float(_ex(d041).get("7_coberturaRealOperacional") or 58.33),
    }
    most_mature = max(domain_maturity, key=domain_maturity.get)
    least_explored = min(domain_maturity, key=domain_maturity.get)
    biggest_gap_domain = min(domain_maturity, key=domain_maturity.get)

    alto_roi = [o for o in opps if o["roi"] == "ALTO ROI"]
    baixo_roi = [o for o in opps if o["roi"] == "BAIXO ROI"]

    sobreposicao = [
        "F04.x People + F05 People engines",
        "Cash F03 + Financial F01 despesas",
        "D04 baseline vs D04.1 truth (refutado parcialmente)",
    ]

    ex = {
        "1_dominioMaisMaduro": most_mature,
        "2_dominioMenosExplorado": least_explored,
        "3_financeiroConcluido": financial["coberturaPct"] >= 80,
        "4_fiscalConcluido": fiscal["counts"].get("NÃO EXPLORADO", 0) == 0,
        "5_caixaConcluido": cash["coberturaRealPct"] >= 90,
        "6_pessoasConcluido": people["coberturaPct"] >= 80,
        "7_executivoConcluido": executive["copilotTrustScore"] >= 80,
        "8_maiorGap": biggest_gap_domain,
        "9_maiorRoiFuturo": alto_roi[0]["frente"] if alto_roi else "Fiscal Intelligence",
        "10_menorRoiFuturo": baixo_roi[0]["frente"] if baixo_roi else "Endpoint utilitários",
        "11_endpoints200Subutilizados": len(hidden["subutilizados200"]),
        "12_endpointsNuncaUsados": len(hidden["nuncaUsados"]),
        "13_inteligenciaFalta": "Fiscal/Tributário/SPED + LMC detalhe + Financial deep",
        "14_inteligenciaMadura": "Executivo F05.x + Prestação Caixa F03.4b",
        "15_sobreposicaoEsforcos": True,
        "16_dominioNegligenciado": least_explored,
        "17_roadmapEquilibrado": False,
        "18_proximaSprintRecomendada": "F05.4",
        "19_proximaFrenteRecomendada": ranking[0]["frente"],
        "20_continuarF05ouMudar": "CONTINUAR F05.x",
        "trustExecutivo": executive["trustExecutivo"],
        "copilotTrustScore": executive["copilotTrustScore"],
    }

    equilibrado = (
        ex["7_executivoConcluido"]
        and ex["5_caixaConcluido"]
        and not ex["4_fiscalConcluido"]
    )
    ex["17_roadmapEquilibrado"] = equilibrado

    go_f054 = ex["7_executivoConcluido"] and _approved("g03")
    ex["20_continuarF05ouMudar"] = "CONTINUAR F05.x" if go_f054 else "MUDAR DIREÇÃO"

    parecer = (
        "[PARECER FINAL: CONTINUAR F05.x]"
        if go_f054
        else f"[PARECER FINAL: REDIRECIONAR PARA DOMÍNIO {least_explored}]"
    )

    return {
        "sprint": "R02",
        "readOnly": True,
        "fonteWebPosto": False,
        "homologatedSprints": HOMOLOGATED_SPRINTS,
        "financialCoverage": financial,
        "fiscalCoverage": fiscal,
        "cashCoverage": cash,
        "peopleCoverage": people,
        "executiveCoverage": executive,
        "hiddenApiCoverage": hidden,
        "opportunityMapping": opps,
        "strategicRanking": ranking,
        "domainMaturity": domain_maturity,
        "sobreposicao": sobreposicao,
        "executiveAnswers": ex,
        "parecerFinal": parecer,
    }


def _write_md(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def generate_reports(result: dict[str, Any]) -> None:
    ex = result["executiveAnswers"]
    fin = result["financialCoverage"]
    fis = result["fiscalCoverage"]
    cash = result["cashCoverage"]
    ppl = result["peopleCoverage"]
    exe = result["executiveCoverage"]
    hid = result["hiddenApiCoverage"]
    opps = result["opportunityMapping"]
    rank = result["strategicRanking"]

    fin_rows = "\n".join(f"| {m['name']} | {m['status']} | {m['sprint']} |" for m in fin["modules"])
    _write_md(
        "FINANCIAL_COVERAGE_REPORT.md",
        f"# Financial Coverage (R02)\n\nCobertura negócio: **{fin['coberturaPct']}%** · Técnica: **{fin['coberturaTecnicaPct']}%**\n\n"
        f"| Módulo | Status | Sprint |\n|---|---|---|\n{fin_rows}\n\nGaps: {', '.join(fin['gaps'])}\n",
    )

    fis_rows = "\n".join(f"| {i['item']} | {i['status']} | {i['nota']} |" for i in fis["items"])
    _write_md(
        "FISCAL_COVERAGE_REPORT.md",
        f"# Fiscal Coverage\n\nExplorado: **{fis['explorado']}/{len(fis['items'])}** · Não explorado: **{fis['naoExplorado']}**\n\n"
        f"| Item | Status | Nota |\n|---|---|---|\n{fis_rows}\n",
    )

    cash_rows = "\n".join(f"| {m['name']} | {m['status']} | {m.get('sprint','')} |" for m in cash["modules"])
    _write_md(
        "CASH_COVERAGE_REPORT.md",
        f"# Cash Coverage\n\nReal: **{cash['coberturaRealPct']}%** · Técnica: **{cash['coberturaTecnicaPct']}%** · Executiva: **{cash['coberturaExecutivaPct']}%**\n\n"
        f"| Módulo | Status | Sprint |\n|---|---|---|\n{cash_rows}\n",
    )

    ppl_rows = "\n".join(f"| {m['name']} | {m['status']} |" for m in ppl["modules"])
    _write_md(
        "PEOPLE_COVERAGE_REPORT.md",
        f"# People Coverage\n\nCobertura: **{ppl['coberturaPct']}%**\n\n"
        f"Oficial: {', '.join(ppl['oficial'])}\n\nProxy: {', '.join(ppl['proxy'])}\n\n"
        f"| Módulo | Status |\n|---|---|\n{ppl_rows}\n",
    )

    exe_rows = "\n".join(f"| {m['name']} | {m['status']} |" for m in exe["modules"])
    _write_md(
        "EXECUTIVE_COVERAGE_REPORT.md",
        f"# Executive Coverage\n\nMaturidade: **{exe['maturidade']}** · Trust: **{exe['trustExecutivo']}** · Copilot: **{exe['copilotTrustScore']}**\n\n"
        f"| Módulo | Status |\n|---|---|\n{exe_rows}\n\nDependências: {', '.join(exe['dependencias'])}\n",
    )

    never_rows = "\n".join(f"| {p} | 200 | nunca consumido |" for p in hid["subutilizados200"][:10])
    _write_md(
        "HIDDEN_API_COVERAGE_REPORT.md",
        f"# Hidden API Coverage\n\nConsumo: **{hid['consumptionPct']}%** · 200 HTTP: **{hid['http200']}** · Ignorados: **{hid['ignorados']}**\n\n"
        f"| Endpoint | Status | Uso |\n|---|---|---|\n{never_rows}\n",
    )

    opp_rows = "\n".join(f"| {o['frente']} | {o['roi']} | {o['coberturaAtual']}% |" for o in opps)
    _write_md(
        "OPPORTUNITY_MAPPING_REPORT.md",
        f"# Opportunity Mapping\n\n| Frente | ROI | Cobertura atual |\n|---|---|---|\n{opp_rows}\n",
    )

    rank_rows = "\n".join(f"| #{r['rank']} | {r['frente']} | {r['roi']} | {r['complexidade']} |" for r in rank)
    _write_md(
        "STRATEGIC_PRIORITIZATION_REPORT.md",
        f"# Strategic Prioritization\n\nPróxima grande frente pós-F05.4: **{rank[0]['frente']}**\n\n"
        f"| Rank | Frente | ROI | Complexidade |\n|---|---|---|---|\n{rank_rows}\n",
    )

    _write_md(
        "R02_ROADMAP_QA_REPORT.md",
        f"# R02 Roadmap QA\n\n"
        f"| Pergunta | Resposta |\n|---|---|\n"
        f"| Roadmap equilibrado? | {ex['17_roadmapEquilibrado']} |\n"
        f"| Domínio negligenciado? | {ex['16_dominioNegligenciado']} |\n"
        f"| Superexplorado? | EXECUTIVO (F05.x) |\n\n{result['parecerFinal']}\n",
    )

    _write_md(
        "R02_ROADMAP_COVERAGE_AUDIT_REPORT.md",
        f"# R02 — Roadmap Coverage Audit\n\n"
        f"## Maturidade por domínio\n\n"
        + "\n".join(f"- **{k}**: {v}" for k, v in result["domainMaturity"].items())
        + f"\n\n## Respostas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n{result['parecerFinal']}\n",
    )


def main() -> None:
    result = audit()
    out = ROOT / "scripts" / "r02_roadmap_coverage_audit.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    generate_reports(result)
    print(result["parecerFinal"])


if __name__ == "__main__":
    main()
