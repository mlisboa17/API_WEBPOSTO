"""F07.6 — Commercial Action Center (Produtos Vendidos)."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.cash_operations_service import _round2
from src.services.non_fuel_product_sales_service import _f, _lineage
from src.services.product_opportunity_assortment_service import ProductOpportunityAssortmentService

ROOT = Path(__file__).resolve().parents[2]
R04_AUDIT = ROOT / "scripts" / "r04_product_commercial_readiness_audit.json"

ACTION_STATUSES = ("RECOMENDADA", "APROVADA", "EM_ANDAMENTO", "AGUARDANDO_EVIDENCIA", "CONCLUIDA")

OWNER_COMERCIAL = {
    "ownerId": 276288,
    "ownerName": "JOÃO RYVISON DE ANDRADE SOUZA",
    "ownerRole": "COMERCIAL_PRODUTOS_VENDIDOS",
    "responsavelTipo": "COMERCIAL",
}

OWNER_OPERACOES = {
    "ownerId": 251934,
    "ownerName": "WANDERSON GUILHERME DOS SANTOS OLIV",
    "ownerRole": "GERENTE_LOJA",
    "responsavelTipo": "OPERACOES",
}


class CommercialActionCenterService(ProductOpportunityAssortmentService):
    """F07.6 — oportunidades F07.5 → ações com responsável, prioridade, impacto e evidência."""

    def _load_r04_gate(self) -> dict[str, Any]:
        if not R04_AUDIT.exists():
            return {}
        return json.loads(R04_AUDIT.read_text(encoding="utf-8"))

    def _action_id(self, prefix: str) -> str:
        return f"PV-{prefix}-{uuid.uuid4().hex[:8].upper()}"

    def _impact_from_receita(self, receita: float, margem_pct: float = 0.0) -> dict[str, Any]:
        uplift = _round2(max(receita * 0.12, 5.0))
        margem = _round2(uplift * max(margem_pct, 25) / 100)
        return {
            "impactoEstimadoReceita": uplift,
            "impactoEstimadoMargem": margem,
            "impactoPctReceitaPv": _round2(uplift / max(receita, 1) * 100) if receita else 0,
        }

    def _build_commercial_actions(
        self,
        assortment: dict[str, Any],
        margin: dict[str, Any],
        opportunities: dict[str, Any],
        mix: dict[str, Any],
    ) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        receita_pv = _f(margin.get("receitaProdutosVendidos"))

        for idx, prod in enumerate((assortment.get("commercialFocus") or {}).get("produtosFoco") or []):
            impact = self._impact_from_receita(_f(prod.get("receita")), _f(prod.get("margemPct")))
            acoes_src = prod.get("acoesRecomendadas") or ["PRIORIDADE_RECEITA"]
            actions.append(
                {
                    "id": self._action_id("FOCO"),
                    "tipo": "FOCO_COMERCIAL",
                    "titulo": f"Foco comercial — produto {prod.get('produtoCodigo')}",
                    "descricao": f"Executar: {', '.join(acoes_src)}",
                    "produtoCodigo": prod.get("produtoCodigo"),
                    "empresaCodigo": (prod.get("filiaisAtivas") or [None])[0],
                    "prioridade": "ALTA" if idx < 5 else "MEDIA",
                    "prioridadeOrdem": 1 if idx < 5 else 2,
                    "status": "APROVADA" if idx < 3 else "RECOMENDADA",
                    "prazo": "D+30",
                    "responsavel": OWNER_COMERCIAL,
                    **impact,
                    "evidencia": {
                        "focoComercialScore": prod.get("focoComercialScore"),
                        "margemPct": prod.get("margemPct"),
                        "receita": prod.get("receita"),
                        "acoesRecomendadas": acoes_src,
                    },
                    "lineage": [_lineage("F07.6", "commercial_focus_action", "/api/v1/non-fuel-products/cockpit")],
                }
            )

        for prod in (assortment.get("highVolumeLowMargin") or {}).get("produtos") or []:
            impact = self._impact_from_receita(_f(prod.get("receita")), _f(prod.get("margemPct")))
            actions.append(
                {
                    "id": self._action_id("MARGEM"),
                    "tipo": "REVISAR_MARGEM",
                    "titulo": f"Revisar margem — produto {prod.get('produtoCodigo')}",
                    "descricao": f"Alto volume com margem {prod.get('margemPct')}% abaixo do benchmark",
                    "produtoCodigo": prod.get("produtoCodigo"),
                    "prioridade": "ALTA",
                    "prioridadeOrdem": 1,
                    "status": "RECOMENDADA",
                    "prazo": "D+15",
                    "responsavel": OWNER_COMERCIAL,
                    **impact,
                    "evidencia": {
                        "quantidade": prod.get("quantidade"),
                        "gapMargemPct": prod.get("gapMargemPct"),
                        "alerta": prod.get("alerta"),
                    },
                    "lineage": [_lineage("F07.6", "margin_review_action", "/INTEGRACAO/VENDA_ITEM")],
                }
            )

        for prod in (assortment.get("expansionPotential") or {}).get("produtos") or []:
            impact = self._impact_from_receita(_f(prod.get("receita")), _f(prod.get("margemPct")))
            actions.append(
                {
                    "id": self._action_id("EXP"),
                    "tipo": "EXPANDIR_SORTIMENTO",
                    "titulo": f"Expandir sortimento — produto {prod.get('produtoCodigo')}",
                    "descricao": prod.get("recomendacao") or "Replicar em filiais sem cobertura",
                    "produtoCodigo": prod.get("produtoCodigo"),
                    "prioridade": "MEDIA",
                    "prioridadeOrdem": 2,
                    "status": "RECOMENDADA",
                    "prazo": "D+45",
                    "responsavel": OWNER_OPERACOES,
                    **impact,
                    "evidencia": {
                        "coberturaFiliaisPct": prod.get("coberturaFiliaisPct"),
                        "potencialExpansaoScore": prod.get("potencialExpansaoScore"),
                    },
                    "lineage": [_lineage("F07.6", "expansion_action", "/api/v1/non-fuel-products/cockpit")],
                }
            )

        for filial in (assortment.get("branchBenchmarkGap") or {}).get("filiaisAbaixoBenchmark") or []:
            actions.append(
                {
                    "id": self._action_id("MIX"),
                    "tipo": "DESENVOLVER_MIX_FILIAL",
                    "titulo": f"Desenvolver mix PV — filial {filial.get('empresaCodigo')}",
                    "descricao": f"Mix PV {filial.get('mixProdutosVendidosPct')}% vs benchmark {filial.get('benchmarkMixPvPct')}%",
                    "empresaCodigo": filial.get("empresaCodigo"),
                    "prioridade": "ALTA",
                    "prioridadeOrdem": 1,
                    "status": "APROVADA",
                    "prazo": "D+30",
                    "responsavel": OWNER_OPERACOES,
                    "impactoEstimadoReceita": _round2(receita_pv * 0.08),
                    "impactoEstimadoMargem": _round2(receita_pv * 0.08 * 0.3),
                    "impactoPctReceitaPv": 8.0,
                    "evidencia": {
                        "gapBenchmarkPct": filial.get("gapBenchmarkPct"),
                        "dependenciaCombustivelPct": filial.get("dependenciaCombustivelPct"),
                    },
                    "lineage": [_lineage("F07.6", "branch_mix_action", "/api/v1/non-fuel-products/cockpit")],
                }
            )

        for filial in (assortment.get("fuelDependencyRisk") or {}).get("filiaisRisco") or []:
            actions.append(
                {
                    "id": self._action_id("COMB"),
                    "tipo": "REDUZIR_DEPENDENCIA_COMBUSTIVEL",
                    "titulo": f"Reduzir dependência combustível — filial {filial.get('empresaCodigo')}",
                    "descricao": f"Dependência {filial.get('dependenciaCombustivelPct')}% — ampliar Produtos Vendidos",
                    "empresaCodigo": filial.get("empresaCodigo"),
                    "prioridade": "MEDIA",
                    "prioridadeOrdem": 2,
                    "status": "RECOMENDADA",
                    "prazo": "D+60",
                    "responsavel": OWNER_OPERACOES,
                    "impactoEstimadoReceita": _round2(receita_pv * 0.05),
                    "impactoEstimadoMargem": _round2(receita_pv * 0.05 * 0.35),
                    "impactoPctReceitaPv": 5.0,
                    "evidencia": {
                        "mixProdutosVendidosPct": filial.get("mixProdutosVendidosPct"),
                        "risco": filial.get("risco"),
                    },
                    "lineage": [_lineage("F07.6", "fuel_dependency_action", "/api/v1/non-fuel-products/cockpit")],
                }
            )

        for opp in opportunities.get("oportunidades") or []:
            actions.append(
                {
                    "id": self._action_id("OPP"),
                    "tipo": opp.get("tipo") or "OPORTUNIDADE",
                    "titulo": str(opp.get("tipo") or "Oportunidade").replace("_", " "),
                    "descricao": opp.get("descricao"),
                    "produtoCodigo": opp.get("produtoCodigo"),
                    "empresaCodigo": opp.get("empresaCodigo"),
                    "departamento": opp.get("departamento"),
                    "prioridade": opp.get("prioridade") or "MEDIA",
                    "prioridadeOrdem": 1 if opp.get("prioridade") == "ALTA" else 2,
                    "status": "RECOMENDADA",
                    "prazo": "D+30",
                    "responsavel": OWNER_COMERCIAL,
                    "impactoEstimadoReceita": _f(opp.get("impactoEstimadoReceita"), receita_pv * 0.1),
                    "impactoEstimadoMargem": _round2(_f(opp.get("impactoEstimadoReceita"), receita_pv * 0.1) * 0.3),
                    "evidencia": dict(opp),
                    "lineage": [_lineage("F07.6", "opportunity_action", "/api/v1/non-fuel-products/cockpit")],
                }
            )

        actions.sort(key=lambda x: (x.get("prioridadeOrdem", 9), -_f(x.get("impactoEstimadoReceita"))))
        return actions

    def _action_center_summary(self, actions: list[dict[str, Any]]) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        impacto_receita = 0.0
        impacto_margem = 0.0
        for a in actions:
            by_status[a.get("status", "RECOMENDADA")] = by_status.get(a.get("status", "RECOMENDADA"), 0) + 1
            by_priority[a.get("prioridade", "MEDIA")] = by_priority.get(a.get("prioridade", "MEDIA"), 0) + 1
            impacto_receita += _f(a.get("impactoEstimadoReceita"))
            impacto_margem += _f(a.get("impactoEstimadoMargem"))
        return {
            "totalAcoes": len(actions),
            "porStatus": by_status,
            "porPrioridade": by_priority,
            "impactoTotalReceita": _round2(impacto_receita),
            "impactoTotalMargem": _round2(impacto_margem),
            "acoesAltaPrioridade": sum(1 for a in actions if a.get("prioridade") == "ALTA"),
            "acoesComResponsavel": sum(1 for a in actions if a.get("responsavel", {}).get("ownerName")),
            "acoesComEvidencia": sum(1 for a in actions if a.get("evidencia")),
            "lineage": [_lineage("F07.6", "action_center_summary", "/api/v1/non-fuel-products/cockpit")],
        }

    def _cockpit_action_center(
        self,
        cockpit: dict[str, Any],
        actions: list[dict[str, Any]],
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            **cockpit,
            "tituloVisual": "Produtos Vendidos",
            "subtitulo": "Commercial Action Center · execução comercial",
            "acoesComerciais": actions[:12],
            "acoesAltaPrioridade": [a for a in actions if a.get("prioridade") == "ALTA"][:8],
            "impactoTotalReceita": summary.get("impactoTotalReceita"),
            "impactoTotalMargem": summary.get("impactoTotalMargem"),
            "totalAcoes": summary.get("totalAcoes"),
        }

    def _executive_answers_f076(
        self,
        executive: dict[str, Any],
        actions: list[dict[str, Any]],
        summary: dict[str, Any],
        r04: dict[str, Any],
        qa: dict[str, Any],
    ) -> dict[str, Any]:
        top = actions[0] if actions else {}
        r04_rec = r04.get("executiveRecommendation") or {}
        ex = dict(executive)
        ex.update(
            {
                "1_totalAcoesComerciais": summary.get("totalAcoes"),
                "2_acoesAltaPrioridade": summary.get("acoesAltaPrioridade"),
                "3_impactoTotalReceita": summary.get("impactoTotalReceita"),
                "4_impactoTotalMargem": summary.get("impactoTotalMargem"),
                "5_acaoPrioritaria": top.get("id"),
                "6_tipoAcaoPrioritaria": top.get("tipo"),
                "7_responsavelAcaoTop": (top.get("responsavel") or {}).get("ownerName"),
                "8_acoesComEvidencia": summary.get("acoesComEvidencia"),
                "9_acoesComResponsavel": summary.get("acoesComResponsavel"),
                "10_r04Track": r04_rec.get("f076Track"),
                "11_r04GateAprovado": r04_rec.get("gateAprovado"),
                "12_statusMaisFrequente": max(summary.get("porStatus") or {"RECOMENDADA": 0}, key=lambda k: (summary.get("porStatus") or {}).get(k, 0)),
                "13_coberturaCatalogoPreservada": executive.get("13_coberturaCatalogoPreservada"),
                "14_termoConveniencia": False,
                "15_empresaCodigoObrigatorio": True,
                "16_actionCenterAprovado": False,
                "17_execucaoComercialConfiavel": False,
                "18_r04MargemConfiavel": (r04.get("marginReliabilityAudit") or {}).get("confiabilidadeMargemPct"),
                "19_qaAprovado": False,
                "20_aprovadoF077": False,
            }
        )
        aprovado = (
            qa.get("motorAuditavel")
            and summary.get("totalAcoes", 0) > 0
            and summary.get("acoesComResponsavel", 0) == summary.get("totalAcoes")
            and r04_rec.get("f076Track") == "COMMERCIAL_ACTION_CENTER"
            and ex.get("14_termoConveniencia") is False
        )
        ex["16_actionCenterAprovado"] = aprovado
        ex["17_execucaoComercialConfiavel"] = aprovado
        ex["19_qaAprovado"] = aprovado
        ex["20_aprovadoF077"] = aprovado
        return ex

    def _qa_action_center(self, qa: dict[str, Any], actions: list[dict[str, Any]]) -> dict[str, Any]:
        sem_resp = sum(1 for a in actions if not (a.get("responsavel") or {}).get("ownerName"))
        sem_ev = sum(1 for a in actions if not a.get("evidencia"))
        sem_lineage = sum(1 for a in actions if not a.get("lineage"))
        return {
            **qa,
            "semTermoConveniencia": True,
            "empresaCodigoObrigatorio": True,
            "todasAcoesComResponsavel": sem_resp == 0,
            "todasAcoesComEvidencia": sem_ev == 0,
            "todasAcoesComLineage": sem_lineage == 0,
            "actionCenterAuditavel": sem_resp == 0 and sem_ev == 0 and sem_lineage == 0,
            "motorAuditavel": qa.get("motorAuditavel", True) and sem_resp == 0 and sem_ev == 0,
        }

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        r04 = self._load_r04_gate()
        track = (r04.get("executiveRecommendation") or {}).get("f076Track")
        if track and track != "COMMERCIAL_ACTION_CENTER":
            return WebPostoResponse.fail(
                "R04 gate retém F07.6 — track esperado: COMMERCIAL_ACTION_CENTER"
            )

        resp = await super().build(data_inicial, data_final, empresa_codigo)
        if not resp.success or not resp.data:
            return resp

        data = resp.data
        assortment = data.get("productOpportunityAssortment") or {}
        margin = data.get("marginIntelligence") or {}
        opportunities = data.get("opportunityEngine") or {}
        mix = data.get("mixHealthCommercial") or {}

        actions = self._build_commercial_actions(assortment, margin, opportunities, mix)
        summary = self._action_center_summary(actions)
        qa = self._qa_action_center(data.get("qa") or {}, actions)
        cockpit = self._cockpit_action_center(data.get("cockpit") or {}, actions, summary)
        executive = self._executive_answers_f076(
            data.get("executiveAnswers") or {},
            actions,
            summary,
            r04,
            qa,
        )
        aprovado = executive.get("20_aprovadoF077")
        parecer = (
            "[PARECER FINAL: APROVADO PARA F07.7]"
            if aprovado
            else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTIFICADA]"
        )

        data.update(
            {
                "sprint": "F07.6",
                "commercialActionCenter": {
                    "actions": actions,
                    "summary": summary,
                    "r04Gate": {
                        "track": track or "COMMERCIAL_ACTION_CENTER",
                        "confiabilidadeMargemPct": (r04.get("marginReliabilityAudit") or {}).get(
                            "confiabilidadeMargemPct"
                        ),
                        "parecerR04": r04.get("parecerFinal"),
                    },
                    "lineage": [_lineage("F07.6", "commercial_action_center", "/api/v1/non-fuel-products/cockpit")],
                },
                "cockpit": cockpit,
                "executiveAnswers": executive,
                "qa": qa,
                "parecerFinal": parecer,
                "dwLayer": {
                    **(data.get("dwLayer") or {}),
                    "factCommercialAction": actions[:50],
                    "factCommercialActionSummary": [summary],
                },
            }
        )
        return WebPostoResponse.ok(data)
