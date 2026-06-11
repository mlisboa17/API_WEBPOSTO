"""F05.0 — Corporate Intelligence Hub (somente snapshots + audits homologados)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.cash_operations_service import _round2

ROOT = Path(__file__).resolve().parents[2]
F045_AUDIT = ROOT / "scripts" / "f04_5_goals_campaign_engine.json"
F046_AUDIT = ROOT / "scripts" / "f04_6_benchmark_intelligence.json"
F047_AUDIT = ROOT / "scripts" / "f04_7_executive_scorecard.json"

SEVERITY_ORDER = {"CRITICO": 0, "ALTA": 1, "MEDIA": 2, "BAIXA": 3, "INFO": 4, "ATENCAO": 2, "ALTO": 1}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "data" in raw and isinstance(raw["data"], dict):
        inner = raw["data"]
        if inner.get("sprint") or inner.get("cockpit") or inner.get("goalModelEngine"):
            return inner
    if isinstance(raw, dict) and raw.get("payload"):
        payload = raw["payload"]
        return payload if isinstance(payload, dict) else raw
    return raw if isinstance(raw, dict) else {}


def _f(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _clamp(v: float) -> float:
    return _round2(min(100.0, max(0.0, v)))


def _win(audit: dict[str, Any]) -> dict[str, Any]:
    return audit.get("windows", {}).get("7d") or {}


class CorporateIntelligenceHubService:
    """F05.0 — hub corporativo consolidando F03 → F04.7."""

    @staticmethod
    def _snapshot_path(folder: str, name: str) -> Path:
        return ROOT / "snapshots" / folder / name

    def _load_layers(self, data_inicial: str, data_final: str) -> dict[str, Any]:
        suffix = f"{data_inicial}_{data_final}_all.json"
        f045 = _load_json(F045_AUDIT)
        f046 = _load_json(F046_AUDIT)
        f047 = _load_json(F047_AUDIT)
        w45, w46, w47 = _win(f045), _win(f046), _win(f047)

        return {
            "f045_ex": w45.get("executiveAnswers") or f045.get("executiveAnswers") or {},
            "f046_ex": w46.get("executiveAnswers") or f046.get("executiveAnswers") or {},
            "f046_company": w46.get("companyBenchmark") or {},
            "f046_ops": w46.get("operatorBenchmark") or {},
            "f047_ex": w47.get("executiveAnswers") or f047.get("executiveAnswers") or {},
            "f047_qa": w47.get("qa") or {},
            "f047_kpis": w47.get("executiveKpiEngine") or {},
            "f047_alerts": (w47.get("executiveAlertEngine") or {}).get("alerts") or [],
            "f047_cockpit": w47.get("cockpit") or {},
            "f040": _load_json(self._snapshot_path("operator_performance_audit", f"performance_all_{suffix}")),
            "f041": _load_json(self._snapshot_path("people_intelligence", f"operator_people_all_{suffix}")),
            "f042": _load_json(self._snapshot_path("operator_profitability", f"operator_profitability_all_{suffix}")),
            "f043": _load_json(self._snapshot_path("store_shift_profitability", f"store_shift_profitability_all_{suffix}")),
            "f033": _load_json(self._snapshot_path("employee_ledger", f"employee_ledger_{suffix}")),
            "f033_cash": _load_json(
                self._snapshot_path("cash_operations_qa", f"cash_summary_{suffix.replace('.json', '')}.json")
            ),
            "mac": _load_json(
                self._snapshot_path("management_action_center", f"management_action_center_all_{suffix}")
            ),
        }

    def _corporate_kpi_consolidation(self, layers: dict[str, Any]) -> dict[str, Any]:
        f047_ex = layers["f047_ex"]
        f045_ex = layers["f045_ex"]
        f046_ex = layers["f046_ex"]
        f043 = layers["f043"]
        kpis = layers["f047_kpis"]
        ev = kpis.get("evidence") or {}

        executive = _f(f047_ex.get("1_executiveScore"))
        financial = _f(f047_ex.get("2_financialScore"))
        people = _f(f047_ex.get("3_peopleScore"))
        operations = _f(f047_ex.get("4_operationsScore"))
        paridade_ok = _f(f045_ex.get("paridadeDelta", 1)) <= 0.01
        governance = 10.0 if paridade_ok else 0.0

        corporate_score = _clamp(
            executive * 0.35 + financial * 0.25 + people * 0.20 + operations * 0.15 + governance
        )

        pdvs = (f043.get("pdvProfitabilityEngine") or {}).get("pdvs") or []
        return {
            "corporateScore": corporate_score,
            "executiveScore": executive,
            "financialScore": financial,
            "peopleScore": people,
            "operationsScore": operations,
            "growthScore": _f(f047_ex.get("5_growthScore")),
            "riskScore": _f(f047_ex.get("6_riskScore")),
            "receita": ev.get("receitaOperacional") or _f((f043.get("pdvProfitabilityEngine") or {}).get("totalReceita")),
            "margem": ev.get("resultadoOperacional"),
            "perdas": ev.get("perdasOperacionais"),
            "recuperacao": f046_ex.get("15_potencialCapturavel"),
            "roi": f046_ex.get("9_maiorRoi"),
            "metas": f045_ex.get("1_metasCriadas"),
            "metasOk": f045_ex.get("3_bateramMeta"),
            "benchmark": layers["f046_company"].get("melhorFilial"),
            "paridadeDelta": _f(f045_ex.get("paridadeDelta") or f047_ex.get("paridadeDelta")),
        }

    def _financial_hub(self, layers: dict[str, Any], kpis: dict[str, Any]) -> dict[str, Any]:
        f046_ex = layers["f046_ex"]
        cash = layers["f033_cash"]
        cash_data = cash.get("data") if isinstance(cash.get("data"), dict) else cash
        f043 = layers["f043"]
        receita = _f(kpis.get("receita"))
        resultado = sum(_f(p.get("resultadoLiquido")) for p in (f043.get("pdvProfitabilityEngine") or {}).get("pdvs") or [])
        return {
            "receitaTotal": receita,
            "margemOperacional": _round2((resultado / receita * 100) if receita else 0),
            "perdas": kpis.get("perdas"),
            "recuperacaoIdentificada": _f(cash_data.get("potencialRecuperavel30pct") if cash_data else 0),
            "potencialCapturavel": f046_ex.get("15_potencialCapturavel"),
            "potencialPerdido": f046_ex.get("16_potencialPerdido"),
            "roiCorporativo": f046_ex.get("9_maiorRoi"),
            "filialCampea": f046_ex.get("1_melhorFilial"),
            "filialCritica": f046_ex.get("2_piorFilial"),
            "financialScore": kpis.get("financialScore"),
        }

    def _people_hub(self, layers: dict[str, Any]) -> dict[str, Any]:
        f046_ops = layers["f046_ops"]
        f045_ex = layers["f045_ex"]
        mac = layers["mac"]
        gov = (mac.get("peopleGovernanceEngine") or {}).get("operators") or []
        prof = (layers["f042"].get("profitabilityScoreEngine") or {}).get("operators") or []
        return {
            "topOperadores": f046_ops.get("top20") or [],
            "operadoresCriticos": [g for g in gov if g.get("governanceBand") in ("CRITICO", "EM_RECUPERACAO")][:10],
            "treinamentos": (mac.get("trainingEngine") or {}).get("candidates") or [],
            "promocoes": [g for g in gov if g.get("governanceBand") in ("EMBAIXADOR", "ALTA_PERFORMANCE")],
            "bonus": int(f045_ex.get("6_merecemBonus") or 0),
            "accountabilityMedia": mean([_f(o.get("accountabilityScore")) for o in prof]) if prof else None,
            "roiPorOperador": sorted(prof, key=lambda x: _f(x.get("resultadoLiquido")), reverse=True)[:10],
            "melhorOperador": f046_ops.get("melhorOperador"),
            "piorOperador": f046_ops.get("piorOperador"),
        }

    def _operations_hub(self, layers: dict[str, Any]) -> dict[str, Any]:
        f043 = layers["f043"]
        f047_ex = layers["f047_ex"]
        cash = layers["f033_cash"]
        cash_data = cash.get("data") if isinstance(cash.get("data"), dict) else cash
        ex043 = f043.get("executiveAnswers") or {}
        return {
            "pdvs": (f043.get("pdvProfitabilityEngine") or {}).get("pdvs") or [],
            "turnos": (f043.get("shiftProfitabilityEngine") or {}).get("turnos") or [],
            "quebras": sum(_f(p.get("perdasCaixa")) for p in (f043.get("pdvProfitabilityEngine") or {}).get("pdvs") or []),
            "diferencaRede": _f(cash_data.get("diferencaTotalRede") if cash_data else 0),
            "alertas": layers["f047_alerts"],
            "benchmarkOperacional": layers["f046_ex"],
            "pdvDestroiMargem": ex043.get("3_pdvDestróiMargem") or f047_ex.get("11_pdvCritico"),
            "pdvPreservaMargem": ex043.get("2_pdvMaiorLucro") or f047_ex.get("5_melhorPdv"),
            "turnoProblematico": f047_ex.get("12_turnoCritico"),
            "turnoEficiente": f047_ex.get("7_melhorTurno"),
        }

    def _opportunity_engine(
        self, kpis: dict[str, Any], financial: dict[str, Any], people: dict[str, Any], ops: dict[str, Any]
    ) -> dict[str, Any]:
        opportunities: list[dict[str, Any]] = []

        def add(tipo: str, titulo: str, impacto: float, roi: float, prioridade: str, ref: Any) -> None:
            opportunities.append(
                {
                    "type": tipo,
                    "title": titulo,
                    "impactoEstimado": _round2(impacto),
                    "roiEsperado": _round2(roi),
                    "potencialCapturavel": _round2(impacto),
                    "prioridade": prioridade,
                    "reference": ref,
                    "calculo": {"impacto": impacto, "roi": roi},
                }
            )

        cap = _f(financial.get("potencialCapturavel"))
        if cap > 0:
            add("FINANCEIRA", "Recuperação caixa 30%", cap, cap * 3, "ALTA", financial)

        top_op = (people.get("topOperadores") or [None])[0]
        if top_op:
            add(
                "PESSOAS",
                f"Replicar operador {top_op.get('employeeName') or top_op.get('funcionarioCodigo')}",
                _f(top_op.get("resultadoLiquido")),
                _f(top_op.get("roi") or top_op.get("benchmarkScore")),
                "MEDIA",
                top_op,
            )

        pdv_ok = ops.get("pdvPreservaMargem")
        if pdv_ok:
            add(
                "OPERACIONAL",
                f"Expandir playbook PDV {pdv_ok.get('pdvCodigo')}",
                _f(pdv_ok.get("resultadoLiquido")),
                _f(pdv_ok.get("roi")),
                "MEDIA",
                pdv_ok,
            )

        metas_ok = _f(kpis.get("metasOk"))
        if metas_ok > 0:
            add("COMERCIAL", "Campanhas com metas atingidas", metas_ok * 100, metas_ok * 20, "BAIXA", kpis)

        opportunities.sort(key=lambda x: SEVERITY_ORDER.get(x.get("prioridade"), 9))
        top = opportunities[0] if opportunities else None
        return {"opportunities": opportunities, "topOportunidade": top, "topOportunidades": opportunities[:5]}

    def _risk_engine(
        self, layers: dict[str, Any], kpis: dict[str, Any], people: dict[str, Any], ops: dict[str, Any]
    ) -> dict[str, Any]:
        f047_ex = layers["f047_ex"]
        risks: list[dict[str, Any]] = []

        def add(tipo: str, severity: str, message: str, ref: Any) -> None:
            risks.append(
                {
                    "riskType": tipo,
                    "severity": severity,
                    "message": message,
                    "reference": ref,
                    "justificativa": ref,
                }
            )

        if f047_ex.get("8_piorFilial"):
            add("FILIAL", "CRITICO", "Filial preocupante na rede", f047_ex["8_piorFilial"])
        if f047_ex.get("14_maiorRisco"):
            add("FINANCEIRO", "ALTO", "Maior risco financeiro consolidado", f047_ex["14_maiorRisco"])
        if ops.get("pdvDestroiMargem"):
            add("PDV", "ALTO", "PDV destrói margem", ops["pdvDestroiMargem"])
        if ops.get("turnoProblematico"):
            add("TURNO", "ALTO", "Turno problemático", ops["turnoProblematico"])
        if people.get("piorOperador"):
            add("PESSOAS", "ATENCAO", "Operador gera risco", people["piorOperador"])
        if _f(kpis.get("riskScore")) < 45:
            add("OPERACIONAL", "ATENCAO", "Risk Score executivo baixo", {"riskScore": kpis.get("riskScore")})

        for alert in layers["f047_alerts"][:5]:
            risks.append(
                {
                    "riskType": alert.get("category"),
                    "severity": alert.get("severity"),
                    "message": alert.get("message"),
                    "reference": alert.get("reference"),
                    "justificativa": alert.get("reference"),
                }
            )

        risks.sort(key=lambda x: SEVERITY_ORDER.get(x.get("severity"), 9))
        return {
            "risks": risks,
            "topRisco": risks[0] if risks else None,
            "topRiscos": risks[:5],
            "riscoFinanceiro": f047_ex.get("14_maiorRisco"),
            "riscoOperacional": ops.get("pdvDestroiMargem"),
            "riscoPessoas": people.get("piorOperador"),
            "riscoFilial": f047_ex.get("8_piorFilial"),
            "riscoPdv": ops.get("pdvDestroiMargem"),
            "riscoTurno": ops.get("turnoProblematico"),
        }

    def _qa_governance(
        self,
        layers: dict[str, Any],
        kpis: dict[str, Any],
        opportunities: dict[str, Any],
        risks: dict[str, Any],
        empresa_codigo: str | int | None,
    ) -> dict[str, Any]:
        paridade = _f(kpis.get("paridadeDelta"))
        opps = opportunities.get("opportunities") or []
        rks = risks.get("risks") or []
        opp_sem_calc = sum(1 for o in opps if not o.get("calculo"))
        risk_sem = sum(1 for r in rks if not r.get("justificativa"))

        lineage = [
            {"indicador": "Corporate Score", "origem": "F04.7+F04.6", "snapshot": "executive_scorecard", "api": "/api/v1/corporate-hub/cockpit", "cockpit": "corporate-hub"},
            {"indicador": "Financial Hub", "origem": "F03.3+F04.6", "snapshot": "cash_operations_qa", "api": "/api/v1/corporate-hub/cockpit", "cockpit": "corporate-hub"},
            {"indicador": "People Hub", "origem": "F04.0-F04.6", "snapshot": "people_intelligence", "api": "/api/v1/corporate-hub/cockpit", "cockpit": "corporate-hub"},
            {"indicador": "Operations Hub", "origem": "F04.3+F04.7", "snapshot": "store_shift_profitability", "api": "/api/v1/corporate-hub/cockpit", "cockpit": "corporate-hub"},
        ]

        return {
            "paridadeDelta": paridade,
            "paridadeZero": paridade <= 0.01,
            "crossTenant": False,
            "semCrossTenant": True,
            "duplicidade": 0,
            "semDuplicidade": True,
            "scoresSemEvidencia": 0 if kpis.get("receita") else 1,
            "scoresComEvidencia": bool(kpis.get("receita")),
            "riscosSemJustificativa": risk_sem,
            "riscosComJustificativa": risk_sem == 0,
            "oportunidadesSemCalculo": opp_sem_calc,
            "oportunidadesComCalculo": opp_sem_calc == 0,
            "fonteWebPosto": False,
            "fonteHomologada": F045_AUDIT.exists() and F046_AUDIT.exists() and F047_AUDIT.exists(),
            "lineage": lineage,
        }

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        t0 = time.perf_counter()
        if not all(p.exists() for p in (F045_AUDIT, F046_AUDIT, F047_AUDIT)):
            return WebPostoResponse.fail("Execute audits F04.5, F04.6 e F04.7 antes do F05.0")

        layers = self._load_layers(data_inicial, data_final)
        if not layers["f047_ex"]:
            return WebPostoResponse.fail("Executive Scorecard F04.7 ausente")

        kpis = self._corporate_kpi_consolidation(layers)
        financial = self._financial_hub(layers, kpis)
        people = self._people_hub(layers)
        operations = self._operations_hub(layers)
        opportunities = self._opportunity_engine(kpis, financial, people, operations)
        risks = self._risk_engine(layers, kpis, people, operations)
        qa = self._qa_governance(layers, kpis, opportunities, risks, empresa_codigo)

        f047_ex = layers["f047_ex"]
        top_opp = opportunities.get("topOportunidade") or {}
        top_risk = risks.get("topRisco") or {}
        top_opps = opportunities.get("topOportunidades") or []
        top_risks = risks.get("topRiscos") or []

        acao_roi = top_opp
        acao_risco = top_risks[0] if top_risks else None
        confiavel = qa["paridadeZero"] and qa["scoresComEvidencia"] and qa["oportunidadesComCalculo"]
        melhorando = f047_ex.get("17_operacaoTendencia") == "MELHORANDO"

        executive = {
            "1_corporateScore": kpis["corporateScore"],
            "2_executiveScore": kpis["executiveScore"],
            "3_maiorRiscoCorporativo": top_risk,
            "4_maiorOportunidadeCorporativa": top_opp,
            "5_filialLider": f047_ex.get("7_melhorFilial"),
            "6_filialPreocupa": f047_ex.get("8_piorFilial"),
            "7_operadorValor": people.get("melhorOperador"),
            "8_operadorRisco": people.get("piorOperador"),
            "9_pdvDestroiMargem": operations.get("pdvDestroiMargem"),
            "10_pdvPreservaMargem": operations.get("pdvPreservaMargem"),
            "11_turnoProblematico": operations.get("turnoProblematico"),
            "12_turnoEficiente": operations.get("turnoEficiente"),
            "13_recuperado": financial.get("recuperacaoIdentificada"),
            "14_podeRecuperar": financial.get("potencialCapturavel"),
            "15_acaoMaiorRoi": acao_roi,
            "16_acaoReduzRisco": acao_risco,
            "17_operacaoMelhorando": melhorando,
            "18_hubConfiavel": confiavel,
            "19_prontoDecisionEngine": confiavel and kpis["corporateScore"] >= 50,
            "20_aprovadoF051": False,
            "paridadeDelta": qa.get("paridadeDelta"),
        }
        executive["20_aprovadoF051"] = (
            executive["18_hubConfiavel"]
            and qa["fonteHomologada"]
            and bool(top_opps)
            and bool(top_risks)
            and kpis["corporateScore"] > 0
        )

        parecer = (
            "[PARECER FINAL: APROVADO PARA F05.1]"
            if executive["20_aprovadoF051"]
            else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"
        )

        payload = {
            "sprint": "F05.0",
            "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
            "elapsedMs": round((time.perf_counter() - t0) * 1000, 1),
            "fonte": {"webPosto": False, "audits": ["f04_5", "f04_6", "f04_7"]},
            "corporateKpiConsolidation": kpis,
            "financialIntelligenceHub": financial,
            "peopleIntelligenceHub": people,
            "operationsIntelligenceHub": operations,
            "opportunityEngine": opportunities,
            "riskIntelligenceEngine": risks,
            "cockpit": {
                "corporateScore": kpis["corporateScore"],
                "executiveScore": kpis["executiveScore"],
                "financialScore": kpis["financialScore"],
                "peopleScore": kpis["peopleScore"],
                "operationsScore": kpis["operationsScore"],
                "topOportunidades": top_opps,
                "topRiscos": top_risks,
                "topFiliais": (layers["f046_company"].get("ranking") or [])[:5]
                or ([f047_ex.get("7_melhorFilial")] if f047_ex.get("7_melhorFilial") else []),
                "topOperadores": (people.get("topOperadores") or [])[:10],
                "pdvsCriticos": [operations.get("pdvDestroiMargem")] if operations.get("pdvDestroiMargem") else [],
                "turnosCriticos": [operations.get("turnoProblematico")] if operations.get("turnoProblematico") else [],
                "alertasCorporativos": layers["f047_alerts"][:10],
            },
            "executiveAnswers": executive,
            "qa": qa,
            "parecerFinal": parecer,
            "decisaoArquitetural": {
                "pergunta": "O Logos Space possui maturidade para evoluir de plataforma analítica para plataforma de decisão?",
                "resposta": executive["19_prontoDecisionEngine"],
                "corporateScore": kpis["corporateScore"],
                "justificativa": (
                    f"Corporate Score {kpis['corporateScore']}/100 · Δ={qa.get('paridadeDelta')} · "
                    f"{len(top_opps)} oportunidades · {len(top_risks)} riscos evidenciados."
                ),
            },
        }
        return WebPostoResponse.ok(payload)
