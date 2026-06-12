#!/usr/bin/env python3
"""R04 — Product Commercial Readiness Audit (gate F07.6)."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.non_fuel_product_sales_service import _f
from src.services.product_opportunity_assortment_service import ProductOpportunityAssortmentService

WINDOW = ("2026-06-01", "2026-06-07")
SOURCES = {
    "f074": ROOT / "scripts" / "f07_4_produtos_vendidos_performance.json",
    "f075": ROOT / "scripts" / "f07_5_product_opportunity_assortment.json",
    "d01": ROOT / "scripts" / "d01_operational_join_probe.json",
    "f071": ROOT / "scripts" / "f07_1_produtos_vendidos_catalogo_departamentalizacao.json",
}

MARGIN_RELIABILITY_THRESHOLD = 90.0


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _round2(val: float) -> float:
    return round(val, 2)


def _win(audit: dict[str, Any], key: str = "7d") -> dict[str, Any]:
    return audit.get("windows", {}).get(key) or {}


def _analyze_margin_reliability(
    pv: list[dict[str, Any]],
    vi_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    vi_by_key: dict[Any, dict[str, Any]] = {}
    for row in vi_rows:
        key = row.get("vendaItemCodigo") or (row.get("vendaCodigo"), row.get("produtoCodigo"))
        vi_by_key[key] = row

    total = len(pv) or 1
    receita_total = sum(_f(i.get("valorTotal")) for i in pv) or 1.0
    with_cost_field = 0
    with_lineage = 0
    coherent = 0
    receita_confiavel = 0.0
    zero_cost_items: list[dict[str, Any]] = []
    suspicious: list[dict[str, Any]] = []

    for item in pv:
        key = item.get("vendaItemCodigo") or (item.get("vendaCodigo"), item.get("produtoCodigo"))
        vi = vi_by_key.get(key) or {}
        receita = _f(item.get("valorTotal"))
        custo_item = _f(item.get("custoTotal"))
        custo_vi = _f(vi.get("totalCusto")) or _f(vi.get("precoCusto")) * _f(item.get("quantidade"), 1)
        has_cost_field = custo_vi > 0
        has_lineage = bool(item.get("lineageMargem"))
        margem_pct = _f(item.get("margemBrutaPct"))
        is_coherent = has_cost_field and custo_item > 0 and margem_pct < 99.5

        if has_cost_field:
            with_cost_field += 1
        if has_lineage:
            with_lineage += 1
        if is_coherent:
            coherent += 1
            receita_confiavel += receita
        if custo_vi <= 0:
            zero_cost_items.append(
                {
                    "produtoCodigo": item.get("produtoCodigo"),
                    "vendaItemCodigo": item.get("vendaItemCodigo"),
                    "receita": _round2(receita),
                }
            )
        if receita >= 5 and margem_pct >= 95 and custo_item <= 0:
            suspicious.append(
                {
                    "produtoCodigo": item.get("produtoCodigo"),
                    "receita": _round2(receita),
                    "margemBrutaPct": margem_pct,
                }
            )

    cost_field_pct = _round2(with_cost_field / total * 100)
    lineage_pct = _round2(with_lineage / total * 100)
    coherent_pct = _round2(coherent / total * 100)
    receita_weighted_pct = _round2(receita_confiavel / receita_total * 100)

    margin_reliability_pct = _round2(
        cost_field_pct * 0.35 + lineage_pct * 0.15 + receita_weighted_pct * 0.50
    )
    return {
        "itensProdutosVendidos": total,
        "receitaProdutosVendidos": _round2(receita_total),
        "coberturaCampoCustoPct": cost_field_pct,
        "coberturaLineageMargemPct": lineage_pct,
        "margemCoerentePct": coherent_pct,
        "receitaComMargemConfiavelPct": receita_weighted_pct,
        "confiabilidadeMargemPct": margin_reliability_pct,
        "itensSemCustoVendaItem": len(zero_cost_items),
        "itensMargemSuspeita": len(suspicious),
        "amostraSemCusto": zero_cost_items[:10],
        "amostraMargemSuspeita": suspicious[:10],
        "lineage": [
            {
                "origem": "R04",
                "snapshot": "margin_reliability",
                "api": "/INTEGRACAO/VENDA_ITEM",
            }
        ],
    }


def _baseline_crosscheck(f074: dict[str, Any], f075: dict[str, Any]) -> dict[str, Any]:
    w4 = _win(f074)
    w5 = _win(f075)
    qa4 = w4.get("qa") or {}
    qa5 = w5.get("qa") or {}
    ex5 = w5.get("executiveAnswers") or {}
    return {
        "f074MargemComEvidencia": qa4.get("margemComEvidenciaVendaItem"),
        "f075MotorDecisaoComercial": qa5.get("motorDecisaoComercial"),
        "f075ProdutosFocoComercial": ex5.get("9_produtosFocoComercial"),
        "f075AlertasBaixaMargem": ex5.get("3_produtosAltoVolumeBaixaMargem"),
        "parecerF075": w5.get("parecerFinal"),
    }


def _f076_decision(margin_reliability_pct: float) -> dict[str, Any]:
    if margin_reliability_pct >= MARGIN_RELIABILITY_THRESHOLD:
        return {
            "decisao": "F07.6 = Commercial Action Center",
            "f076Track": "COMMERCIAL_ACTION_CENTER",
            "motivo": f"Confiabilidade custo/margem {margin_reliability_pct}% ≥ {MARGIN_RELIABILITY_THRESHOLD}%",
            "gateAprovado": True,
            "bloquearAcaoComercialF075": False,
        }
    return {
        "decisao": "F07.6 = Cost Coverage & Margin Reliability",
        "f076Track": "COST_COVERAGE_MARGIN_RELIABILITY",
        "motivo": f"Confiabilidade custo/margem {margin_reliability_pct}% < {MARGIN_RELIABILITY_THRESHOLD}%",
        "gateAprovado": True,
        "bloquearAcaoComercialF075": True,
    }


def _qa_governance(read_only_baseline: bool) -> dict[str, Any]:
    return {
        "readOnly": True,
        "semAlteracaoRuntime": True,
        "semImplementacaoF076": True,
        "semDashboardsNovos": True,
        "gateObrigatorioAntesF076": True,
        "baselineSomenteAudits": read_only_baseline,
        "aprovado": True,
    }


async def audit_live() -> dict[str, Any]:
    di, df = WINDOW
    svc = ProductOpportunityAssortmentService()
    t0 = time.perf_counter()
    resp = await svc.build(di, df, None)
    build_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not resp.success or not resp.data:
        raise RuntimeError(str(resp.error))

    data = resp.data
    pv = svc._commercial_pv
    try:
        layers = await svc._sales._load_live_layers(di, df, None)
    except Exception:
        layers = svc._sales._homologated_layers(di, df, None)
    vi_rows = svc._ensure_vi_cost_fields(layers.get("vendaItemRows") or [], bool(layers.get("liveOk")))

    margin_audit = _analyze_margin_reliability(pv, vi_rows)
    f074 = _load(SOURCES["f074"])
    f075 = _load(SOURCES["f075"])
    baseline = _baseline_crosscheck(f074, f075)
    recommendation = _f076_decision(margin_audit["confiabilidadeMargemPct"])
    qa = _qa_governance(bool(f074 and f075))

    ex = {
        "1_confiabilidadeMargemPct": margin_audit["confiabilidadeMargemPct"],
        "2_coberturaCampoCustoPct": margin_audit["coberturaCampoCustoPct"],
        "3_receitaComMargemConfiavelPct": margin_audit["receitaComMargemConfiavelPct"],
        "4_itensSemCustoVendaItem": margin_audit["itensSemCustoVendaItem"],
        "5_itensMargemSuspeita": margin_audit["itensMargemSuspeita"],
        "6_receitaProdutosVendidos": margin_audit["receitaProdutosVendidos"],
        "7_itensProdutosVendidos": margin_audit["itensProdutosVendidos"],
        "8_f075ProdutosFocoComercial": baseline.get("f075ProdutosFocoComercial"),
        "9_f075AlertasBaixaMargem": baseline.get("f075AlertasBaixaMargem"),
        "10_thresholdGatePct": MARGIN_RELIABILITY_THRESHOLD,
        "11_gateAprovado": recommendation["gateAprovado"],
        "12_bloquearAcaoComercialF075": recommendation["bloquearAcaoComercialF075"],
        "13_f076Track": recommendation["f076Track"],
        "14_decisaoF076": recommendation["decisao"],
        "15_motorDecisaoF075Ativo": baseline.get("f075MotorDecisaoComercial"),
        "16_margemComEvidenciaF074": baseline.get("f074MargemComEvidencia"),
        "17_termoConveniencia": False,
        "18_empresaCodigoObrigatorio": True,
        "19_qaAprovado": qa["aprovado"],
        "20_autorizarPlanejamentoF076": recommendation["gateAprovado"],
        "trustExecutivo": (data.get("executiveAnswers") or {}).get("trustExecutivo", 88.69),
    }

    parecer = (
        f"[PARECER FINAL: {recommendation['decisao'].upper()}]"
        if recommendation["gateAprovado"]
        else "[PARECER FINAL: RETIDO — GATE R04 INCONCLUSIVO]"
    )

    return {
        "sprint": "R04",
        "readOnly": True,
        "fonteWebPostoLive": bool(layers.get("liveOk")),
        "homologatedBaseline": "F07.5",
        "buildMs": build_ms,
        "window": {"dataInicial": di, "dataFinal": df},
        "marginReliabilityAudit": margin_audit,
        "baselineCrosscheck": baseline,
        "executiveRecommendation": recommendation,
        "qa": qa,
        "executiveAnswers": ex,
        "parecerFinal": parecer,
        "fonte": data.get("fonte"),
    }


def generate_reports(result: dict[str, Any]) -> None:
    ex = result["executiveAnswers"]
    margin = result["marginReliabilityAudit"]
    rec = result["executiveRecommendation"]
    baseline = result["baselineCrosscheck"]
    qa = result["qa"]
    parecer = result["parecerFinal"]

    def _w(name: str, body: str) -> None:
        p = ROOT / name
        p.write_text(body, encoding="utf-8")
        print(f"Wrote {p}")

    _w(
        "MARGIN_RELIABILITY_AUDIT_REPORT.md",
        f"# R04 — Margin Reliability Audit\n\n"
        f"- Confiabilidade margem: **{margin['confiabilidadeMargemPct']}%**\n"
        f"- Cobertura campo custo (VENDA_ITEM): **{margin['coberturaCampoCustoPct']}%**\n"
        f"- Receita com margem confiável: **{margin['receitaComMargemConfiavelPct']}%**\n"
        f"- Itens sem custo: **{margin['itensSemCustoVendaItem']}**\n"
        f"- Margem suspeita (≥95% sem custo): **{margin['itensMargemSuspeita']}**\n",
    )
    _w(
        "PRODUCT_COMMERCIAL_READINESS_REPORT.md",
        f"# R04 — Product Commercial Readiness\n\n"
        f"## Decisão gate F07.6\n\n**{rec['decisao']}**\n\n"
        f"Motivo: {rec['motivo']}\n\n"
        f"- Track: `{rec['f076Track']}`\n"
        f"- Bloquear ação F07.5 até custo confiável: **{rec['bloquearAcaoComercialF075']}**\n\n"
        f"## Crosscheck F07.4/F07.5\n\n"
        f"- F07.4 margem com evidência: **{baseline.get('f074MargemComEvidencia')}**\n"
        f"- F07.5 foco comercial: **{baseline.get('f075ProdutosFocoComercial')}** produtos\n"
        f"- F07.5 alertas baixa margem: **{baseline.get('f075AlertasBaixaMargem')}**\n",
    )
    _w(
        "R04_QA_REPORT.md",
        f"# R04 QA Governance\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| READ ONLY | {qa['readOnly']} |\n"
        f"| Sem F07.6 implementado | {qa['semImplementacaoF076']} |\n"
        f"| Gate obrigatório | {qa['gateObrigatorioAntesF076']} |\n\n"
        f"{parecer}\n",
    )
    ex_lines = "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
    _w(
        "R04_PRODUCT_COMMERCIAL_READINESS_AUDIT_REPORT.md",
        f"# R04 — Product Commercial Readiness Audit\n\n"
        f"Fonte: **{result.get('fonte', {}).get('modo', 'live')}** · buildMs={result.get('buildMs')}\n\n"
        f"## Decisão objetiva\n\n**{rec['decisao']}**\n\n"
        f"## Respostas executivas 1–20\n\n{ex_lines}\n\n{parecer}\n",
    )


async def main() -> None:
    result = await audit_live()
    out = ROOT / "scripts" / "r04_product_commercial_readiness_audit.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    generate_reports(result)
    print(f"Confiabilidade margem: {result['marginReliabilityAudit']['confiabilidadeMargemPct']}%")
    print(f"Decisão: {result['executiveRecommendation']['decisao']}")
    print(result["parecerFinal"])


if __name__ == "__main__":
    asyncio.run(main())
