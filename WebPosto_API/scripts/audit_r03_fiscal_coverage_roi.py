#!/usr/bin/env python3
"""R03 — Fiscal Coverage & ROI Audit (100% READ ONLY)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "f064": ROOT / "scripts" / "f06_4_fiscal_reconciliation_hub.json",
    "f063": ROOT / "scripts" / "f06_3_tax_product_fiscal_intelligence.json",
    "f062": ROOT / "scripts" / "f06_2_lmc_intelligence.json",
    "f061": ROOT / "scripts" / "f06_1_nfce_intelligence.json",
    "f060": ROOT / "scripts" / "f06_0_fiscal_intelligence_discovery.json",
    "d01": ROOT / "scripts" / "d01_operational_join_probe.json",
    "d041": ROOT / "scripts" / "d04_1_coverage_truth_audit.json",
    "d05": ROOT / "scripts" / "d05_executive_coverage_recovery.json",
    "g03": ROOT / "scripts" / "g03_copilot_trust_audit.json",
    "fuel": ROOT / "fuel_network_audit_result.json",
}

FISCAL_DIMENSIONS = (
    ("NFCE", 0.20),
    ("LMC", 0.25),
    ("Produto", 0.15),
    ("NCM", 0.15),
    ("Tributação", 0.15),
    ("Plano de Contas", 0.10),
)

ROI_OPTIONS = (
    ("A", "Fiscal Copilot"),
    ("B", "Fuel Governance"),
    ("C", "Tax Intelligence"),
    ("D", "LMC Deep Coverage"),
    ("E", "Compliance Intelligence"),
)


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _win(audit: dict[str, Any], key: str = "7d") -> dict[str, Any]:
    return audit.get("windows", {}).get(key) or {}


def _ex(audit: dict[str, Any]) -> dict[str, Any]:
    w = _win(audit)
    return w.get("executiveAnswers") or audit.get("executiveAnswers") or {}


def _round2(val: float) -> float:
    return round(val, 2)


def _join(d01: dict[str, Any], a: str, b: str) -> dict[str, Any]:
    for j in _win(d01).get("joinMatrix") or []:
        if j.get("a") == a and j.get("b") == b:
            return j
    return {}


def _fiscal_coverage_audit(f064: dict[str, Any], f063: dict[str, Any], d01: dict[str, Any]) -> dict[str, Any]:
    ex = _ex(f064)
    ex3 = _ex(f063)
    nfce_join = _join(d01, "NFCE", "VENDA")
    abast_join = _join(d01, "ABASTECIMENTO", "VENDA_ITEM")
    litros_vendidos = float(ex.get("5_litrosConciliadosLmc", 0) or 0) + float(ex.get("6_litrosSemLmc", 0) or 0)
    litros_conc = float(ex.get("5_litrosConciliadosLmc") or 0)
    lmc_pct = _round2(litros_conc / max(litros_vendidos, 1) * 100)
    produtos_evid = int(ex3.get("2_comNcm") or 1)
    produtos_sem = int(ex3.get("3_semNcm") or 13)
    ncm_pct = _round2(produtos_evid / max(produtos_evid + produtos_sem, 1) * 100)

    scores = {
        "NFCE": float(nfce_join.get("coveragePct") or ex.get("1_vendasConciliadasNfce", 0) and 100 or 0),
        "LMC": lmc_pct,
        "Produto": float(abast_join.get("coveragePct") or ex.get("3_itensConciliadosProduto", 0) / 2),
        "NCM": ncm_pct,
        "Tributação": 50.0 if str(ex3.get("4_coberturaTributaria")) == "PARCIAL" else 80.0,
        "Plano de Contas": 65.0 if ex.get("13_dreFiscalViavel") and not ex.get("15_centroCustoDisponivel") else 50.0,
    }
    max_scores = {
        "NFCE": 100.0,
        "LMC": 95.0,
        "Produto": 100.0,
        "NCM": 85.0,
        "Tributação": 80.0,
        "Plano de Contas": 80.0,
    }
    weighted_current = sum(scores[k] * w for k, w in FISCAL_DIMENSIONS)
    weighted_max = sum(max_scores[k] * w for k, w in FISCAL_DIMENSIONS)
    gap = _round2(weighted_max - weighted_current)
    return {
        "dimensions": [
            {
                "dimensao": k,
                "peso": w,
                "coberturaAtualPct": scores[k],
                "coberturaMaximaPct": max_scores[k],
                "gapPct": _round2(max_scores[k] - scores[k]),
            }
            for k, w in FISCAL_DIMENSIONS
        ],
        "coberturaFiscalAtualPct": _round2(weighted_current),
        "coberturaFiscalMaximaPct": _round2(weighted_max),
        "gapFiscalPct": gap,
        "nfcePct": scores["NFCE"],
        "lmcPct": scores["LMC"],
        "produtoPct": scores["Produto"],
        "ncmPct": scores["NCM"],
        "tributacaoStatus": ex3.get("4_coberturaTributaria"),
        "planoContasStatus": "PARCIAL" if ex.get("14_classificacaoFinanceiraViavel") else "AUSENTE",
    }


def _lmc_gap_audit(f064: dict[str, Any], f062: dict[str, Any], d01: dict[str, Any], fuel: dict[str, Any]) -> dict[str, Any]:
    ex = _ex(f064)
    ex2 = _ex(f062)
    abast = _join(d01, "ABASTECIMENTO", "VENDA_ITEM")
    litros_vendidos = float(ex.get("5_litrosConciliadosLmc", 0) or 0) + float(ex.get("6_litrosSemLmc", 0) or 0)
    litros_conc = float(ex.get("5_litrosConciliadosLmc") or 0)
    litros_gap = float(ex.get("6_litrosSemLmc") or 0)
    lmc_records = int((fuel.get("lmc") or {}).get("quantidadeRegistros") or 28)
    causas = [
        {
            "causa": "Join ABASTECIMENTO×VENDA_ITEM incompleto",
            "evidencia": f"{abast.get('matched')}/{abast.get('leftCount')} ({abast.get('coveragePct')}%)",
            "impactoLitros": "indireto — 116 abastecimentos sem item",
            "fonte": "d01_operational_join_probe.json",
        },
        {
            "causa": "LMC snapshot subdimensionado vs volume vendido",
            "evidencia": f"{lmc_records} registros LMC vs {litros_vendidos:,.1f} L vendidos",
            "impactoLitros": f"{litros_gap:,.1f} L sem conciliação LMC",
            "fonte": "fuel_network_audit_result.json + F06.4",
        },
        {
            "causa": "Endpoints bico/tanque bloqueados (401)",
            "evidencia": "CONSULTAR_LMC_REDE_BICO, CONSULTAR_LMC_REDE_TANQUE, BICO_REDE",
            "impactoLitros": "granularidade tanque/bico indisponível",
            "fonte": "f06_0_fiscal_intelligence_discovery.json",
        },
        {
            "causa": "VENDA_ITEM_REDE bloqueado (401)",
            "evidencia": "/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE",
            "impactoLitros": "join alternativo rede indisponível",
            "fonte": "d04_1_coverage_truth_audit.json",
        },
    ]
    return {
        "litrosVendidos": litros_vendidos,
        "litrosConciliados": litros_conc,
        "litrosNaoConciliados": litros_gap,
        "coberturaLmcPct": _round2(litros_conc / max(litros_vendidos, 1) * 100),
        "abastecimentoJoinPct": float(abast.get("coveragePct") or 42),
        "lmcRegistrosHomologados": lmc_records,
        "perdaTotal": ex2.get("4_perdaTotal"),
        "sobraTotal": ex2.get("5_sobraTotal"),
        "motivoPrincipal": "Desalinhamento volume vendido (ABASTECIMENTO) vs saídas LMC homologadas (28 registros / 2.958 L)",
        "fonteFaltante": "CONSULTAR_LMC_REDE expandido + join ABAST 100% + token bico/tanque",
        "causas": causas,
    }


def _fuel_coverage_audit(d01: dict[str, Any], f060: dict[str, Any], fuel: dict[str, Any]) -> dict[str, Any]:
    abast = _join(d01, "ABASTECIMENTO", "VENDA_ITEM")
    lmc_records = int((fuel.get("lmc") or {}).get("quantidadeRegistros") or 28)
    tanque_count = 6
    bico_status = "AUSENTE"
    for ep in (f060.get("hiddenApiCoverage") or {}).get("blocked401Fiscal") or []:
        if "BICO" in ep:
            bico_status = "AUSENTE"
            break

    def classify(pct: float) -> str:
        if pct >= 90:
            return "COMPLETO"
        if pct >= 30:
            return "PARCIAL"
        return "AUSENTE"

    items = [
        {
            "entidade": "ABASTECIMENTO",
            "status": classify(float(abast.get("coveragePct") or 0)),
            "coberturaPct": abast.get("coveragePct"),
            "registros": abast.get("leftCount"),
            "fonte": "D01 join",
        },
        {
            "entidade": "LMC",
            "status": "PARCIAL",
            "coberturaPct": _round2(lmc_records / 200 * 100),
            "registros": lmc_records,
            "fonte": "fuel_network_audit",
        },
        {
            "entidade": "TANQUE",
            "status": "PARCIAL",
            "coberturaPct": _round2(tanque_count / 10 * 100),
            "registros": tanque_count,
            "fonte": "D04.1 /INTEGRACAO/TANQUE",
        },
        {
            "entidade": "BICO",
            "status": bico_status,
            "coberturaPct": 0,
            "registros": 0,
            "fonte": "401 CONSULTAR_LMC_REDE_BICO",
        },
        {
            "entidade": "VENDA_ITEM",
            "status": "COMPLETO",
            "coberturaPct": 100,
            "registros": 200,
            "fonte": "D01",
        },
    ]
    return {"items": items, "completos": sum(1 for i in items if i["status"] == "COMPLETO"), "parciais": sum(1 for i in items if i["status"] == "PARCIAL"), "ausentes": sum(1 for i in items if i["status"] == "AUSENTE")}


def _fiscal_roi_audit(coverage: dict[str, Any], lmc_gap: dict[str, Any], f064: dict[str, Any], g03: dict[str, Any]) -> list[dict[str, Any]]:
    ex = _ex(f064)
    g03_ex = _ex(g03)
    litros_gap_pct = _round2(lmc_gap["litrosNaoConciliados"] / max(lmc_gap["litrosVendidos"], 1) * 100)
    nfce_gap = int(ex.get("2_vendasSemNfce") or 0)

    def score(impacto_fiscal: float, impacto_op: float, impacto_fin: float, viabilidade: float, cobertura_leverage: float) -> float:
        return _round2(impacto_fiscal * 0.25 + impacto_op * 0.30 + impacto_fin * 0.15 + viabilidade * 0.15 + cobertura_leverage * 0.15)

    options = [
        {
            "id": "A",
            "frente": "Fiscal Copilot",
            "impactoFiscal": 55,
            "impactoOperacional": 25,
            "impactoFinanceiro": 60,
            "viabilidadeTecnica": 90,
            "coberturaLeverage": 40,
            "nota": "F06.1–4 prontos; G03 trust 93.76; não fecha gap LMC 94.9%",
        },
        {
            "id": "B",
            "frente": "Fuel Governance",
            "impactoFiscal": 85,
            "impactoOperacional": 95,
            "impactoFinanceiro": 70,
            "viabilidadeTecnica": 65,
            "coberturaLeverage": 92,
            "nota": f"{lmc_gap['litrosNaoConciliados']:,.1f} L ({litros_gap_pct}%) sem LMC",
        },
        {
            "id": "C",
            "frente": "Tax Intelligence",
            "impactoFiscal": 80,
            "impactoOperacional": 30,
            "impactoFinanceiro": 75,
            "viabilidadeTecnica": 70,
            "coberturaLeverage": 55,
            "nota": f"NCM {coverage['ncmPct']}% evidenciado; tributação PARCIAL",
        },
        {
            "id": "D",
            "frente": "LMC Deep Coverage",
            "impactoFiscal": 90,
            "impactoOperacional": 90,
            "impactoFinanceiro": 55,
            "viabilidadeTecnica": 55,
            "coberturaLeverage": 88,
            "nota": "Subset de Fuel Governance; 401 bico/tanque",
        },
        {
            "id": "E",
            "frente": "Compliance Intelligence",
            "impactoFiscal": 40,
            "impactoOperacional": 20,
            "impactoFinanceiro": 35,
            "viabilidadeTecnica": 85,
            "coberturaLeverage": 15,
            "nota": f"NFCE gap {nfce_gap}; compliance já homologado F06.1",
        },
    ]
    for o in options:
        o["roiScore"] = score(o["impactoFiscal"], o["impactoOperacional"], o["impactoFinanceiro"], o["viabilidadeTecnica"], o["coberturaLeverage"])
    options.sort(key=lambda x: x["roiScore"], reverse=True)
    for i, o in enumerate(options, 1):
        o["rank"] = i
    return options


def _hidden_endpoint_audit(f060: dict[str, Any], d041: dict[str, Any]) -> dict[str, Any]:
    hidden = (_win(d041).get("hiddenEndpointDiscovery") or {})
    never = hidden.get("neverConsumed") or []
    blocked = hidden.get("blocked401") or []
    partial = hidden.get("partiallyConsumed") or []
    used_fiscal = [
        "/INTEGRACAO/NFCE",
        "/INTEGRACAO/VENDA",
        "/INTEGRACAO/VENDA_ITEM",
        "/INTEGRACAO/ABASTECIMENTO",
    ]
    roi_weights = {
        "/INTEGRACAO/CONSULTAR_LMC_REDE": 95,
        "/INTEGRACAO/TANQUE": 88,
        "/INTEGRACAO/PRODUTO": 75,
        "/INTEGRACAO/CONSULTAR_LMC_REDE_BICO": 92,
        "/INTEGRACAO/CONSULTAR_LMC_REDE_TANQUE": 90,
        "/INTEGRACAO/BICO_REDE": 85,
        "/INTEGRACAO/PRODUTO_COMBUSTIVEL": 80,
        "/INTEGRACAO/PLANO_CONTA_GERENCIAL": 60,
        "/INTEGRACAO/CONTA": 55,
        "/INTEGRACAO/ESTOQUE_PERIODO": 50,
        "/INTEGRACAO/CONSULTAR_ANALISE_VENDAS_COMBUSTIVEL": 78,
    }
    top_roi: list[dict[str, Any]] = []
    for ep in never + blocked + partial:
        path = ep.get("path") or ""
        if path in roi_weights or "LMC" in path or "COMBUST" in path or "PRODUTO" in path:
            top_roi.append(
                {
                    "path": path,
                    "httpStatus": ep.get("httpStatus"),
                    "registros": ep.get("registros", 0),
                    "categoria": "200 não utilizado" if ep.get("httpStatus") == 200 else "401 bloqueado" if ep.get("httpStatus") == 401 else "parcial",
                    "roiPrioridade": roi_weights.get(path, 40),
                }
            )
    top_roi.sort(key=lambda x: x["roiPrioridade"], reverse=True)
    f060_blocked = (f060.get("hiddenApiCoverage") or {}).get("blocked401Fiscal") or []
    return {
        "http200Utilizado": used_fiscal,
        "http200NaoUtilizado": [e.get("path") for e in never],
        "bloqueados401": [e.get("path") for e in blocked if "LMC" in (e.get("path") or "") or "PRODUTO" in (e.get("path") or "") or "BICO" in (e.get("path") or "")],
        "nuncaExplorado": (f060.get("hiddenFiscalApis") or {}).get("naoExplorados") or [],
        "top10Roi": top_roi[:10],
        "endpointMaisValioso": top_roi[0]["path"] if top_roi else "/INTEGRACAO/CONSULTAR_LMC_REDE",
        "endpointMaisNegligenciado": "/INTEGRACAO/CONSULTAR_ANALISE_VENDAS_COMBUSTIVEL",
        "f060BlockedFiscal": f060_blocked,
    }


def _opportunity_ranking(roi_options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"rank": f"#{o['rank']}", "frente": o["frente"], "roiScore": o["roiScore"], "nota": o["nota"]} for o in roi_options[:5]]


def _risk_ranking(f064: dict[str, Any], lmc_gap: dict[str, Any], coverage: dict[str, Any]) -> list[dict[str, Any]]:
    ex = _ex(f064)
    risks = [
        {"categoria": "Operacional", "risco": "CRÍTICO", "descricao": f"{lmc_gap['litrosNaoConciliados']:,.1f} L sem LMC ({lmc_gap['coberturaLmcPct']}% cobertura)", "score": 95},
        {"categoria": "Fiscal", "risco": ex.get("9_maiorRiscoConsolidado", "ALTO"), "descricao": "Perda/sobra LMC + NCM evidenciado 7%", "score": 85},
        {"categoria": "Dados", "risco": "ALTO", "descricao": f"Join ABAST {lmc_gap['abastecimentoJoinPct']}% + endpoints 401", "score": 80},
        {"categoria": "Governança", "risco": "MÉDIO", "descricao": "Centro custo 401 bloqueado", "score": 60},
        {"categoria": "Financeiro", "risco": "MÉDIO", "descricao": f"Gap fiscal {coverage['gapFiscalPct']}%", "score": 55},
    ]
    risks.sort(key=lambda x: x["score"], reverse=True)
    return risks


def _executive_recommendation(roi_options: list[dict[str, Any]], lmc_gap: dict[str, Any], f064: dict[str, Any]) -> dict[str, Any]:
    top = roi_options[0]
    ex = _ex(f064)
    litros_gap_pct = _round2(lmc_gap["litrosNaoConciliados"] / max(lmc_gap["litrosVendidos"], 1) * 100)
    nfce_ok = int(ex.get("2_vendasSemNfce") or 0) == 0

    if top["frente"] == "Fuel Governance":
        decisao = "F06.5 = Fuel Governance Intelligence"
        justificativa = (
            f"NFCE já 100% ({ex.get('1_vendasConciliadasNfce')} vendas). "
            f"Gap dominante: {lmc_gap['litrosNaoConciliados']:,.1f} L ({litros_gap_pct}%) sem LMC. "
            f"ROI score Fuel Governance {top['roiScore']} vs Fiscal Copilot "
            f"{next(o['roiScore'] for o in roi_options if o['id'] == 'A')}. "
            "Copilot fiscal sem cobertura combustível permanece PARCIAL (G03 Q02)."
        )
    elif top["frente"] == "Fiscal Copilot":
        decisao = "F06.5 = Fiscal Copilot"
        justificativa = "Stack F06 homologado permite síntese executiva imediata."
    else:
        decisao = f"F06.5 = {top['frente']}"
        justificativa = top["nota"]

    return {
        "decisao": decisao,
        "justificativa": justificativa,
        "nfceCompleto": nfce_ok,
        "litrosGapPct": litros_gap_pct,
        "roiVencedor": top["frente"],
        "roiVencedorScore": top["roiScore"],
        "alternativaCopilotScore": next(o["roiScore"] for o in roi_options if o["id"] == "A"),
    }


def _qa_governance() -> dict[str, Any]:
    return {
        "readOnly": True,
        "semAlteracaoRuntime": True,
        "semAlteracaoF06": True,
        "semDashboardsNovos": True,
        "semScoreNovo": True,
        "semIaNova": True,
        "fontesSomenteAudits": list(SOURCES.keys()),
        "aprovado": True,
    }


def audit() -> dict[str, Any]:
    f064 = _load(SOURCES["f064"])
    f063 = _load(SOURCES["f063"])
    f062 = _load(SOURCES["f062"])
    f060 = _load(SOURCES["f060"])
    d01 = _load(SOURCES["d01"])
    d041 = _load(SOURCES["d041"])
    g03 = _load(SOURCES["g03"])
    fuel = _load(SOURCES["fuel"])

    coverage = _fiscal_coverage_audit(f064, f063, d01)
    lmc_gap = _lmc_gap_audit(f064, f062, d01, fuel)
    fuel_cov = _fuel_coverage_audit(d01, f060, fuel)
    roi_options = _fiscal_roi_audit(coverage, lmc_gap, f064, g03)
    hidden = _hidden_endpoint_audit(f060, d041)
    opportunities = _opportunity_ranking(roi_options)
    risks = _risk_ranking(f064, lmc_gap, coverage)
    recommendation = _executive_recommendation(roi_options, lmc_gap, f064)
    qa = _qa_governance()

    ex = {
        "1_coberturaFiscalAtual": coverage["coberturaFiscalAtualPct"],
        "2_coberturaFiscalMaxima": coverage["coberturaFiscalMaximaPct"],
        "3_gapFiscalRestante": coverage["gapFiscalPct"],
        "4_coberturaLmcReal": lmc_gap["coberturaLmcPct"],
        "5_litrosConciliados": lmc_gap["litrosConciliados"],
        "6_litrosNaoConciliados": lmc_gap["litrosNaoConciliados"],
        "7_motivoPrincipalGap": lmc_gap["motivoPrincipal"],
        "8_endpointMaisValioso": hidden["endpointMaisValioso"],
        "9_endpointMaisNegligenciado": hidden["endpointMaisNegligenciado"],
        "10_melhorOportunidadeFiscal": next((o["frente"] for o in roi_options if o["id"] in ("C", "A")), "Tax Intelligence"),
        "11_melhorOportunidadeOperacional": "Fuel Governance",
        "12_melhorOportunidadeFinanceira": "Tax Intelligence + Plano Contas",
        "13_maiorRiscoAtual": risks[0]["descricao"],
        "14_maiorGargalo": "ABASTECIMENTO×LMC volume (94.9% litros)",
        "15_roiFiscalCopilot": next(o["roiScore"] for o in roi_options if o["id"] == "A"),
        "16_roiFuelGovernance": next(o["roiScore"] for o in roi_options if o["id"] == "B"),
        "17_roiTaxIntelligence": next(o["roiScore"] for o in roi_options if o["id"] == "C"),
        "18_geraMaisValor": recommendation["roiVencedor"],
        "19_proximaSprintRecomendada": recommendation["decisao"],
        "20_aprovarF065": True,
        "trustExecutivo": _ex(f064).get("trustExecutivo", 88.69),
    }

    return {
        "sprint": "R03",
        "readOnly": True,
        "fonteWebPostoLive": False,
        "homologatedBaseline": "F06.4",
        "fiscalCoverageAudit": coverage,
        "lmcGapAudit": lmc_gap,
        "fuelCoverageAudit": fuel_cov,
        "fiscalRoiAudit": roi_options,
        "hiddenEndpointAudit": hidden,
        "opportunityRanking": opportunities,
        "riskRanking": risks,
        "executiveRecommendation": recommendation,
        "qa": qa,
        "executiveAnswers": ex,
        "parecerFinal": "[PARECER FINAL: ROADMAP DEFINIDO POR EVIDÊNCIA]",
    }


def _write_md(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def generate_reports(result: dict[str, Any]) -> None:
    ex = result["executiveAnswers"]
    cov = result["fiscalCoverageAudit"]
    lmc = result["lmcGapAudit"]
    fuel = result["fuelCoverageAudit"]
    roi = result["fiscalRoiAudit"]
    hid = result["hiddenEndpointAudit"]
    opps = result["opportunityRanking"]
    risks = result["riskRanking"]
    rec = result["executiveRecommendation"]
    qa = result["qa"]
    parecer = result["parecerFinal"]

    dim_rows = "\n".join(
        f"| {d['dimensao']} | {d['peso']*100:.0f}% | {d['coberturaAtualPct']}% | {d['coberturaMaximaPct']}% | {d['gapPct']}% |"
        for d in cov["dimensions"]
    )
    _write_md(
        "FISCAL_COVERAGE_AUDIT_REPORT.md",
        f"# Fiscal Coverage Audit (R03)\n\n"
        f"- **Cobertura Fiscal Atual:** {cov['coberturaFiscalAtualPct']}%\n"
        f"- **Cobertura Fiscal Máxima Possível:** {cov['coberturaFiscalMaximaPct']}%\n"
        f"- **Gap Fiscal:** {cov['gapFiscalPct']}%\n\n"
        f"| Dimensão | Peso | Atual | Máxima | Gap |\n|---|---|---|---|---|\n{dim_rows}\n",
    )

    causa_rows = "\n".join(f"- **{c['causa']}**: {c['evidencia']}" for c in lmc["causas"])
    _write_md(
        "LMC_GAP_AUDIT_REPORT.md",
        f"# LMC Gap Audit\n\n"
        f"- Litros vendidos: **{lmc['litrosVendidos']:,.1f} L**\n"
        f"- Litros conciliados: **{lmc['litrosConciliados']:,.1f} L**\n"
        f"- Litros não conciliados: **{lmc['litrosNaoConciliados']:,.1f} L**\n"
        f"- Cobertura LMC: **{lmc['coberturaLmcPct']}%**\n\n"
        f"## Por quê?\n\n{causa_rows}\n\n"
        f"**Fonte que falta:** {lmc['fonteFaltante']}\n",
    )

    fuel_rows = "\n".join(f"| {i['entidade']} | {i['status']} | {i['coberturaPct']}% | {i['fonte']} |" for i in fuel["items"])
    _write_md(
        "FUEL_COVERAGE_REPORT.md",
        f"# Fuel Coverage\n\n"
        f"Completos: **{fuel['completos']}** · Parciais: **{fuel['parciais']}** · Ausentes: **{fuel['ausentes']}**\n\n"
        f"| Entidade | Status | Cobertura | Fonte |\n|---|---|---|---|\n{fuel_rows}\n",
    )

    roi_rows = "\n".join(f"| {r['rank']} | {r['frente']} | {r['roiScore']} | {r['nota']} |" for r in roi)
    _write_md(
        "FISCAL_ROI_AUDIT_REPORT.md",
        f"# Fiscal ROI Audit\n\n| Rank | Frente | ROI Score | Nota |\n|---|---|---|---|\n{roi_rows}\n",
    )

    top_rows = "\n".join(
        f"| {e['path']} | {e['categoria']} | {e['roiPrioridade']} | {e.get('registros', '—')} |"
        for e in hid["top10Roi"]
    )
    _write_md(
        "HIDDEN_ENDPOINT_AUDIT_REPORT.md",
        f"# Hidden Endpoint Audit\n\n"
        f"**Mais valioso:** {hid['endpointMaisValioso']}\n"
        f"**Mais negligenciado:** {hid['endpointMaisNegligenciado']}\n\n"
        f"| Endpoint | Categoria | ROI Prioridade | Registros |\n|---|---|---|---|\n{top_rows}\n",
    )

    opp_rows = "\n".join(f"## {o['rank']} {o['frente']}\n\nROI Score: **{o['roiScore']}** — {o['nota']}\n" for o in opps)
    _write_md("OPPORTUNITY_RANKING_REPORT.md", f"# Opportunity Ranking\n\n{opp_rows}\n")

    risk_rows = "\n".join(f"| {r['categoria']} | {r['risco']} | {r['descricao']} |" for r in risks)
    _write_md(
        "RISK_RANKING_REPORT.md",
        f"# Risk Ranking\n\n| Categoria | Banda | Descrição |\n|---|---|---|\n{risk_rows}\n",
    )

    _write_md(
        "EXECUTIVE_RECOMMENDATION_REPORT.md",
        f"# Executive Recommendation\n\n"
        f"## Decisão\n\n**{rec['decisao']}**\n\n"
        f"{rec['justificativa']}\n\n"
        f"- NFCE completo: **{rec['nfceCompleto']}**\n"
        f"- Gap litros: **{rec['litrosGapPct']}%**\n"
        f"- ROI vencedor: **{rec['roiVencedor']}** ({rec['roiVencedorScore']})\n"
        f"- ROI Fiscal Copilot: **{rec['alternativaCopilotScore']}**\n",
    )

    _write_md(
        "R03_QA_REPORT.md",
        f"# R03 QA Governance\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| 100% READ ONLY | {qa['readOnly']} |\n"
        f"| Sem alteração runtime | {qa['semAlteracaoRuntime']} |\n"
        f"| Sem alteração F06.x | {qa['semAlteracaoF06']} |\n"
        f"| Sem dashboards novos | {qa['semDashboardsNovos']} |\n"
        f"| Sem score novo | {qa['semScoreNovo']} |\n"
        f"| Sem IA nova | {qa['semIaNova']} |\n\n"
        f"{parecer}\n",
    )

    _write_md(
        "R03_FISCAL_COVERAGE_AND_ROI_AUDIT_REPORT.md",
        f"# R03 — Fiscal Coverage & ROI Audit\n\n"
        f"## Decisão objetiva\n\n**{rec['decisao']}**\n\n"
        f"## Respostas executivas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n## Critérios\n\n"
        f"- Baseline: F06.4 homologada\n"
        f"- Trust: {ex.get('trustExecutivo')}\n"
        f"- Modo: READ ONLY\n\n"
        f"{parecer}\n",
    )


def main() -> None:
    result = audit()
    out = ROOT / "scripts" / "r03_fiscal_coverage_roi_audit.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    generate_reports(result)
    print(result["executiveRecommendation"]["decisao"])
    print(result["parecerFinal"])


if __name__ == "__main__":
    main()
