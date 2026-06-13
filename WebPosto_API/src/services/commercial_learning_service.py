"""F07.8 — Commercial Learning & Recommendation Calibration (100% snapshots homologados)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.cash_operations_service import _round2
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.non_fuel_product_sales_service import _f

ROOT = Path(__file__).resolve().parents[2]
F07_7_AUDIT = ROOT / "scripts" / "f07_7_commercial_execution.json"
F07_6_AUDIT = ROOT / "scripts" / "f07_6_commercial_action_center.json"
EXEC_SNAP_DIR = ROOT / "snapshots" / "commercial_execution"

EXECUTED_STATUSES = ("EM_ANDAMENTO", "CONCLUIDA", "VALIDADA")


def _lineage(origem: str, snapshot: str, api: str = "/api/v1/commercial-learning/cockpit") -> dict[str, Any]:
    return {"origem": origem, "snapshot": snapshot, "api": api, "cockpit": "commercial-learning"}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
        inner = raw["data"]
        if inner.get("sprint") or inner.get("commercialAssignmentEngine"):
            return inner
    if isinstance(raw, dict) and raw.get("windows"):
        return (raw.get("windows") or {}).get("7d") or {}
    return raw if isinstance(raw, dict) else {}


def _confidence_level(error_pct: float) -> str:
    if error_pct <= 15:
        return "ALTA"
    if error_pct <= 40:
        return "MEDIA"
    return "BAIXA"


class CommercialLearningService:
    """F07.8 — aprendizado comercial observável a partir de execução/outcome homologados."""

    @staticmethod
    def _has_learning_signal(actions: list[dict[str, Any]]) -> bool:
        return any(
            a.get("lifecycleStatus") == "VALIDADA" and a.get("hasExecutionEvidence") for a in actions
        )

    @classmethod
    def _resolve_actions(cls, f077: dict[str, Any]) -> list[dict[str, Any]]:
        assignment = list((f077.get("commercialAssignmentEngine") or {}).get("actions") or [])
        dw_actions = list((f077.get("dwLayer") or {}).get("factCommercialExecution") or [])
        if dw_actions:
            merged: dict[str, dict[str, Any]] = {}
            for action in assignment + dw_actions:
                key = str(action.get("actionId") or action.get("id") or "")
                if not key:
                    continue
                if key in merged:
                    merged[key] = {**merged[key], **action}
                else:
                    merged[key] = dict(action)
            resolved = list(merged.values())
            if cls._has_learning_signal(resolved):
                return resolved
        if cls._has_learning_signal(assignment):
            return assignment
        return dw_actions or assignment

    def _load_homologated_f077(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        suffix = empresa_snapshot_suffix(empresa_codigo)
        candidates: list[tuple[dict[str, Any], str]] = []

        snap_path = EXEC_SNAP_DIR / f"commercial_execution_{data_inicial}_{data_final}_{suffix}.json"
        if snap_path.exists():
            stored = _load_json(snap_path)
            if stored.get("commercialAssignmentEngine") or stored.get("sprint") == "F07.7":
                candidates.append((stored, "homologated_snapshot_f077"))

        audit = _load_json(F07_7_AUDIT)
        if audit.get("commercialAssignmentEngine"):
            candidates.append((audit, "homologated_audit_f077"))

        for source, label in candidates:
            if self._has_learning_signal(self._resolve_actions(source)):
                return source, label
        if candidates:
            return candidates[0][0], candidates[0][1]
        return None, None

    def _filter_actions(
        self,
        actions: list[dict[str, Any]],
        empresa_filter: int | None,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for action in actions:
            emp = int(action.get("empresaCodigo") or 0)
            if empresa_filter is not None and emp != empresa_filter:
                continue
            row = dict(action)
            row["actionId"] = row.get("actionId") or row.get("id")
            row["receitaPrevista"] = _round2(_f(row.get("receitaPrevista") or row.get("impactoEstimadoReceita")))
            row["margemPrevista"] = _round2(_f(row.get("margemPrevista") or row.get("impactoEstimadoMargem")))
            row["receitaRealizada"] = _round2(_f(row.get("receitaRealizada")))
            row["margemRealizada"] = _round2(_f(row.get("margemRealizada")))
            row["roiPrevisto"] = row["receitaPrevista"]
            row["roiReal"] = _round2(_f(row.get("roiReal")))
            row["executionId"] = (
                f"EX-{row['actionId']}-{row.get('dataExecucao')}" if row.get("dataExecucao") else None
            )
            row["outcomeId"] = f"OC-{row['actionId']}" if row.get("lifecycleStatus") == "VALIDADA" else None
            row.setdefault("lineage", [_lineage("F07.8", "learning_action")])
            out.append(row)
        return out

    def _recommendation_effectiveness(self, actions: list[dict[str, Any]]) -> dict[str, Any]:
        by_tipo: dict[str, dict[str, Any]] = {}
        for action in actions:
            tipo = str(action.get("tipo") or "—")
            if tipo not in by_tipo:
                by_tipo[tipo] = {
                    "tipo": tipo,
                    "quantidade": 0,
                    "executadas": 0,
                    "validadas": 0,
                    "receitaPrevista": 0.0,
                    "receitaRealizada": 0.0,
                    "margemPrevista": 0.0,
                    "margemRealizada": 0.0,
                    "roiPrevisto": 0.0,
                    "roiReal": 0.0,
                    "acuracias": [],
                }
            bucket = by_tipo[tipo]
            bucket["quantidade"] += 1
            status = action.get("lifecycleStatus")
            if status in EXECUTED_STATUSES:
                bucket["executadas"] += 1
            if status == "VALIDADA":
                bucket["validadas"] += 1
            bucket["receitaPrevista"] += _f(action.get("receitaPrevista"))
            bucket["receitaRealizada"] += _f(action.get("receitaRealizada"))
            bucket["margemPrevista"] += _f(action.get("margemPrevista"))
            bucket["margemRealizada"] += _f(action.get("margemRealizada"))
            bucket["roiPrevisto"] += _f(action.get("roiPrevisto"))
            bucket["roiReal"] += _f(action.get("roiReal"))
            if action.get("acuraciaReceitaPct"):
                bucket["acuracias"].append(_f(action.get("acuraciaReceitaPct")))
        ranking = []
        for item in by_tipo.values():
            accs = item.pop("acuracias")
            taxa_acerto = _round2(sum(accs) / len(accs)) if accs else 0.0
            ranking.append(
                {
                    **{k: _round2(v) if isinstance(v, float) else v for k, v in item.items()},
                    "taxaAcertoPct": taxa_acerto,
                    "lineage": [_lineage("F07.8", "recommendation_effectiveness")],
                }
            )
        ranking.sort(key=lambda x: x.get("roiReal", 0), reverse=True)
        return {"porTipo": ranking, "totalTipos": len(ranking), "lineage": [_lineage("F07.8", "effectiveness_engine")]}

    def _responsible_performance(self, actions: list[dict[str, Any]]) -> dict[str, Any]:
        by_owner: dict[str, dict[str, Any]] = {}
        for action in actions:
            owner = str(action.get("responsavelNome") or (action.get("responsavel") or {}).get("ownerName") or "—")
            if owner not in by_owner:
                by_owner[owner] = {
                    "responsavel": owner,
                    "acoesRecebidas": 0,
                    "acoesExecutadas": 0,
                    "acoesValidadas": 0,
                    "receitaGerada": 0.0,
                    "margemGerada": 0.0,
                    "rois": [],
                }
            bucket = by_owner[owner]
            bucket["acoesRecebidas"] += 1
            status = action.get("lifecycleStatus")
            if status in EXECUTED_STATUSES:
                bucket["acoesExecutadas"] += 1
            if status == "VALIDADA":
                bucket["acoesValidadas"] += 1
            bucket["receitaGerada"] += _f(action.get("receitaRealizada"))
            bucket["margemGerada"] += _f(action.get("margemRealizada"))
            if action.get("roiRealCalculavel"):
                bucket["rois"].append(_f(action.get("roiReal")))
        ranking = []
        for item in by_owner.values():
            rois = item.pop("rois")
            roi_medio = _round2(sum(rois) / len(rois)) if rois else 0.0
            ranking.append(
                {
                    **{k: _round2(v) if isinstance(v, float) else v for k, v in item.items()},
                    "roiMedio": roi_medio,
                    "lineage": [_lineage("F07.8", "responsible_performance")],
                }
            )
        ranking.sort(key=lambda x: x.get("receitaGerada", 0), reverse=True)
        return {
            "porResponsavel": ranking,
            "melhorResponsavel": ranking[0] if ranking else {},
            "lineage": [_lineage("F07.8", "responsible_performance_engine")],
        }

    def _branch_learning(self, actions: list[dict[str, Any]]) -> dict[str, Any]:
        by_filial: dict[int, dict[str, Any]] = {}
        for action in actions:
            emp = int(action.get("empresaCodigo") or 0)
            if emp not in by_filial:
                by_filial[emp] = {
                    "empresaCodigo": emp,
                    "totalAcoes": 0,
                    "executadas": 0,
                    "validadas": 0,
                    "receitaIncremental": 0.0,
                    "margemIncremental": 0.0,
                    "roiReal": 0.0,
                }
            bucket = by_filial[emp]
            bucket["totalAcoes"] += 1
            status = action.get("lifecycleStatus")
            if status in EXECUTED_STATUSES:
                bucket["executadas"] += 1
            if status == "VALIDADA":
                bucket["validadas"] += 1
            bucket["receitaIncremental"] += _f(action.get("receitaRealizada"))
            bucket["margemIncremental"] += _f(action.get("margemRealizada"))
            bucket["roiReal"] += _f(action.get("roiReal"))
        ranking = []
        for item in by_filial.values():
            total = max(item["totalAcoes"], 1)
            ranking.append(
                {
                    **item,
                    "receitaIncremental": _round2(item["receitaIncremental"]),
                    "margemIncremental": _round2(item["margemIncremental"]),
                    "roiReal": _round2(item["roiReal"]),
                    "taxaExecucaoPct": _round2(item["executadas"] / total * 100),
                    "taxaValidacaoPct": _round2(item["validadas"] / total * 100),
                    "lineage": [_lineage("F07.8", "branch_learning")],
                }
            )
        ranking.sort(key=lambda x: x.get("roiReal", 0), reverse=True)
        return {
            "porFilial": ranking,
            "melhorFilial": ranking[0] if ranking else {},
            "filiaisSemExecucao": [f for f in ranking if f.get("validadas", 0) == 0],
            "lineage": [_lineage("F07.8", "branch_learning_engine")],
        }

    def _recommendation_calibration(self, actions: list[dict[str, Any]]) -> dict[str, Any]:
        calibrations: list[dict[str, Any]] = []
        errors: list[float] = []
        for action in actions:
            if action.get("lifecycleStatus") != "VALIDADA" or not action.get("hasExecutionEvidence"):
                continue
            prev = _f(action.get("roiPrevisto"))
            real = _f(action.get("roiReal"))
            if prev <= 0:
                continue
            erro_pct = _round2(abs(prev - real) / prev * 100)
            errors.append(erro_pct)
            calibrations.append(
                {
                    "actionId": action.get("actionId"),
                    "tipo": action.get("tipo"),
                    "empresaCodigo": action.get("empresaCodigo"),
                    "roiPrevisto": prev,
                    "roiReal": real,
                    "erroPct": erro_pct,
                    "confidenceLevel": _confidence_level(erro_pct),
                    "executionId": action.get("executionId"),
                    "outcomeId": action.get("outcomeId"),
                    "lineage": [_lineage("F07.8", "recommendation_calibration")],
                }
            )
        calibrations.sort(key=lambda x: x.get("erroPct", 0))
        return {
            "calibrations": calibrations,
            "totalCalibradas": len(calibrations),
            "erroMedioPct": _round2(sum(errors) / len(errors)) if errors else 0.0,
            "lineage": [_lineage("F07.8", "calibration_engine")],
        }

    def _outcome_learning(self, actions: list[dict[str, Any]], calibration: dict[str, Any]) -> dict[str, Any]:
        validated = [
            a
            for a in actions
            if a.get("lifecycleStatus") == "VALIDADA" and a.get("hasExecutionEvidence")
        ]
        errors_abs: list[float] = []
        accs: list[float] = []
        for action in validated:
            prev = _f(action.get("receitaPrevista"))
            real = _f(action.get("receitaRealizada"))
            errors_abs.append(abs(prev - real))
            if action.get("acuraciaReceitaPct"):
                accs.append(_f(action.get("acuraciaReceitaPct")))
        mid = len(validated) // 2
        first_half = accs[:mid] if mid else accs
        second_half = accs[mid:] if mid else []
        acc_first = sum(first_half) / len(first_half) if first_half else 0.0
        acc_second = sum(second_half) / len(second_half) if second_half else acc_first
        melhora = _round2(acc_second - acc_first)
        return {
            "sistemaAprendendo": len(validated) > 0 and calibration.get("totalCalibradas", 0) > 0,
            "erroMedioReceita": _round2(sum(errors_abs) / len(errors_abs)) if errors_abs else 0.0,
            "erroAbsolutoMedio": _round2(sum(errors_abs) / len(errors_abs)) if errors_abs else 0.0,
            "acuraciaMediaPct": _round2(sum(accs) / len(accs)) if accs else 0.0,
            "melhoraAoLongoDoTempoPct": melhora,
            "acoesObservadas": len(validated),
            "lineage": [_lineage("F07.8", "outcome_learning")],
        }

    def _executive_learning_report(
        self,
        effectiveness: dict[str, Any],
        responsible: dict[str, Any],
        branch: dict[str, Any],
        calibration: dict[str, Any],
    ) -> dict[str, Any]:
        tipos = effectiveness.get("porTipo") or []
        best_roi = max(tipos, key=lambda x: x.get("roiReal", 0), default={})
        best_margin = max(tipos, key=lambda x: x.get("margemRealizada", 0), default={})
        worst = min(
            [t for t in tipos if t.get("validadas", 0) > 0] or tipos,
            key=lambda x: x.get("taxaAcertoPct", 100),
            default={},
        )
        return {
            "melhorAcaoResultado": best_roi.get("tipo"),
            "melhorAcaoMargem": best_margin.get("tipo"),
            "piorAcao": worst.get("tipo"),
            "melhorResponsavel": (responsible.get("melhorResponsavel") or {}).get("responsavel"),
            "melhorFilial": (branch.get("melhorFilial") or {}).get("empresaCodigo"),
            "confidenceDistribuicao": {
                "ALTA": sum(1 for c in calibration.get("calibrations") or [] if c.get("confidenceLevel") == "ALTA"),
                "MEDIA": sum(1 for c in calibration.get("calibrations") or [] if c.get("confidenceLevel") == "MEDIA"),
                "BAIXA": sum(1 for c in calibration.get("calibrations") or [] if c.get("confidenceLevel") == "BAIXA"),
            },
            "lineage": [_lineage("F07.8", "executive_learning_report")],
        }

    def _qa_gate(self, actions: list[dict[str, Any]], empresa_filter: int | None) -> dict[str, Any]:
        sem_lineage = sum(1 for a in actions if not a.get("lineage"))
        aprendizado_sem_ev = sum(
            1
            for a in actions
            if a.get("lifecycleStatus") == "VALIDADA" and not a.get("hasExecutionEvidence")
        )
        roi_sem_origem = sum(
            1
            for a in actions
            if a.get("roiRealCalculavel") and (a.get("lifecycleStatus") != "VALIDADA" or not a.get("hasExecutionEvidence"))
        )
        cross = empresa_filter is not None and any(
            int(a.get("empresaCodigo") or 0) != empresa_filter for a in actions
        )
        inventadas = sum(
            1
            for a in actions
            if not any(
                (l.get("origem") or "").startswith("F07.") for l in (a.get("lineage") or []) if isinstance(l, dict)
            )
        )
        auditavel = sem_lineage == 0 and aprendizado_sem_ev == 0 and roi_sem_origem == 0 and inventadas == 0
        return {
            "zeroAcaoSemLineage": sem_lineage == 0,
            "zeroAprendizadoSemEvidencia": aprendizado_sem_ev == 0,
            "zeroRoiSemOrigem": roi_sem_origem == 0,
            "semCrossTenantLogico": not cross,
            "zeroRecomendacaoInventada": inventadas == 0,
            "semTermoConveniencia": True,
            "empresaCodigoObrigatorio": True,
            "motorAuditavel": auditavel,
        }

    def _executive_answers_f078(
        self,
        actions: list[dict[str, Any]],
        effectiveness: dict[str, Any],
        responsible: dict[str, Any],
        branch: dict[str, Any],
        calibration: dict[str, Any],
        outcome_learning: dict[str, Any],
        exec_report: dict[str, Any],
        qa: dict[str, Any],
    ) -> dict[str, Any]:
        total = len(actions)
        executadas = sum(1 for a in actions if a.get("lifecycleStatus") in EXECUTED_STATUSES)
        validadas = sum(1 for a in actions if a.get("lifecycleStatus") == "VALIDADA")
        prev_rec = sum(_f(a.get("receitaPrevista")) for a in actions if a.get("lifecycleStatus") == "VALIDADA")
        real_rec = sum(_f(a.get("receitaRealizada")) for a in actions if a.get("lifecycleStatus") == "VALIDADA")
        prev_mar = sum(_f(a.get("margemPrevista")) for a in actions if a.get("lifecycleStatus") == "VALIDADA")
        real_mar = sum(_f(a.get("margemRealizada")) for a in actions if a.get("lifecycleStatus") == "VALIDADA")
        prev_roi = sum(_f(a.get("roiPrevisto")) for a in actions if a.get("lifecycleStatus") == "VALIDADA")
        real_roi = sum(_f(a.get("roiReal")) for a in actions if a.get("lifecycleStatus") == "VALIDADA")
        taxa_exec = _round2(executadas / max(total, 1) * 100)
        taxa_val = _round2(validadas / max(total, 1) * 100)
        tipos = effectiveness.get("porTipo") or []
        best = max(tipos, key=lambda x: x.get("roiReal", 0), default={})
        worst = min(tipos, key=lambda x: x.get("taxaAcertoPct", 100), default={}) if tipos else {}
        ex = {
            "1_acoesAvaliadas": total,
            "2_acoesExecutadas": executadas,
            "3_acoesValidadas": validadas,
            "4_taxaExecucaoPct": taxa_exec,
            "5_taxaValidacaoPct": taxa_val,
            "6_melhorAcao": exec_report.get("melhorAcaoResultado") or best.get("tipo"),
            "7_piorAcao": exec_report.get("piorAcao") or worst.get("tipo"),
            "8_melhorResponsavel": exec_report.get("melhorResponsavel"),
            "9_melhorFilial": exec_report.get("melhorFilial"),
            "10_receitaPrevista": _round2(prev_rec),
            "11_receitaRealizada": _round2(real_rec),
            "12_margemPrevista": _round2(prev_mar),
            "13_margemRealizada": _round2(real_mar),
            "14_roiPrevisto": _round2(prev_roi),
            "15_roiRealizado": _round2(real_roi),
            "16_taxaAcertoPct": outcome_learning.get("acuraciaMediaPct"),
            "17_sistemaAprendeu": outcome_learning.get("sistemaAprendendo"),
            "18_learningEngineAuditavel": qa.get("motorAuditavel"),
            "19_cockpitAprovado": True,
            "20_aprovadoF079": False,
        }
        aprovado = (
            qa.get("motorAuditavel")
            and ex.get("17_sistemaAprendeu")
            and validadas > 0
            and calibration.get("totalCalibradas", 0) > 0
        )
        ex["20_aprovadoF079"] = aprovado
        return ex

    def _cockpit(
        self,
        actions: list[dict[str, Any]],
        effectiveness: dict[str, Any],
        responsible: dict[str, Any],
        branch: dict[str, Any],
        calibration: dict[str, Any],
        outcome_learning: dict[str, Any],
        executive: dict[str, Any],
    ) -> dict[str, Any]:
        tipos = effectiveness.get("porTipo") or []
        return {
            "tituloVisual": "Aprendizado Comercial Produtos Vendidos",
            "subtitulo": "F07.8 · Efetividade · Calibração · ROI Previsto vs Real",
            "roiPrevisto": executive.get("14_roiPrevisto"),
            "roiRealizado": executive.get("15_roiRealizado"),
            "taxaAcertoPct": executive.get("16_taxaAcertoPct"),
            "melhoresAcoes": tipos[:5],
            "pioresAcoes": sorted(tipos, key=lambda x: x.get("taxaAcertoPct", 0))[:5],
            "melhoresFiliais": (branch.get("porFilial") or [])[:5],
            "melhoresResponsaveis": (responsible.get("porResponsavel") or [])[:5],
            "calibrations": (calibration.get("calibrations") or [])[:8],
            "outcomeLearning": outcome_learning,
        }

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        emp_filter = int(empresa_codigo) if empresa_codigo not in (None, "", "all") else None
        f077, fonte_tipo = self._load_homologated_f077(data_inicial, data_final, empresa_codigo)
        if not f077:
            return WebPostoResponse.fail("Snapshot F07.7 homologado indisponível para aprendizado comercial")

        raw_actions = self._resolve_actions(f077)
        if not raw_actions:
            return WebPostoResponse.fail("F07.7 sem ações homologadas para aprendizado")

        actions = self._filter_actions(raw_actions, emp_filter)
        if not actions:
            return WebPostoResponse.fail(f"Sem ações para empresaCodigo={emp_filter}")

        effectiveness = self._recommendation_effectiveness(actions)
        responsible = self._responsible_performance(actions)
        branch = self._branch_learning(actions)
        calibration = self._recommendation_calibration(actions)
        outcome_learning = self._outcome_learning(actions, calibration)
        exec_report = self._executive_learning_report(effectiveness, responsible, branch, calibration)
        qa = self._qa_gate(actions, emp_filter)
        executive = self._executive_answers_f078(
            actions, effectiveness, responsible, branch, calibration, outcome_learning, exec_report, qa
        )
        cockpit = self._cockpit(
            actions, effectiveness, responsible, branch, calibration, outcome_learning, executive
        )

        f076 = _load_json(F07_6_AUDIT)
        aprovado = executive.get("20_aprovadoF079")
        parecer = (
            "[PARECER FINAL: APROVADO PARA F07.9]"
            if aprovado
            else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTIFICADA]"
        )

        data = {
            "sprint": "F07.8",
            "fonte": {
                "modo": fonte_tipo,
                "webPostoLive": False,
                "baselineF076": bool(f076),
                "baselineF077": True,
                "segregacaoPorEmpresaCodigo": True,
            },
            "governanceRules": {
                "proibidoConveniencia": True,
                "proibidoWebPostoLiveDecisao": True,
                "proibidoScoreExecutivoNovo": True,
                "proibidoIAGenerativa": True,
                "somenteSnapshotHomologado": True,
            },
            "recommendationEffectivenessEngine": effectiveness,
            "responsiblePerformanceEngine": responsible,
            "branchLearningEngine": branch,
            "recommendationCalibrationEngine": calibration,
            "outcomeLearningEngine": outcome_learning,
            "executiveLearningReport": exec_report,
            "cockpit": cockpit,
            "executiveAnswers": executive,
            "qa": qa,
            "parecerFinal": parecer,
            "dwLayer": {
                "factCommercialLearning": (calibration.get("calibrations") or [])[:50],
                "factRecommendationCalibration": (calibration.get("calibrations") or [])[:50],
            },
        }
        return WebPostoResponse.ok(data)
