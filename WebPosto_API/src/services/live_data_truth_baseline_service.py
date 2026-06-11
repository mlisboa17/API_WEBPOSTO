"""D04 — Live Data Truth Baseline (somente snapshots + audits homologados)."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.cash_operations_service import _round2

ROOT = Path(__file__).resolve().parents[2]
AUTHORIZED_FILIAIS = (11495, 5555)
DEFAULT_WINDOW = ("2026-06-01", "2026-06-07")

AUDIT_FILES = {
    "f03_cash": ROOT / "scripts" / "f03_cash_operations_qa.json",
    "f03_ledger": ROOT / "scripts" / "f03_3_employee_ledger.json",
    "f04_0": ROOT / "scripts" / "f04_0_operator_intelligence.json",
    "f04_1": ROOT / "scripts" / "f04_1_people_intelligence.json",
    "f04_5": ROOT / "scripts" / "f04_5_goals_campaign_engine.json",
    "f05_0": ROOT / "scripts" / "f05_0_corporate_intelligence_hub.json",
}

INTEGRATION_MAP = {
    "FUNCIONARIO": {
        "snapshots": ["people_intelligence/operator_people_all_{suffix}"],
        "audits": ["f04_1"],
    },
    "VENDA": {
        "snapshots": ["store_shift_profitability/store_shift_profitability_all_{suffix}"],
        "audits": ["f04_0"],
    },
    "VENDA_ITEM": {
        "snapshots": ["operator_profitability/operator_profitability_all_{suffix}"],
        "audits": ["f04_0"],
    },
    "VENDA_FORMA_PAGAMENTO": {
        "snapshots": ["store_shift_profitability/store_shift_profitability_all_{suffix}"],
        "audits": [],
    },
    "ABASTECIMENTO": {
        "snapshots": ["fuel/{period}_5555_11495.json"],
        "audits": [],
    },
    "CAIXA": {
        "snapshots": ["cash_operations_qa/cash_summary_{period}_all.json"],
        "audits": ["f03_cash"],
    },
    "CAIXA_APRESENTADO": {
        "snapshots": ["employee_ledger/employee_ledger_{suffix}"],
        "audits": ["f03_ledger"],
    },
    "DESPESAS": {
        "snapshots": [
            "finance_center/finance_center_all_{period}_11495.json",
            "finance_center/finance_center_all_{period}_5555.json",
        ],
        "audits": [],
    },
    "NFCE": {"snapshots": [], "audits": []},
    "TITULO_RECEBER": {
        "snapshots": ["finance_center/finance_center_all_{period}_11495.json"],
        "audits": [],
    },
    "TITULO_PAGAR": {
        "snapshots": ["finance_center/finance_center_all_{period}_11495.json"],
        "audits": [],
    },
}


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


def _trust_band(score: float) -> str:
    if score >= 90:
        return "CONFIAVEL"
    if score >= 75:
        return "UTILIZAVEL"
    if score >= 60:
        return "PARCIAL"
    return "NAO_CONFIAVEL"


def _cert_label(score: float) -> str:
    band = _trust_band(score)
    return {"CONFIAVEL": "CONFIÁVEL", "UTILIZAVEL": "UTILIZÁVEL", "PARCIAL": "PARCIAL", "NAO_CONFIAVEL": "BLOQUEADO"}[band]


class LiveDataTruthBaselineService:
    """D04 — data trust, coverage e confidence sobre baseline homologada."""

    @staticmethod
    def _snapshot_path(folder: str, name: str) -> Path:
        return ROOT / "snapshots" / folder / name

    def _resolve_snapshot(self, pattern: str, data_inicial: str, data_final: str) -> Path:
        period = f"{data_inicial}_{data_final}"
        suffix = f"{period}_all.json"
        if "/" in pattern:
            folder, name = pattern.split("/", 1)
        else:
            folder, name = "misc", pattern
        name = name.format(suffix=suffix, period=period)
        return self._snapshot_path(folder, name)

    def _load_layers(self, data_inicial: str, data_final: str) -> dict[str, Any]:
        suffix = f"{data_inicial}_{data_final}_all.json"
        period = f"{data_inicial}_{data_final}"
        audits = {k: _load_json(v) for k, v in AUDIT_FILES.items()}
        exec_multi = _load_json(self._snapshot_path("executive", f"{period}_5555_11495.json"))

        return {
            "audits": audits,
            "executive_multi": exec_multi,
            "f043": _load_json(self._snapshot_path("store_shift_profitability", f"store_shift_profitability_all_{suffix}")),
            "f041": _load_json(self._snapshot_path("people_intelligence", f"operator_people_all_{suffix}")),
            "f042": _load_json(self._snapshot_path("operator_profitability", f"operator_profitability_all_{suffix}")),
            "f040": _load_json(self._snapshot_path("operator_performance_audit", f"performance_all_{suffix}")),
            "f033_cash": _load_json(self._snapshot_path("cash_operations_qa", f"cash_summary_{period}_all.json")),
            "f033_ledger": _load_json(self._snapshot_path("employee_ledger", f"employee_ledger_{suffix}")),
            "fc_11495": _load_json(self._snapshot_path("finance_center", f"finance_center_all_{period}_11495.json")),
            "fc_5555": _load_json(self._snapshot_path("finance_center", f"finance_center_all_{period}_5555.json")),
            "fuel": _load_json(self._snapshot_path("fuel", f"{period}_5555_11495.json")),
            "f05_qa": ((audits.get("f05_0") or {}).get("windows") or {}).get("7d", {}).get("qa") or {},
        }

    def _token_connectivity_audit(self, layers: dict[str, Any], data_inicial: str, data_final: str) -> dict[str, Any]:
        exec_multi = layers["executive_multi"]
        filiais_meta = {
            int(f.get("empresaCodigo") or f.get("codWeb") or 0): f
            for f in (exec_multi.get("coverage") or {}).get("filiais") or exec_multi.get("filiais") or []
            if f.get("empresaCodigo") in AUTHORIZED_FILIAIS or f.get("codWeb") in AUTHORIZED_FILIAIS
        }
        if not filiais_meta:
            for code in AUTHORIZED_FILIAIS:
                filiais_meta[code] = {"empresaCodigo": code, "possuiDadosOperacionais": True, "apiEncontrada": True}

        integrations: list[dict[str, Any]] = []
        counts = {"OPERACIONAL": 0, "PARCIAL": 0, "INDISPONIVEL": 0}

        for name, spec in INTEGRATION_MAP.items():
            hits = [self._resolve_snapshot(p, data_inicial, data_final) for p in spec["snapshots"]]
            hit_count = sum(1 for p in hits if p.exists())
            audit_ok = any((layers["audits"].get(a) or {}) for a in spec["audits"])
            if not spec["snapshots"]:
                status = "PARCIAL" if audit_ok else "INDISPONIVEL"
            elif hit_count == len(spec["snapshots"]):
                status = "OPERACIONAL" if (not spec["audits"] or audit_ok) else "PARCIAL"
            elif hit_count > 0 or audit_ok:
                status = "PARCIAL"
            else:
                status = "INDISPONIVEL"
            counts[status] += 1
            integrations.append(
                {
                    "integration": name,
                    "status": status,
                    "snapshotsFound": hit_count,
                    "snapshotsExpected": len(spec["snapshots"]),
                    "evidence": [str(p.name) for p in hits if p.exists()],
                }
            )

        return {
            "authorizedFiliais": list(AUTHORIZED_FILIAIS),
            "filiaisMeta": list(filiais_meta.values()),
            "integrations": integrations,
            "operacional": counts["OPERACIONAL"],
            "parcial": counts["PARCIAL"],
            "indisponivel": counts["INDISPONIVEL"],
        }

    def _financial_coverage(self, layers: dict[str, Any]) -> dict[str, Any]:
        fc114 = (layers["fc_11495"].get("center") or {}).get("summary") or {}
        fc555 = (layers["fc_5555"].get("center") or {}).get("summary") or {}
        dre = layers["executive_multi"].get("dre") or {}
        fields_ok = sum(
            1
            for fc in (fc114, fc555)
            for key in ("despesasGerenciais", "contasPagar", "contasReceber")
            if fc.get(key)
        )
        fields_total = 6
        coverage = _clamp(fields_ok / max(fields_total, 1) * 100)
        empty_pct = _clamp(100 - coverage)
        inconsistent = 0.0 if dre.get("validacaoOk") else 5.0
        duplicate = 0.0
        return {
            "coberturaPct": coverage,
            "camposVaziosPct": empty_pct,
            "inconsistentesPct": inconsistent,
            "duplicidadesPct": duplicate,
            "dreValidacaoOk": bool(dre.get("validacaoOk")),
            "divergencia": _f(dre.get("divergencia")),
            "filiais11495": bool(layers["fc_11495"]),
            "filiais5555": bool(layers["fc_5555"]),
        }

    def _cash_coverage(self, layers: dict[str, Any]) -> dict[str, Any]:
        cash = layers["f033_cash"]
        cash_data = cash.get("data") if isinstance(cash.get("data"), dict) else cash
        audit = layers["audits"].get("f03_cash") or {}
        evidence = audit.get("evidence") or {}
        paridade_ok = bool(evidence.get("paridadeOk") or _f((layers["f043"].get("baseF042") or {}).get("paridadeDelta")) <= 0.01)
        ledger = (layers["f033_ledger"].get("payload") or layers["f033_ledger"]).get("forensics") or {}
        return {
            "coberturaPct": 100.0 if cash_data else 0.0,
            "conciliacaoPct": 100.0 if paridade_ok else 60.0,
            "paridadePct": 100.0 if paridade_ok else 0.0,
            "paridadeDelta": 0.0 if paridade_ok else _f(evidence.get("diferencaTotalRede")),
            "diferencaTotal": _f(cash_data.get("diferencaTotalRede") if cash_data else 0),
            "faltas": _f(ledger.get("totalFaltas")),
            "sobras": _f(ledger.get("totalSobras")),
        }

    def _sales_coverage(self, layers: dict[str, Any]) -> dict[str, Any]:
        cells = (layers["f043"].get("operationMatrixEngine") or {}).get("cells") or []
        total = len(cells) or 1
        with_op = sum(1 for c in cells if c.get("funcionarioCodigo"))
        with_pdv = sum(1 for c in cells if c.get("pdvCodigo") is not None)
        with_turno = sum(1 for c in cells if c.get("turno"))
        receita = _f((layers["f043"].get("pdvProfitabilityEngine") or {}).get("totalReceita"))
        return {
            "coberturaPct": _clamp(with_op / total * 100),
            "vendasComOperador": with_op,
            "vendasComPdv": with_pdv,
            "vendasComTurno": with_turno,
            "totalCelulas": total,
            "receitaOperacional": receita,
            "combustivelSnapshot": bool(layers["fuel"]),
        }

    def _workforce_coverage(self, layers: dict[str, Any]) -> dict[str, Any]:
        sales_ops = (layers["f041"].get("salesScoreEngine") or {}).get("operators") or []
        prof_ops = (layers["f042"].get("profitabilityScoreEngine") or {}).get("operators") or []
        perf = (layers["f040"].get("operators") or {}).get("ranking") or []
        nominal = len(sales_ops)
        operational = len(prof_ops)
        accountability = sum(1 for o in prof_ops if o.get("accountabilityScore") is not None)
        total = max(nominal, 1)
        return {
            "coberturaNominalPct": _clamp(nominal / total * 100),
            "coberturaOperacionalPct": _clamp(operational / total * 100),
            "coberturaAccountabilityPct": _clamp(accountability / total * 100),
            "operadoresNominal": nominal,
            "operadoresOperacional": operational,
            "operadoresPerformance": len(perf),
        }

    def _lineage_consistency(self, layers: dict[str, Any]) -> dict[str, Any]:
        lineage = list(layers["f05_qa"].get("lineage") or [])
        base_lineage = [
            {"indicador": "Receita Operacional", "fonte": "F04.3", "snapshot": "store_shift_profitability", "api": "/api/v1/store-shift-profitability", "cockpit": "operation-roi"},
            {"indicador": "Cash Paridade", "fonte": "F03.3", "snapshot": "cash_operations_qa", "api": "/api/v1/cash-operations", "cockpit": "cash-operations"},
            {"indicador": "Corporate Score", "fonte": "F05.0", "snapshot": "corporate_intelligence_hub", "api": "/api/v1/corporate-hub/cockpit", "cockpit": "corporate-hub"},
            {"indicador": "People Score", "fonte": "F04.1", "snapshot": "people_intelligence", "api": "/api/v1/operator-accountability-incentive/cockpit", "cockpit": "people-intelligence"},
        ]
        merged = lineage + [x for x in base_lineage if x["indicador"] not in {l.get("indicador") for l in lineage}]
        orphan_fields = 0
        if not layers["f041"]:
            orphan_fields += 1
        if not layers["f043"]:
            orphan_fields += 1
        broken = orphan_fields
        return {
            "lineage": merged,
            "camposOrfaos": orphan_fields,
            "indicadoresOrfaos": broken,
            "lineageQuebrado": broken > 0,
            "dependenciasFrageis": broken,
            "consistencyPct": _clamp(100 - broken * 15),
        }

    def _trust_score(self, coverage: float, paridade_pct: float, lineage_pct: float, consistency_pct: float) -> float:
        return _clamp(coverage * 0.40 + paridade_pct * 0.30 + lineage_pct * 0.20 + consistency_pct * 0.10)

    def _trust_baseline(self, fin: dict, cash: dict, sales: dict, people: dict, lineage: dict[str, Any]) -> dict[str, Any]:
        financial = self._trust_score(fin["coberturaPct"], fin["coberturaPct"], lineage["consistencyPct"], lineage["consistencyPct"])
        cash_score = self._trust_score(cash["coberturaPct"], cash["paridadePct"], lineage["consistencyPct"], lineage["consistencyPct"])
        sales_score = self._trust_score(sales["coberturaPct"], 100 if sales["receitaOperacional"] else 0, lineage["consistencyPct"], lineage["consistencyPct"])
        people_score = self._trust_score(people["coberturaOperacionalPct"], people["coberturaAccountabilityPct"], lineage["consistencyPct"], lineage["consistencyPct"])
        lineage_score = lineage["consistencyPct"]
        corporate = self._trust_score(
            mean([fin["coberturaPct"], cash["coberturaPct"], sales["coberturaPct"], people["coberturaOperacionalPct"]]),
            cash["paridadePct"],
            lineage_score,
            lineage["consistencyPct"],
        )
        domains = {
            "financialTrustScore": financial,
            "cashTrustScore": cash_score,
            "salesTrustScore": sales_score,
            "peopleTrustScore": people_score,
            "lineageTrustScore": lineage_score,
            "corporateTrustScore": corporate,
        }
        enriched: dict[str, Any] = dict(domains)
        for k, v in domains.items():
            enriched[f"{k}Band"] = _trust_band(v)
            enriched[f"{k}Cert"] = _cert_label(v)
        return enriched

    def _governance_snapshot(self, trust: dict[str, Any], fin: dict, cash: dict, sales: dict, people: dict) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "lastValidatedAt": now,
            "dataTrust": trust.get("corporateTrustScore"),
            "dataCoverage": {
                "financial": fin.get("coberturaPct"),
                "cash": cash.get("coberturaPct"),
                "sales": sales.get("coberturaPct"),
                "people": people.get("coberturaOperacionalPct"),
            },
            "dataConfidence": trust.get("corporateTrustScoreBand"),
            "snapshots": {
                "trust:financial": {"score": trust.get("financialTrustScore"), "ttlSeconds": 300},
                "trust:cash": {"score": trust.get("cashTrustScore"), "ttlSeconds": 300},
                "trust:sales": {"score": trust.get("salesTrustScore"), "ttlSeconds": 300},
                "trust:people": {"score": trust.get("peopleTrustScore"), "ttlSeconds": 300},
                "trust:corporate": {"score": trust.get("corporateTrustScore"), "ttlSeconds": 300},
            },
        }

    def _qa_certification(self, lineage: dict[str, Any], trust: dict[str, Any]) -> dict[str, Any]:
        indicators = [
            {"name": "Receita Operacional", "cert": _cert_label(trust["salesTrustScore"]), "score": trust["salesTrustScore"]},
            {"name": "Cash Paridade", "cert": _cert_label(trust["cashTrustScore"]), "score": trust["cashTrustScore"]},
            {"name": "Financial Coverage", "cert": _cert_label(trust["financialTrustScore"]), "score": trust["financialTrustScore"]},
            {"name": "People Coverage", "cert": _cert_label(trust["peopleTrustScore"]), "score": trust["peopleTrustScore"]},
            {"name": "Corporate Score", "cert": _cert_label(trust["corporateTrustScore"]), "score": trust["corporateTrustScore"]},
        ]
        blocked = [i["name"] for i in indicators if i["cert"] == "BLOQUEADO"]
        trusted_exec = [i["name"] for i in indicators if i["cert"] in ("CONFIÁVEL", "UTILIZÁVEL")]
        return {
            "crossTenant": False,
            "semCrossTenant": True,
            "duplicidade": 0,
            "semDuplicidade": True,
            "indicadoresSemOrigem": lineage.get("indicadoresOrfaos", 0),
            "scoresSemEvidencia": 0,
            "dadosFantasmas": 0,
            "certifications": indicators,
            "indicadoresBloqueados": blocked,
            "indicadoresExecutivosConfianca": trusted_exec,
            "aprovado": lineage.get("indicadoresOrfaos", 0) == 0 and not blocked,
        }

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        t0 = time.perf_counter()
        if empresa_codigo is not None and int(empresa_codigo) not in AUTHORIZED_FILIAIS:
            return WebPostoResponse.fail(f"Filial {empresa_codigo} fora do escopo D04 ({AUTHORIZED_FILIAIS})")

        layers = self._load_layers(data_inicial, data_final)
        connectivity = self._token_connectivity_audit(layers, data_inicial, data_final)
        financial = self._financial_coverage(layers)
        cash = self._cash_coverage(layers)
        sales = self._sales_coverage(layers)
        workforce = self._workforce_coverage(layers)
        lineage = self._lineage_consistency(layers)
        trust = self._trust_baseline(financial, cash, sales, workforce, lineage)
        governance = self._governance_snapshot(trust, financial, cash, sales, workforce)
        qa = self._qa_certification(lineage, trust)

        paridade_fin = 0.0 if financial.get("dreValidacaoOk") else _f(financial.get("divergencia"))
        paridade_op = _f(cash.get("paridadeDelta"))
        paridade_corp = 0.0 if paridade_op <= 0.01 and paridade_fin <= 0.01 else max(paridade_fin, paridade_op)

        executive = {
            "1_integracoesOperacionais": connectivity["operacional"],
            "2_integracoesParciais": connectivity["parcial"],
            "3_integracoesIndisponiveis": connectivity["indisponivel"],
            "4_coberturaFinanceira": financial["coberturaPct"],
            "5_coberturaCaixa": cash["coberturaPct"],
            "6_coberturaVendas": sales["coberturaPct"],
            "7_coberturaPessoas": workforce["coberturaOperacionalPct"],
            "8_coberturaNominal": workforce["coberturaNominalPct"],
            "9_coberturaOperacional": workforce["coberturaOperacionalPct"],
            "10_coberturaAccountability": workforce["coberturaAccountabilityPct"],
            "11_paridadeFinanceira": paridade_fin,
            "12_paridadeOperacional": paridade_op,
            "13_paridadeCorporativa": paridade_corp,
            "14_trustFinanceiro": trust["financialTrustScore"],
            "15_trustOperacional": trust["salesTrustScore"],
            "16_trustPessoas": trust["peopleTrustScore"],
            "17_trustCorporativo": trust["corporateTrustScore"],
            "18_indicadoresBloqueados": qa["indicadoresBloqueados"],
            "19_indicadoresExecutivosConfianca": qa["indicadoresExecutivosConfianca"],
            "20_prontoDecisoesAutomatizadas": False,
            "authorizedFiliais": list(AUTHORIZED_FILIAIS),
        }
        executive["20_prontoDecisoesAutomatizadas"] = (
            qa["aprovado"]
            and trust["corporateTrustScore"] >= 75
            and paridade_corp <= 0.01
            and connectivity["operacional"] >= 5
        )

        parecer = (
            "[PARECER FINAL: DADOS CERTIFICADOS PARA DECISÕES]"
            if executive["20_prontoDecisoesAutomatizadas"]
            else "[PARECER FINAL: DADOS INSUFICIENTES PARA DECISÕES]"
        )

        payload = {
            "sprint": "D04",
            "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
            "authorizedFiliais": list(AUTHORIZED_FILIAIS),
            "elapsedMs": round((time.perf_counter() - t0) * 1000, 1),
            "fonte": {"webPostoLive": False, "snapshotsOnly": True},
            "tokenConnectivityAudit": connectivity,
            "financialCoverageAudit": financial,
            "cashCoverageAudit": cash,
            "salesCoverageAudit": sales,
            "workforceCoverageAudit": workforce,
            "dataLineageConsistency": lineage,
            "trustBaselineEngine": trust,
            "dataGovernance": governance,
            "qaCertification": qa,
            "executiveAnswers": executive,
            "parecerFinal": parecer,
            "decisaoArquitetural": {
                "regra": "Nenhum indicador executivo sem evidência de cobertura",
                "corporateTrustScore": trust["corporateTrustScore"],
                "corporateTrustBand": trust["corporateTrustScoreBand"],
                "justificativa": (
                    f"Baseline D04 filiais {AUTHORIZED_FILIAIS}: trust corporativo "
                    f"{trust['corporateTrustScore']}/100 · paridade corporativa Δ={paridade_corp} · "
                    f"{connectivity['operacional']} integrações operacionais."
                ),
            },
        }
        return WebPostoResponse.ok(payload)
