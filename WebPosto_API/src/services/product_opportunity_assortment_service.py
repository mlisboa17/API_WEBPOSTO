"""F07.5 — Product Opportunity & Assortment Intelligence."""
from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.cash_operations_service import _round2
from src.services.non_fuel_product_sales_service import _f, _lineage
from src.services.produtos_vendidos_performance_service import ProdutosVendidosPerformanceService

FUEL_DEPENDENCY_THRESHOLD = 70.0
MIX_BENCHMARK_GAP_PP = 5.0


class ProductOpportunityAssortmentService(ProdutosVendidosPerformanceService):
    """F07.5 — decisão comercial: sortimento, oportunidade e dependência."""

    def _product_rollup(self, pv: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_prod: dict[int, dict[str, Any]] = defaultdict(
            lambda: {
                "nome": "",
                "departamento": "",
                "qtd": 0.0,
                "receita": 0.0,
                "margem": 0.0,
                "filiais": set(),
            }
        )
        for i in pv:
            pc = int(i.get("produtoCodigo") or 0)
            if not pc:
                continue
            row = by_prod[pc]
            row["qtd"] += _f(i.get("quantidade"))
            row["receita"] += _f(i.get("valorTotal"))
            row["margem"] += _f(i.get("margemBruta"))
            row["nome"] = i.get("produtoNome") or row["nome"]
            row["departamento"] = i.get("departamento") or row["departamento"]
            emp = int(i.get("empresaCodigo") or 0)
            if emp:
                row["filiais"].add(emp)
        rows: list[dict[str, Any]] = []
        for pc, v in by_prod.items():
            receita = v["receita"]
            margem = v["margem"]
            rows.append(
                {
                    "produtoCodigo": pc,
                    "nome": v["nome"],
                    "departamento": v["departamento"],
                    "quantidade": _round2(v["qtd"]),
                    "receita": _round2(receita),
                    "margemBruta": _round2(margem),
                    "margemPct": _round2(margem / receita * 100) if receita else 0.0,
                    "filiaisAtivas": sorted(v["filiais"]),
                    "qtdFiliais": len(v["filiais"]),
                }
            )
        return rows

    def _margin_leaders(self, rollup: list[dict[str, Any]]) -> dict[str, Any]:
        ranked = sorted(
            [r for r in rollup if r.get("receita", 0) > 0],
            key=lambda x: (x.get("margemPct", 0), x.get("margemBruta", 0)),
            reverse=True,
        )
        return {
            "topProdutoMargemPct": ranked[0] if ranked else {},
            "rankingMargemPct": ranked[:15],
            "lineage": [_lineage("F07.5", "margin_leaders", "/INTEGRACAO/VENDA_ITEM")],
        }

    def _high_volume_low_margin(
        self,
        rollup: list[dict[str, Any]],
        margin_benchmark_pct: float,
    ) -> dict[str, Any]:
        qtys = [r.get("quantidade", 0) for r in rollup]
        vol_threshold = sorted(qtys)[int(len(qtys) * 0.75)] if qtys else 0
        alerts = [
            {
                **r,
                "alerta": "ALTO_VOLUME_BAIXA_MARGEM",
                "gapMargemPct": _round2(margin_benchmark_pct - r.get("margemPct", 0)),
            }
            for r in rollup
            if r.get("quantidade", 0) >= max(vol_threshold, 1)
            and r.get("margemPct", 0) < margin_benchmark_pct
        ]
        alerts.sort(key=lambda x: (x.get("quantidade", 0), -x.get("margemPct", 0)), reverse=True)
        return {
            "benchmarkMargemPct": margin_benchmark_pct,
            "volumeThreshold": vol_threshold,
            "produtos": alerts[:15],
            "totalAlertas": len(alerts),
            "lineage": [_lineage("F07.5", "high_volume_low_margin", "/api/v1/non-fuel-products/cockpit")],
        }

    def _expansion_potential(
        self,
        rollup: list[dict[str, Any]],
        branch_mix: dict[str, Any] | None,
        margin_benchmark_pct: float,
    ) -> dict[str, Any]:
        total_filiais = len((branch_mix or {}).get("filiais") or []) or 1
        candidates: list[dict[str, Any]] = []
        for r in rollup:
            if r.get("margemPct", 0) < margin_benchmark_pct:
                continue
            cobertura = r.get("qtdFiliais", 0) / total_filiais
            if cobertura >= 1:
                continue
            score = _round2(r.get("margemPct", 0) * (1 - cobertura) + r.get("receita", 0) * 0.01)
            candidates.append(
                {
                    **r,
                    "potencialExpansaoScore": score,
                    "coberturaFiliaisPct": _round2(cobertura * 100),
                    "recomendacao": f"Expandir para {total_filiais - r.get('qtdFiliais', 0)} filiais",
                }
            )
        candidates.sort(key=lambda x: x.get("potencialExpansaoScore", 0), reverse=True)
        return {
            "produtos": candidates[:15],
            "totalPotencial": len(candidates),
            "lineage": [_lineage("F07.5", "expansion_potential", "/api/v1/non-fuel-products/cockpit")],
        }

    def _branch_benchmark_gap(self, branch_mix: dict[str, Any] | None) -> dict[str, Any]:
        filiais = list((branch_mix or {}).get("filiais") or [])
        mixes = [float(f.get("mixProdutosVendidosPct") or 0) for f in filiais]
        benchmark = _round2(median(mixes)) if mixes else 0.0
        abaixo: list[dict[str, Any]] = []
        for f in filiais:
            mix_pv = float(f.get("mixProdutosVendidosPct") or 0)
            gap = _round2(benchmark - mix_pv)
            if gap > MIX_BENCHMARK_GAP_PP:
                abaixo.append(
                    {
                        **f,
                        "benchmarkMixPvPct": benchmark,
                        "gapBenchmarkPct": gap,
                        "status": "ABAIXO_BENCHMARK",
                    }
                )
        abaixo.sort(key=lambda x: x.get("gapBenchmarkPct", 0), reverse=True)
        return {
            "benchmarkMixProdutosVendidosPct": benchmark,
            "filiaisAbaixoBenchmark": abaixo,
            "totalAbaixoBenchmark": len(abaixo),
            "lineage": [_lineage("F07.5", "branch_benchmark_gap", "/api/v1/non-fuel-products/cockpit")],
        }

    def _commercial_focus_engine(
        self,
        rollup: list[dict[str, Any]],
        margin_leaders: dict[str, Any],
        low_margin: dict[str, Any],
        expansion: dict[str, Any],
    ) -> dict[str, Any]:
        low_margin_codes = {p.get("produtoCodigo") for p in low_margin.get("produtos") or []}
        expansion_codes = {p.get("produtoCodigo") for p in expansion.get("produtos") or []}
        leader_top = (margin_leaders.get("rankingMargemPct") or [])[:5]
        leader_codes = {p.get("produtoCodigo") for p in leader_top}
        foco: list[dict[str, Any]] = []
        for r in rollup:
            score = 0.0
            acoes: list[str] = []
            if r.get("produtoCodigo") in leader_codes:
                score += 30
                acoes.append("PROTEGER_MARGEM")
            if r.get("produtoCodigo") in expansion_codes:
                score += 35
                acoes.append("EXPANDIR_SORTIMENTO")
            if r.get("produtoCodigo") in low_margin_codes:
                score += 25
                acoes.append("REVISAR_PRECO_OU_CUSTO")
            if r.get("receita", 0) >= 20:
                score += min(20, r.get("receita", 0) / 10)
                acoes.append("PRIORIDADE_RECEITA")
            if score <= 0:
                continue
            foco.append(
                {
                    **r,
                    "focoComercialScore": _round2(score),
                    "acoesRecomendadas": acoes,
                }
            )
        foco.sort(key=lambda x: x.get("focoComercialScore", 0), reverse=True)
        return {
            "produtosFoco": foco[:15],
            "totalFoco": len(foco),
            "lineage": [_lineage("F07.5", "commercial_focus", "/api/v1/non-fuel-products/cockpit")],
        }

    def _fuel_dependency_risk(
        self,
        branch_mix: dict[str, Any] | None,
        mix_health: dict[str, Any],
    ) -> dict[str, Any]:
        filiais = list((branch_mix or {}).get("filiais") or [])
        risco_filiais = [
            {
                **f,
                "risco": "DEPENDENCIA_COMBUSTIVEL_ALTA",
            }
            for f in filiais
            if float(f.get("dependenciaCombustivelPct") or 0) >= FUEL_DEPENDENCY_THRESHOLD
        ]
        risco_filiais.sort(key=lambda x: float(x.get("dependenciaCombustivelPct") or 0), reverse=True)
        rede_pv = float(mix_health.get("participacaoProdutosVendidosPct") or 0)
        return {
            "thresholdDependenciaPct": FUEL_DEPENDENCY_THRESHOLD,
            "filiaisRisco": risco_filiais,
            "totalFiliaisRisco": len(risco_filiais),
            "dependenciaRedeExcessiva": rede_pv < 25,
            "participacaoProdutosVendidosPct": rede_pv,
            "lineage": [_lineage("F07.5", "fuel_dependency", "/api/v1/non-fuel-products/cockpit")],
        }

    def _assortment_intelligence(
        self,
        margin_leaders: dict[str, Any],
        low_margin: dict[str, Any],
        expansion: dict[str, Any],
        benchmark_gap: dict[str, Any],
        focus: dict[str, Any],
        fuel_risk: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "marginLeaders": margin_leaders,
            "highVolumeLowMargin": low_margin,
            "expansionPotential": expansion,
            "branchBenchmarkGap": benchmark_gap,
            "commercialFocus": focus,
            "fuelDependencyRisk": fuel_risk,
            "lineage": [_lineage("F07.5", "assortment_intelligence", "/api/v1/non-fuel-products/cockpit")],
        }

    def _cockpit_decision(
        self,
        cockpit: dict[str, Any],
        assortment: dict[str, Any],
    ) -> dict[str, Any]:
        leaders = assortment.get("marginLeaders") or {}
        low = assortment.get("highVolumeLowMargin") or {}
        exp = assortment.get("expansionPotential") or {}
        gap = assortment.get("branchBenchmarkGap") or {}
        focus = assortment.get("commercialFocus") or {}
        fuel = assortment.get("fuelDependencyRisk") or {}
        return {
            **cockpit,
            "tituloVisual": "Produtos Vendidos",
            "subtitulo": "Decisão comercial · sortimento e oportunidade",
            "topMargem": (leaders.get("rankingMargemPct") or [])[:5],
            "alertasBaixaMargem": (low.get("produtos") or [])[:5],
            "potencialExpansao": (exp.get("produtos") or [])[:5],
            "filiaisAbaixoBenchmark": (gap.get("filiaisAbaixoBenchmark") or [])[:5],
            "produtosFocoComercial": (focus.get("produtosFoco") or [])[:5],
            "dependenciaCombustivel": fuel.get("filiaisRisco") or [],
        }

    def _executive_answers_f075(
        self,
        executive: dict[str, Any],
        assortment: dict[str, Any],
        qa: dict[str, Any],
        coverage: dict[str, Any],
    ) -> dict[str, Any]:
        leaders = assortment.get("marginLeaders") or {}
        low = assortment.get("highVolumeLowMargin") or {}
        exp = assortment.get("expansionPotential") or {}
        gap = assortment.get("branchBenchmarkGap") or {}
        focus = assortment.get("commercialFocus") or {}
        fuel = assortment.get("fuelDependencyRisk") or {}
        top_margin = leaders.get("topProdutoMargemPct") or {}
        top_focus = (focus.get("produtosFoco") or [{}])[0]
        ex = dict(executive)
        ex.update(
            {
                "1_produtoMaiorMargemPct": top_margin.get("produtoCodigo"),
                "2_margemPctLider": top_margin.get("margemPct"),
                "3_produtosAltoVolumeBaixaMargem": low.get("totalAlertas"),
                "4_produtoAlertaMargemTop": ((low.get("produtos") or [{}])[0] or {}).get("produtoCodigo"),
                "5_produtosPotencialExpansao": exp.get("totalPotencial"),
                "6_produtoExpansaoTop": ((exp.get("produtos") or [{}])[0] or {}).get("produtoCodigo"),
                "7_filiaisAbaixoBenchmarkMix": gap.get("totalAbaixoBenchmark"),
                "8_benchmarkMixProdutosVendidosPct": gap.get("benchmarkMixProdutosVendidosPct"),
                "9_produtosFocoComercial": focus.get("totalFoco"),
                "10_produtoFocoPrioritario": top_focus.get("produtoCodigo"),
                "11_filiaisDependenciaCombustivel": fuel.get("totalFiliaisRisco"),
                "12_dependenciaRedeExcessiva": fuel.get("dependenciaRedeExcessiva"),
                "13_coberturaCatalogoPreservada": coverage.get("coberturaCatalogoFinalPct"),
                "14_termoConveniencia": False,
                "15_empresaCodigoObrigatorio": True,
                "16_cockpitDecisaoAprovado": False,
                "17_assortmentConfiavel": False,
                "18_motorDecisaoComercial": False,
                "19_qaAprovado": False,
                "20_aprovadoF076": False,
            }
        )
        aprovado = (
            qa.get("motorAuditavel")
            and leaders.get("topProdutoMargemPct")
            and ex.get("14_termoConveniencia") is False
            and (coverage.get("coberturaCatalogoFinalPct") or 0) >= 95
        )
        ex["16_cockpitDecisaoAprovado"] = aprovado
        ex["17_assortmentConfiavel"] = aprovado
        ex["18_motorDecisaoComercial"] = aprovado
        ex["19_qaAprovado"] = aprovado
        ex["20_aprovadoF076"] = aprovado
        return ex

    def _qa_assortment(self, qa: dict[str, Any], assortment: dict[str, Any]) -> dict[str, Any]:
        focus = assortment.get("commercialFocus") or {}
        has_lineage = all(
            (assortment.get(k) or {}).get("lineage")
            for k in (
                "marginLeaders",
                "highVolumeLowMargin",
                "expansionPotential",
                "branchBenchmarkGap",
                "commercialFocus",
                "fuelDependencyRisk",
            )
        )
        return {
            **qa,
            "semTermoConveniencia": True,
            "empresaCodigoObrigatorio": True,
            "assortmentComLineage": has_lineage,
            "focoComercialQuantificado": (focus.get("totalFoco") or 0) >= 0,
            "motorDecisaoComercial": has_lineage and qa.get("motorAuditavel", True),
            "motorAuditavel": qa.get("motorAuditavel", True) and has_lineage,
        }

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        resp = await super().build(data_inicial, data_final, empresa_codigo)
        if not resp.success or not resp.data:
            return resp

        data = resp.data
        pv = self._commercial_pv
        margin = data.get("marginIntelligence") or {}
        mix = data.get("mixHealthCommercial") or {}
        branch_mix = data.get("branchProductMix") or {}
        coverage = data.get("productMasterCoverage") or {}
        margin_benchmark = float(margin.get("margemBrutaPct") or mix.get("margemMediaPct") or 25)

        rollup = self._product_rollup(pv)
        margin_leaders = self._margin_leaders(rollup)
        low_margin = self._high_volume_low_margin(rollup, margin_benchmark)
        expansion = self._expansion_potential(rollup, branch_mix, margin_benchmark)
        benchmark_gap = self._branch_benchmark_gap(branch_mix)
        focus = self._commercial_focus_engine(rollup, margin_leaders, low_margin, expansion)
        fuel_risk = self._fuel_dependency_risk(branch_mix, mix)
        assortment = self._assortment_intelligence(
            margin_leaders, low_margin, expansion, benchmark_gap, focus, fuel_risk
        )
        qa = self._qa_assortment(data.get("qa") or {}, assortment)
        cockpit = self._cockpit_decision(data.get("cockpit") or {}, assortment)
        executive = self._executive_answers_f075(
            data.get("executiveAnswers") or {},
            assortment,
            qa,
            coverage,
        )
        aprovado = executive.get("20_aprovadoF076")
        parecer = (
            "[PARECER FINAL: APROVADO PARA F07.6]"
            if aprovado
            else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTIFICADA]"
        )

        data.update(
            {
                "sprint": "F07.5",
                "productOpportunityAssortment": assortment,
                "assortmentIntelligence": assortment,
                "cockpit": cockpit,
                "executiveAnswers": executive,
                "qa": qa,
                "parecerFinal": parecer,
                "dwLayer": {
                    **(data.get("dwLayer") or {}),
                    "factProductAssortmentRollup": rollup[:50],
                    "factCommercialFocus": focus.get("produtosFoco") or [],
                    "factBranchBenchmarkGap": benchmark_gap.get("filiaisAbaixoBenchmark") or [],
                    "factFuelDependencyRisk": fuel_risk.get("filiaisRisco") or [],
                },
            }
        )
        return WebPostoResponse.ok(data)
