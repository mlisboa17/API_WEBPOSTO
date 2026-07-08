"""DIR-01 — enriquecimento nominal de evidence_items."""

from __future__ import annotations

import logging
from collections import Counter
from decimal import Decimal
from typing import Any

import httpx

from src.core.config import load_core_config
from src.gateway.webposto_client import WebPostoClient
from src.services.decision_evidence.models import BeneficiaryVsReview, DecisionEvidenceItem
from src.services.decision_evidence.nominal_matcher import (
    MATCH_AMBIGUOUS,
    MATCH_NO_MATCH,
    MATCH_PROBABLE,
    NominalMatcher,
    PrestacaoNominalMatcher,
    build_nominal_candidates_from_screen_rows,
    build_prestacao_candidates,
    match_status_ui_label,
    resolve_employee_name,
)
from src.services.decision_evidence.prestacao_nominal_extractor import load_prestacao_nominal_items
from src.services.employee_dimension_service import EmployeeDimensionService
from src.services.expense_lineage_service import ExpenseLineageService
from src.services.expense_semantic_service import ExpenseSemanticService
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService
from src.services.prestacao_contas_intelligence_service import PrestacaoContasIntelligenceService

logger = logging.getLogger(__name__)

VALE_ENDPOINT_PATHS = (
    ("VALE_FUNCIONARIO_REDE", "/INTEGRACAO/VALE_FUNCIONARIO_REDE"),
    ("CONSULTAR_VALE_FUNCIONARIO_REDE", "/INTEGRACAO/CONSULTAR_VALE_FUNCIONARIO_REDE"),
)
PRESTACAO_PARSER = "PrestacaoContasIntelligenceService.vale_forensics"
PRESTACAO_MARKDOWN_PARSER = "prestacao_nominal_extractor.load_prestacao_nominal_items"


def _beneficiary_block(person_name: str | None) -> BeneficiaryVsReview:
    return BeneficiaryVsReview(
        beneficiary_available=bool(person_name),
        review_responsible=None,
        review_workflow_implemented=False,
    )


def _apply_match_to_item(
    item: DecisionEvidenceItem,
    match: Any,
    *,
    employee_index: dict[int, dict[str, Any]],
    prestacao_meta: dict[str, Any] | None = None,
) -> DecisionEvidenceItem:
    cand = match.candidate
    code = cand.funcionario_codigo if cand else None
    name = resolve_employee_name(code, employee_index)
    if not name and cand and cand.raw.get("person_name"):
        name = str(cand.raw.get("person_name"))
    elif not name and cand and cand.description and cand.source == "PRESTACAO_CONTAS":
        name = str(cand.description)
    if name:
        person = name
    elif code:
        person = f"Funcionário {code}"
    else:
        person = None

    item_limitations = list(item.limitations or [])
    item_limitations.extend(match.limitations)
    if match.status == MATCH_NO_MATCH and not person:
        item_limitations.append(
            "Beneficiário não identificado na fonte disponível para este lançamento."
        )
    if match.status == MATCH_AMBIGUOUS:
        item_limitations.append(
            "Mais de um beneficiário possível — requer conferência manual."
        )

    source_file = None
    source_page = None
    if prestacao_meta and cand and str(cand.source) == "PRESTACAO_CONTAS":
        source_file = prestacao_meta.get("source_file") or cand.raw.get("source_file")
        source_page = cand.raw.get("page_number")

    return item.model_copy(
        update={
            "funcionario_codigo": code,
            "person_name": person,
            "cash_register": str(cand.caixa_codigo) if cand and cand.caixa_codigo else item.cash_register,
            "shift": cand.turno if cand and cand.turno else item.shift,
            "match_status": match.status,
            "match_confidence": match.confidence,
            "nominal_source": cand.source if cand else None,
            "nominal_source_file": source_file,
            "nominal_source_page": source_page,
            "nominal_source_reference": cand.source_reference if cand else None,
            "matching_reason": match.reason or None,
            "limitations": item_limitations,
            "review_responsible": None,
            "beneficiary_vs_review": _beneficiary_block(person),
        }
    )


def _rows(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data", "items"):
            chunk = payload.get(key)
            if isinstance(chunk, list):
                return [r for r in chunk if isinstance(r, dict)]
    return []


class NominalEnrichmentService:
    """Enriquece evidence_items financeiros com dados nominais de CAIXA."""

    def __init__(self, client: WebPostoClient | None = None) -> None:
        self._client = client or WebPostoClient()
        self._overview = NetworkFinancialOverviewService(self._client)
        self._employees = EmployeeDimensionService(self._client)
        self._lineage = ExpenseLineageService(self._overview)
        self._semantic = ExpenseSemanticService()
        self._prestacao = PrestacaoContasIntelligenceService()

    async def _audit_vale_endpoints(
        self,
        *,
        period_start: str,
        period_end: str,
        empresa_codigo: int | None,
    ) -> dict[str, Any]:
        cfg = load_core_config()
        api_key = cfg.webposto_api_key
        probes: list[dict[str, Any]] = []
        async with httpx.AsyncClient(base_url=cfg.webposto_base_url, timeout=45.0) as http:
            for name, path in VALE_ENDPOINT_PATHS:
                params: dict[str, Any] = {
                    "dataInicial": period_start,
                    "dataFinal": period_end,
                    "CHAVE": api_key,
                }
                if empresa_codigo is not None:
                    params["empresaCodigo"] = empresa_codigo
                try:
                    resp = await http.get(path, params=params)
                    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None
                    rows = _rows(body)
                    probes.append(
                        {
                            "endpoint": name,
                            "path": path,
                            "method": "GET",
                            "empresaCodigo": empresa_codigo,
                            "http_status": resp.status_code,
                            "row_count": len(rows),
                            "sample_fields": sorted(rows[0].keys())[:20] if rows else [],
                        }
                    )
                except Exception as exc:
                    probes.append(
                        {
                            "endpoint": name,
                            "path": path,
                            "empresaCodigo": empresa_codigo,
                            "http_status": 0,
                            "error": str(exc)[:160],
                        }
                    )
        return {
            "endpoints": probes,
            "401_cause": (
                "HTTP 401 em /INTEGRACAO/VALE_FUNCIONARIO_REDE = endpoint sem permissão no token "
                "(Authorization), não rota incorreta — reproduzido para 5555, 11495 e 74014."
            ),
            "consultar_usable": any(
                p.get("http_status") == 200 for p in probes if p.get("endpoint") == "CONSULTAR_VALE_FUNCIONARIO_REDE"
            ),
            "consultar_rows_in_period": sum(
                p.get("row_count", 0)
                for p in probes
                if p.get("endpoint") == "CONSULTAR_VALE_FUNCIONARIO_REDE"
            ),
        }

    async def _audit_prestacao_vales(
        self,
        enriched_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        vf = self._prestacao.vale_forensics(enriched_rows)
        sample = vf.get("amostra") or []
        with_fn = sum(1 for row in sample if row.get("funcionarioCodigo") not in (None, "", 0))
        return {
            "parser_reused": PRESTACAO_PARSER,
            "vale_forensics_total": vf.get("total"),
            "sample_with_funcionario": with_fn,
            "can_enrich_line_level": with_fn > 0,
            "note": (
                "Prestação (camada API) agrega vales consolidados — amostra sem funcionarioCodigo "
                "para lançamentos financeiros desta categoria."
            ),
        }

    async def enrich_items(
        self,
        items: list[DecisionEvidenceItem],
        *,
        tenant_id: str,
        period_start: str,
        period_end: str,
    ) -> tuple[list[DecisionEvidenceItem], dict[str, Any]]:
        if not items:
            return items, {"nominal_sources_audited": [], "match_summary": {}}

        try:
            empresa = int(tenant_id)
        except (TypeError, ValueError):
            empresa = None

        filters = FinancialOverviewFilters(
            data_inicial=period_start,
            data_final=period_end,
            empresa_codigo=empresa,
        )

        screen_rows: list[dict[str, Any]] = []
        enriched_rows: list[dict[str, Any]] = []
        fetch_error: str | None = None
        try:
            screen_rows, err = await self._overview._load_screen_expenses(filters)
            if err and not err.success:
                fetch_error = str(err.error or err.message or "falha ao carregar despesas de tela")
            ctx = await self._lineage.build_context(self._overview, filters)
            enriched_rows = [
                self._semantic.classify_row(self._lineage.enrich_row(row, ctx)) for row in screen_rows
            ]
        except Exception as exc:
            fetch_error = str(exc)
            logger.warning(
                "DIR-01 nominal enrichment: falha screen/lineage tenant=%s err=%s",
                tenant_id,
                exc,
            )

        vale_audit = await self._audit_vale_endpoints(
            period_start=period_start,
            period_end=period_end,
            empresa_codigo=empresa,
        )
        prestacao_audit = await self._audit_prestacao_vales(enriched_rows)
        prestacao_items, prestacao_locate = load_prestacao_nominal_items(
            empresa_codigo=empresa or tenant_id,
            period_start=period_start,
            period_end=period_end,
            tenant_name=items[0].tenant_name if items else None,
        )
        prestacao_audit["markdown_extractor"] = PRESTACAO_MARKDOWN_PARSER
        prestacao_audit["locate"] = {
            k: prestacao_locate.get(k)
            for k in (
                "found",
                "source_gap",
                "path",
                "source_file",
                "empresa_codigo",
                "period_start",
                "period_end",
                "items_extracted",
                "reason",
            )
            if k in prestacao_locate
        }
        prestacao_audit["nominal_items_loaded"] = len(prestacao_items)
        prestacao_audit["can_enrich_from_markdown"] = bool(
            prestacao_locate.get("found") and prestacao_items
        )

        employee_index: dict[int, dict[str, Any]] = {}
        try:
            dim = await self._employees.build(period_start, period_end)
            employee_index = dim.get("index") or {}
        except Exception as exc:
            logger.warning("DIR-01 nominal enrichment: falha FUNCIONARIO err=%s", exc)

        candidates = build_nominal_candidates_from_screen_rows(screen_rows)
        matcher = NominalMatcher(candidates)
        prestacao_candidates = build_prestacao_candidates(prestacao_items)
        enriched: list[DecisionEvidenceItem] = []
        summary: dict[str, Any] = {
            "EXACT": 0,
            "PROBABLE": 0,
            "AMBIGUOUS": 0,
            "NO_MATCH": 0,
            "with_funcionario": 0,
            "with_caixa": 0,
            "with_turno": 0,
            "prestacao_enriched": 0,
            "total_with_funcionario_amount": 0.0,
            "total_without_funcionario_amount": 0.0,
        }

        first_pass: list[tuple[DecisionEvidenceItem, Any]] = []
        for item in items:
            match = matcher.match_financial_row(
                empresa_codigo=item.empresa_codigo or empresa,
                data=item.date,
                valor=item.amount,
                category=item.category,
                description=item.description,
            )
            first_pass.append((item, match))

        no_match_amounts = Counter(
            Decimal(str(item.amount)).quantize(Decimal("0.01"))
            for item, match in first_pass
            if match.status == MATCH_NO_MATCH
        )
        prestacao_matcher = PrestacaoNominalMatcher(
            prestacao_candidates,
            no_match_amount_counts=dict(no_match_amounts),
        )

        for item, caixa_match in first_pass:
            match = caixa_match
            prestacao_meta = None
            if match.status == MATCH_NO_MATCH and prestacao_candidates:
                prestacao_match = prestacao_matcher.match_financial_row(
                    empresa_codigo=item.empresa_codigo or empresa,
                    data=item.date,
                    valor=item.amount,
                    category=item.category,
                )
                if prestacao_match.status != MATCH_NO_MATCH:
                    match = prestacao_match
                    prestacao_meta = prestacao_locate
                    summary["prestacao_enriched"] = summary.get("prestacao_enriched", 0) + (
                        1 if prestacao_match.status == MATCH_PROBABLE else 0
                    )

            enriched_item = _apply_match_to_item(
                item,
                match,
                employee_index=employee_index,
                prestacao_meta=prestacao_meta,
            )
            enriched.append(enriched_item)

            summary[match.status] = summary.get(match.status, 0) + 1
            person = enriched_item.person_name
            if person:
                summary["with_funcionario"] += 1
                summary["total_with_funcionario_amount"] = round(
                    summary["total_with_funcionario_amount"] + item.amount,
                    2,
                )
            else:
                summary["total_without_funcionario_amount"] = round(
                    summary["total_without_funcionario_amount"] + item.amount,
                    2,
                )
            if enriched_item.cash_register:
                summary["with_caixa"] += 1
            if enriched_item.shift:
                summary["with_turno"] += 1

        total = len(items) or 1
        total_amount = round(sum(i.amount for i in items), 2) or 1.0
        metadata = {
            "nominal_sources_audited": [
                "CAIXA (/INTEGRACAO/CAIXA)",
                "CAIXA_REDE (/INTEGRACAO/CONSULTAR_CAIXA_REDE)",
                "CAIXA_APRESENTADO (/INTEGRACAO/CAIXA_APRESENTADO)",
                "CAIXA_APRESENTADO_REDE (/INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO_REDE)",
                "CONSULTAR_VALE_FUNCIONARIO_REDE (/INTEGRACAO/CONSULTAR_VALE_FUNCIONARIO_REDE)",
                "VALE_FUNCIONARIO_REDE (/INTEGRACAO/VALE_FUNCIONARIO_REDE)",
                "FUNCIONARIO (/INTEGRACAO/FUNCIONARIO)",
                PRESTACAO_PARSER,
                PRESTACAO_MARKDOWN_PARSER,
                "DESPESAS_FINANCEIRO_REDE (origem financeira — sem beneficiário)",
            ],
            "nominal_source_primary": "CAIXA+CAIXA_APRESENTADO.valeFunApurado",
            "prestacao_nominal_source": (
                prestacao_locate.get("source_file") if prestacao_locate.get("found") else None
            ),
            "prestacao_source_gap": bool(prestacao_locate.get("source_gap")),
            "prestacao_not_external_proof": True,
            "vale_endpoint_audit": vale_audit,
            "prestacao_audit": prestacao_audit,
            "nominal_candidates_loaded": len(candidates),
            "screen_rows_loaded": len(screen_rows),
            "fetch_error": fetch_error,
            "match_summary": summary,
            "coverage_pct_count": round(100 * summary["with_funcionario"] / total, 1),
            "coverage_pct_amount": round(
                100 * summary["total_with_funcionario_amount"] / total_amount,
                1,
            ),
            "match_status_ui_labels": {
                k: match_status_ui_label(k)
                for k in ("EXACT", "PROBABLE", "AMBIGUOUS", "NO_MATCH")
            },
            "beneficiary_vs_review": {
                "beneficiary_field": "person_name",
                "review_responsible_field": "review_responsible",
                "review_workflow_implemented": False,
                "per_item_field": "beneficiary_vs_review",
            },
            "prestacao_disclaimer": (
                "A Prestação de Contas foi usada apenas para identificar beneficiários. "
                "Ela não substitui conferência financeira externa."
            ),
            "complementary_sources_required": [
                "VALE_FUNCIONARIO_REDE — HTTP 401 (sem permissão no token Quality).",
                "CONSULTAR_VALE_FUNCIONARIO_REDE — HTTP 200, porém 0 registros no período 74014.",
                "Prestação PDF/markdown — seção Vale de Funcionários traz totais mensais por funcionário, "
                "não espelho linha a linha dos lançamentos financeiros consolidados.",
            ],
            "forced_match": False,
        }
        return enriched, metadata
