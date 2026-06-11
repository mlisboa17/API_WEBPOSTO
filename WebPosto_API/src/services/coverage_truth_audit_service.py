"""D04.1 — Coverage Truth Audit (adversarial challenge to D04)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

from src.gateway.webposto_client import ENDPOINTS
from src.models.response_model import WebPostoResponse
from src.services.cash_operations_service import _round2

ROOT = Path(__file__).resolve().parents[2]
AUTHORIZED_FILIAIS = (11495, 5555)
DEFAULT_WINDOW = ("2026-06-01", "2026-06-07")

AUDIT_FILES = {
    "d04": ROOT / "scripts" / "d04_live_data_truth_baseline.json",
    "d01": ROOT / "scripts" / "d01_operational_join_probe.json",
    "d02": ROOT / "scripts" / "d02_hidden_nominal_layer.json",
    "f034b": ROOT / "scripts" / "f03_4b_prestacao_contas.json",
    "f047": ROOT / "scripts" / "f04_7_executive_scorecard.json",
    "f050": ROOT / "scripts" / "f05_0_corporate_intelligence_hub.json",
    "network_probe": ROOT / "webposto_network_probe_result.json",
}

LOGOS_CONSUMED_KEYS = {
    "abastecimento",
    "caixa",
    "caixa_apresentado",
    "caixa_rede",
    "caixa_apresentado_rede",
    "despesas_financeiro_rede",
    "financeiro",
    "titulo_receber",
    "movimento_conta",
    "transferencia_bancaria",
    "venda",
    "venda_item",
    "venda_item_rede",
    "venda_forma_pagamento",
    "venda_forma_pagamento_rede",
    "nfce",
    "funcionario",
    "analise_vendas_combustivel",
    "empresas",
    "produto_combustivel",
}

BUSINESS_DOMAINS = (
    "Prestação de Contas",
    "Movimento Caixa",
    "Operações PDV",
    "Metas",
    "Produtividade",
    "Participação",
)

FINANCIAL_GAP_CHECKS = (
    ("Carta Frete", "CAIXA_APRESENTADO.cartaFrete*", "partial", "yes", "partial"),
    ("Serviços", "VENDA (não tipado)", "none", "partial", "none"),
    ("Trocas", "VENDA.troco apenas", "none", "none", "none"),
    ("Suprimentos", "MOVIMENTO_CONTA", "partial", "partial", "partial"),
    ("Movimentos manuais", "CAIXA_APRESENTADO", "partial", "yes", "partial"),
    ("Despesas não conciliadas", "DESPESAS_REDE + F03.2", "partial", "yes", "partial"),
)

OPERATIONAL_GAP_CHECKS = (
    ("Cancelamentos", "VENDA.cancelada + NFCE", "partial", "partial", "partial"),
    ("Autorizações", "—", "none", "none", "none"),
    ("LMC", "CONSULTAR_LMC_REDE", "partial", "blocked", "partial"),
    ("Operações PDV", "VENDA+CAIXA", "yes", "yes", "yes"),
    ("Movimentos não tipados", "CAIXA_APRESENTADO", "partial", "partial", "partial"),
    ("Eventos de turno", "CAIXA.turno", "yes", "yes", "yes"),
)

PRESTACAO_FIELDS = (
    "funcionarioNome",
    "participacaoIndividual",
    "produtividadeFuncionario",
    "metaFuncionario",
    "fundoCaixa",
)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def _window(d: dict[str, Any], prefer: tuple[str, ...] = ("7d", "30d")) -> dict[str, Any]:
    windows = d.get("windows") or {}
    for key in prefer:
        if key in windows:
            return windows[key]
    return next(iter(windows.values()), {})


def _f(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _clamp(v: float) -> float:
    return _round2(min(100.0, max(0.0, v)))


def _trust_band(score: float) -> str:
    if score >= 90:
        return "CONFIAVEL"
    if score >= 75:
        return "UTILIZAVEL"
    if score >= 60:
        return "PARCIAL"
    return "NAO_CONFIAVEL"


def _level_score(level: str) -> float:
    return {"yes": 100.0, "partial": 50.0, "blocked": 25.0, "none": 0.0, "derived": 75.0}.get(level, 0.0)


def _available_score(val: Any) -> float:
    if val is True:
        return 100.0
    if val == "partial":
        return 50.0
    return 0.0


class CoverageTruthAuditService:
    """D04.1 — tenta refutar o trust 100% do D04 com evidência D00–F05."""

    def _load_layers(self) -> dict[str, Any]:
        audits = {k: _load_json(v) for k, v in AUDIT_FILES.items()}
        d04w = _window(audits["d04"])
        d01w = _window(audits["d01"], ("7d",))
        d02w = _window(audits["d02"], ("7d", "30d"))
        f034w = _window(audits["f034b"], ("30d", "7d"))
        probe = audits["network_probe"].get("endpoints") or []
        return {
            "audits": audits,
            "d04": d04w,
            "d04_ex": (d04w.get("executiveAnswers") or audits["d04"].get("executiveAnswers") or {}),
            "d01": d01w,
            "d01_ex": audits["d01"].get("executiveAnswers") or {},
            "d02": d02w,
            "d02_ex": audits["d02"].get("executiveAnswers") or {},
            "f034b": f034w,
            "f047_ex": (_window(audits["f047"]).get("executiveAnswers") or audits["f047"].get("executiveAnswers") or {}),
            "f050_ex": (_window(audits["f050"]).get("executiveAnswers") or audits["f050"].get("executiveAnswers") or {}),
            "network_probe": probe,
        }

    def _technical_coverage(self, layers: dict[str, Any]) -> dict[str, Any]:
        probe = layers["network_probe"]
        d02_nom = (layers["d02"].get("employeeNominalDiscovery") or {})
        catalog_total = len(probe) or (len(ENDPOINTS) + len(d02_nom.get("endpointsAuditados") or []))
        consumed = len(LOGOS_CONSUMED_KEYS)
        ignored = max(catalog_total - consumed, 0)
        status200 = sum(1 for e in probe if e.get("httpStatus") == 200)
        status401 = sum(1 for e in probe if e.get("httpStatus") == 401)
        d01_perf = layers["d01"].get("performance") or {}
        d01_200 = sum(1 for p in d01_perf.values() if p.get("status") == 200)
        return {
            "totalEndpoints": catalog_total,
            "endpointsCatalogClient": len(ENDPOINTS),
            "endpointsConsumidos": consumed,
            "endpointsIgnorados": ignored,
            "http200": status200 or d01_200,
            "http401": status401 or len(d02_nom.get("endpoints401") or []),
            "consumptionPct": _clamp(consumed / max(catalog_total, 1) * 100),
            "technicalReachPct": _clamp(status200 / max(catalog_total, 1) * 100),
            "blocked401Pct": _clamp(status401 / max(catalog_total, 1) * 100),
            "evidence": ["webposto_network_probe_result.json", "d01_operational_join_probe.json", "d02_hidden_nominal_layer.json"],
        }

    def _business_coverage(self, layers: dict[str, Any]) -> dict[str, Any]:
        d02_gap = (layers["d02"].get("prestacaoGapAnalysis") or {})
        f034_cov = ((layers["f034b"].get("discovery") or {}).get("apiCoverage") or {})
        f034_avg = mean(_available_score(v.get("available")) for v in f034_cov.values()) if f034_cov else 0.0
        d01_pct = _f(layers["d01_ex"].get("19_cobertura_reconstrucao_pct"), 87.5)
        d02_pct = _f(d02_gap.get("coberturaD02Pct") or layers["d02_ex"].get("15_novaCoberturaPct"), 97.5)
        movimento_avg = mean(_level_score(x[4]) for x in FINANCIAL_GAP_CHECKS)
        pdv_avg = mean(_level_score(x[4]) for x in OPERATIONAL_GAP_CHECKS)

        matrix = [
            {"dominio": "Prestação de Contas", "negocio": "UI completa", "api": f"{d02_pct}% campos", "coberturaPct": d02_pct},
            {"dominio": "Movimento Caixa", "negocio": "Tipos UI", "api": "Parcial/agregado", "coberturaPct": movimento_avg},
            {"dominio": "Operações PDV", "negocio": "Turno/PDV/cancel", "api": "Join transacional", "coberturaPct": pdv_avg},
            {"dominio": "Metas", "negocio": "metaFuncionario UI", "api": "GRUPO_META isolado", "coberturaPct": 0.0},
            {"dominio": "Produtividade", "negocio": "Oficial UI", "api": "Proxy inferido", "coberturaPct": 50.0},
            {"dominio": "Participação", "negocio": "Oficial UI", "api": "Calculável/inferido", "coberturaPct": 50.0},
        ]
        business_avg = mean([m["coberturaPct"] for m in matrix] + [f034_avg, d01_pct]) if matrix else 0.0
        return {
            "matrix": matrix,
            "f034bApiCoveragePct": _clamp(f034_avg),
            "d01ReconstructionPct": d01_pct,
            "d02PrestacaoPct": d02_pct,
            "businessCoveragePct": _clamp(business_avg),
            "evidence": ["d01", "d02", "f03_4b", "D00 catalogs"],
        }

    def _prestacao_gap(self, layers: dict[str, Any]) -> dict[str, Any]:
        gap = (layers["d02"].get("prestacaoGapAnalysis") or {})
        fields = gap.get("fields") or {}
        f034_pdf = ((layers["f034b"].get("prestacaoVsApi") or {}).get("pdfNotInApi") or [])
        rows = []
        for name in PRESTACAO_FIELDS:
            spec = fields.get(name) or {}
            rows.append(
                {
                    "campo": name,
                    "equivalenteApi": bool(spec.get("api")),
                    "proxy": bool(spec.get("calculavel")),
                    "inferencia": bool(spec.get("inferivel")),
                    "naoExiste": name in (gap.get("inexistenteApi") or []) or name in f034_pdf,
                    "origem": spec.get("origem", "—"),
                }
            )
        return {
            "fields": rows,
            "exclusivoPrestacao": gap.get("exclusivoPrestacao") or [],
            "calculaveis": gap.get("calculavel") or [],
            "inferiveis": gap.get("inferivel") or [],
            "inexistentesApi": gap.get("inexistenteApi") or [],
            "coberturaD02Pct": _f(gap.get("coberturaD02Pct"), 97.5),
            "atinge100": bool(gap.get("atinge100")),
            "naoAtinge100": not bool(gap.get("atinge100", False)),
            "evidence": ["d02_hidden_nominal_layer.json", "f03_4b_prestacao_contas.json"],
        }

    def _people_challenge(self, layers: dict[str, Any], d04_ex: dict[str, Any]) -> dict[str, Any]:
        d04_claim = _f(d04_ex.get("7_coberturaPessoas"), 100)
        d02_ex = layers["d02_ex"]
        catalog = _f((layers["d02"].get("employeeNominalDiscovery") or {}).get("funcionarioCatalogCount"), 84)
        tecnica = 100.0 if d02_ex.get("1_funcionarioNomeEndpoint") else 70.0
        operacional = _clamp(
            mean(
                [
                    100.0 if d02_ex.get("9_operadoresNominalizaveis") else 60.0,
                    50.0 if not d02_ex.get("4_produtividadeOficial") else 100.0,
                    50.0 if not d02_ex.get("5_participacaoOficial") else 100.0,
                ]
            )
        )
        gerencial = _clamp(
            mean(
                [
                    0.0 if not d02_ex.get("7_metaOperacional") else 100.0,
                    0.0 if not d02_ex.get("8_rankingOficial") else 100.0,
                    100.0 if d02_ex.get("2_cpfOperador") else 50.0,
                ]
            )
        )
        real_people = _clamp(mean([tecnica, operacional, gerencial]))
        return {
            "d04ClaimPct": d04_claim,
            "d04ClaimMeaning": "100% dos operadores presentes nos snapshots F04.1/F04.2 — não 100% da equipe nem métricas gerenciais UI",
            "funcionariosCatalogo": int(catalog),
            "coberturaTecnicaPct": tecnica,
            "coberturaOperacionalPct": operacional,
            "coberturaGerencialPct": gerencial,
            "coberturaRealPct": real_people,
            "deltaVsD04": _round2(d04_claim - real_people),
            "produtividadeOficialApi": bool(d02_ex.get("4_produtividadeOficial")),
            "participacaoOficialApi": bool(d02_ex.get("5_participacaoOficial")),
            "metaOperacionalApi": bool(d02_ex.get("7_metaOperacional")),
        }

    def _financial_gap(self, layers: dict[str, Any], d04_ex: dict[str, Any]) -> dict[str, Any]:
        d04_claim = _f(d04_ex.get("4_coberturaFinanceira"), 100)
        rows = [
            {
                "item": name,
                "endpoint": endpoint,
                "ui": ui,
                "logos": logos,
                "coberturaPct": _level_score(logos if logos != "yes" else ui),
            }
            for name, endpoint, ui, _biz, logos in FINANCIAL_GAP_CHECKS
        ]
        real = _clamp(mean(r["coberturaPct"] for r in rows))
        dre_ok = bool((layers["d04"].get("financialCoverageAudit") or {}).get("dreValidacaoOk"))
        return {
            "d04ClaimPct": d04_claim,
            "d04ClaimMeaning": "100% dos 6 campos finance_center snapshot — não 100% dos movimentos UI",
            "gaps": rows,
            "coberturaRealPct": real,
            "deltaVsD04": _round2(d04_claim - real),
            "dreValidacaoOk": dre_ok,
        }

    def _operational_gap(self, layers: dict[str, Any], d04_ex: dict[str, Any]) -> dict[str, Any]:
        d04_claim = _f(d04_ex.get("6_coberturaVendas"), 100)
        rows = [
            {"item": name, "fonte": src, "ui": ui, "logos": logos, "coberturaPct": _level_score(logos)}
            for name, src, ui, _biz, logos in OPERATIONAL_GAP_CHECKS
        ]
        real = _clamp(mean(r["coberturaPct"] for r in rows))
        sales_cells = (layers["d04"].get("salesCoverageAudit") or {})
        return {
            "d04ClaimPct": d04_claim,
            "d04ClaimMeaning": "100% células F04.3 com operador — não 100% eventos PDV/LMC/autorização",
            "gaps": rows,
            "coberturaRealPct": real,
            "deltaVsD04": _round2(d04_claim - real),
            "vendasComOperador": sales_cells.get("vendasComOperador"),
            "totalCelulas": sales_cells.get("totalCelulas"),
        }

    def _hidden_endpoints(self, layers: dict[str, Any]) -> dict[str, Any]:
        probe = layers["network_probe"]
        consumed_paths = {ENDPOINTS[k] for k in LOGOS_CONSUMED_KEYS if k in ENDPOINTS}
        never = []
        partial = []
        blocked = []
        strategic = []
        for item in probe:
            path = item.get("path") or ""
            status = item.get("httpStatus")
            recs = item.get("registros") or 0
            entry = {"endpoint": item.get("endpoint"), "path": path, "httpStatus": status, "registros": recs}
            if status == 401:
                blocked.append(entry)
            elif path not in consumed_paths and recs:
                never.append(entry)
            elif path in consumed_paths and recs == 0:
                partial.append(entry)
            elif path not in consumed_paths and status == 200:
                strategic.append(entry)
        d02_probes = (layers["d02"].get("nominalEndpointProbes") or [])
        for p in d02_probes:
            if p.get("httpStatus") == 401 and p.get("path") not in {b["path"] for b in blocked}:
                blocked.append(
                    {
                        "endpoint": p.get("endpoint"),
                        "path": p.get("path"),
                        "httpStatus": 401,
                        "registros": 0,
                        "source": "D02",
                    }
                )
        return {
            "neverConsumed": never[:15],
            "partiallyConsumed": partial[:10],
            "blocked401": blocked[:15],
            "strategicPotential": strategic[:10],
            "totals": {
                "neverConsumed": len(never),
                "partiallyConsumed": len(partial),
                "blocked401": len(blocked),
                "strategicPotential": len(strategic),
            },
            "evidence": ["D00 webposto_network_probe", "D01", "D02"],
        }

    def _trust_challenge(self, layers: dict[str, Any], business: dict[str, Any], people: dict, fin: dict, ops: dict) -> dict[str, Any]:
        d04_ex = layers["d04_ex"]
        trust_tecnico = _f(d04_ex.get("17_trustCorporativo"), 100)
        trust_negocio = _clamp(business["businessCoveragePct"])
        confianca_doc = _f(((layers["f034b"].get("documentLineage") or {}).get("confiancaPct")), 88.6)
        trust_executivo = _clamp(min(trust_negocio, confianca_doc, people["coberturaRealPct"], fin["coberturaRealPct"], ops["coberturaRealPct"]))
        gap = _round2(trust_tecnico - trust_negocio)
        return {
            "d04TrustCorporativo": trust_tecnico,
            "trustTecnico": trust_tecnico,
            "trustTecnicoBand": _trust_band(trust_tecnico),
            "trustNegocio": trust_negocio,
            "trustNegocioBand": _trust_band(trust_negocio),
            "trustExecutivo": trust_executivo,
            "trustExecutivoBand": _trust_band(trust_executivo),
            "gapTecnicoVsNegocio": gap,
            "d04Trust100IsTechnicalOnly": trust_tecnico >= 90 and trust_negocio < 90,
            "formula": "Trust Executivo = min(Negócio, Prestação confiança, Pessoas real, Financeiro real, Operacional real)",
        }

    def _qa_certification(self, layers: dict[str, Any], trust: dict[str, Any], prestacao: dict) -> dict[str, Any]:
        d04_ex = layers["d04_ex"]
        d04_claims_100 = all(
            _f(d04_ex.get(k), 0) >= 99.9
            for k in (
                "4_coberturaFinanceira",
                "5_coberturaCaixa",
                "6_coberturaVendas",
                "7_coberturaPessoas",
                "17_trustCorporativo",
            )
        )
        gap_material = trust["gapTecnicoVsNegocio"] >= 15
        hidden = len(prestacao.get("inexistentesApi") or []) + _f(layers["d02_ex"].get("10_camposExclusivosSemOrigem"), 0)
        superestimou = d04_claims_100 and (gap_material or hidden > 0 or prestacao.get("naoAtinge100"))
        if superestimou:
            classification = "REFUTADO"
            d04_valid = "PARCIALMENTE CONFIRMADO"
        elif trust["trustExecutivo"] >= 75:
            classification = "CONFIRMADO"
            d04_valid = "CONFIRMADO"
        else:
            classification = "PARCIALMENTE CONFIRMADO"
            d04_valid = "PARCIALMENTE CONFIRMADO"
        return {
            "d04SuperestimouCobertura": superestimou,
            "classificacaoD04": classification,
            "d04ValidoCamadaTecnica": trust["trustTecnico"] >= 75,
            "d04ValidoCamadaNegocio": trust["trustNegocio"] >= 75,
            "certificacao": d04_valid,
            "evidenciasRefutacao": {
                "gapTrustTecnicoNegocio": trust["gapTecnicoVsNegocio"],
                "camposSemOrigemApi": hidden,
                "prestacaoAtinge100": prestacao.get("atinge100"),
                "d04ProntoDecisoesAutomatizadas": bool(d04_ex.get("20_prontoDecisoesAutomatizadas")),
            },
        }

    def _indicators_review(self, layers: dict[str, Any], trust: dict[str, Any], qa: dict) -> dict[str, Any]:
        inferidos = [
            "participacaoIndividual",
            "produtividadeFuncionario",
            "fundoCaixa (rótulo UI)",
            "growthScore (F04.7 proxy)",
            "goalPercentual parcial",
        ]
        comprovados = [
            "Cash paridade Δ=0",
            "Receita operacional F04.3",
            "Join venda-operador D01",
            "Finance center despesas/títulos snapshot",
            "Employee ledger F03.3",
        ]
        rebaixar = []
        bloquear = []
        if trust["trustNegocio"] < 90:
            rebaixar.extend(["People Coverage D04", "Sales Coverage D04", "Financial Coverage D04"])
        if not layers["d02_ex"].get("7_metaOperacional"):
            bloquear.append("metaFuncionario / Metas operacionais")
        if not layers["d02_ex"].get("5_participacaoOficial"):
            bloquear.append("participacaoIndividual oficial UI")
        if qa["d04SuperestimouCobertura"]:
            rebaixar.append("Corporate Trust D04 (executivo)")
        f047 = layers["f047_ex"]
        f050 = layers["f050_ex"]
        return {
            "camposOcultos": list(PRESTACAO_FIELDS) + ["layoutOperacionalTurno", "autorizacaoGerencial"],
            "indicadoresInferidos": inferidos,
            "indicadoresComprovados": comprovados,
            "indicadoresRebaixados": rebaixar,
            "indicadoresBloqueados": bloquear,
            "corporateScoreConfiavel": _f(f050.get("1_corporateScore"), 0) > 0 and trust["trustExecutivo"] >= 60,
            "executiveScoreConfiavel": _f(f047.get("1_executiveScore"), 0) > 0 and trust["trustExecutivo"] >= 60,
            "peopleScoreConfiavel": _f(f047.get("3_peopleScore"), 0) > 0 and trust["trustExecutivo"] >= 60,
        }

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        t0 = time.perf_counter()
        if empresa_codigo is not None and int(empresa_codigo) not in AUTHORIZED_FILIAIS:
            return WebPostoResponse.fail(f"Filial {empresa_codigo} fora do escopo D04.1 ({AUTHORIZED_FILIAIS})")

        layers = self._load_layers()
        d04_ex = layers["d04_ex"]
        if not d04_ex:
            return WebPostoResponse.fail("Baseline D04 ausente — execute audit_d04_live_data_truth_baseline.py")

        technical = self._technical_coverage(layers)
        business = self._business_coverage(layers)
        prestacao = self._prestacao_gap(layers)
        people = self._people_challenge(layers, d04_ex)
        financial = self._financial_gap(layers, d04_ex)
        operational = self._operational_gap(layers, d04_ex)
        hidden = self._hidden_endpoints(layers)
        trust = self._trust_challenge(layers, business, people, financial, operational)
        qa = self._qa_certification(layers, trust, prestacao)
        indicators = self._indicators_review(layers, trust, qa)

        pronto_decisoes = (
            qa["certificacao"] == "CONFIRMADO"
            and trust["trustExecutivo"] >= 75
            and not qa["d04SuperestimouCobertura"]
        )

        executive = {
            "1_d04ContinuaValido": qa["certificacao"] in ("CONFIRMADO", "PARCIALMENTE CONFIRMADO"),
            "2_trust100Real": trust["trustTecnico"] >= 99 and trust["trustNegocio"] >= 99,
            "3_trust100ApenasTecnico": trust["d04Trust100IsTechnicalOnly"],
            "4_coberturaRealNegocio": business["businessCoveragePct"],
            "5_coberturaRealPessoas": people["coberturaRealPct"],
            "6_coberturaRealFinanceira": financial["coberturaRealPct"],
            "7_coberturaRealOperacional": operational["coberturaRealPct"],
            "8_coberturaRealPrestacao": prestacao["coberturaD02Pct"],
            "9_camposOcultos": indicators["camposOcultos"],
            "10_indicadoresInferidos": indicators["indicadoresInferidos"],
            "11_indicadoresComprovados": indicators["indicadoresComprovados"],
            "12_indicadoresRebaixados": indicators["indicadoresRebaixados"],
            "13_indicadoresBloqueados": indicators["indicadoresBloqueados"],
            "14_corporateScoreConfiavel": indicators["corporateScoreConfiavel"],
            "15_executiveScoreConfiavel": indicators["executiveScoreConfiavel"],
            "16_peopleScoreConfiavel": indicators["peopleScoreConfiavel"],
            "17_logosEnxerga100Operacao": operational["coberturaRealPct"] >= 99,
            "18_logosEnxerga100Pessoas": people["coberturaRealPct"] >= 99,
            "19_prontoDecisoesAutomatizadas": pronto_decisoes,
            "20_d04ConfirmadoOuSuperestimado": "CONFIRMADO" if qa["certificacao"] == "CONFIRMADO" else "SUPERESTIMADO",
            "authorizedFiliais": list(AUTHORIZED_FILIAIS),
        }

        parecer = (
            "[PARECER FINAL: D04 CONFIRMADO]"
            if qa["certificacao"] == "CONFIRMADO" and not qa["d04SuperestimouCobertura"]
            else "[PARECER FINAL: D04 SUPERESTIMOU A COBERTURA]"
        )

        payload = {
            "sprint": "D04.1",
            "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
            "authorizedFiliais": list(AUTHORIZED_FILIAIS),
            "elapsedMs": round((time.perf_counter() - t0) * 1000, 1),
            "fonte": {"webPostoLive": False, "auditsOnly": True, "adversarial": True},
            "technicalCoverageAudit": technical,
            "businessCoverageAudit": business,
            "prestacaoGapAudit": prestacao,
            "peopleCoverageChallenge": people,
            "financialGapAudit": financial,
            "operationalGapAudit": operational,
            "hiddenEndpointDiscovery": hidden,
            "trustScoreChallenge": trust,
            "qaCertification": qa,
            "indicatorsReview": indicators,
            "executiveAnswers": executive,
            "parecerFinal": parecer,
            "oQueSabemos": {
                "snapshotsHomologados": "Paridade Δ=0 · joins D01 comprovados · finance/cash/vendas nos snapshots",
                "limites": "Trust D04 mede completude do pipeline capturado, não universo UI WebPosto",
            },
            "oQueAchamosQueSabemos": {
                "people100": "Operadores no snapshot F04 — não equipe completa nem métricas gerenciais UI",
                "prestacao975": "Campos mapeados — 2 exclusivos UI sem API · 3 inferidos",
            },
            "oQueNaoSabemos": {
                "autorizacaoGerencial": "Sem endpoint token",
                "lmcDetalhe": "LMC rede parcial/bloqueado",
                "metaFuncionarioTurno": "GRUPO_META sem vínculo turno oficial",
                "redeCompleta": "Escopo limitado filiais 11495/5555",
            },
        }
        return WebPostoResponse.ok(payload)
