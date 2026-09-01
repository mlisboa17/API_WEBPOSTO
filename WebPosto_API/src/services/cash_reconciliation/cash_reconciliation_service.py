"""D02 — Conferência Financeira de Caixa (service layer)."""
from __future__ import annotations

import asyncio
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from src.domain.reconciliation.card_normalization import aggregate_card_breakdown, card_rows_from_vfp
from src.domain.reconciliation.models import (
    CaptureOrigin,
    NatureSummaryCard,
    PaymentNatureCode,
    PreCheckSummary,
    ReconciliationEvidence,
    ReconciliationItem,
    ReconciliationStatus,
    ReconciliationSummary,
)
from src.domain.reconciliation.nature_strategies import TOLERANCE
from src.domain.reconciliation.payment_normalization import (
    EXPECTED_DESTINATION,
    NATURE_FIELD_MAP,
    infer_capture_origin,
)
from src.gateway.webposto_client import WebPostoClient
from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.multiselect_utils import is_network_wide_empresa, parse_empresa_codigos
from src.services.cash_operations_service import CashOperationsService, _dec, _round2
from src.services.cash_reconciliation.audit_signal_engine import AuditSignalEngine
from src.services.cash_reconciliation.pre_reconciliation_engine import PreReconciliationEngine
from src.services.cash_reconciliation.reconciliation_state_store import ReconciliationStateStore
from src.services.network_financial_overview_service import FinancialOverviewFilters

SANGRIA_MARKERS = ("SANGRIA", "RETIRADA", "DEPOSITO CAIXA")
DEPOSIT_MARKERS = ("DEPOSITO", "DEPÓSITO", "DINHEIRO", "ESPECIE", "ESPÉCIE", "CAIXA", "COFRE")


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").upper().strip())


class CashReconciliationService:
    """Conferência financeira integrada à prestação de contas — fonte WebPosto."""

    def __init__(
        self,
        client: WebPostoClient | None = None,
        cash_ops: CashOperationsService | None = None,
        state_store: ReconciliationStateStore | None = None,
    ) -> None:
        self._client = client or WebPostoClient()
        self._cash = cash_ops or CashOperationsService(self._client)
        self._state = state_store or ReconciliationStateStore()
        self._pre = PreReconciliationEngine()
        self._audit = AuditSignalEngine()

    async def _resolve_cash_ops(self, empresa_codigo: str | int | None) -> CashOperationsService:
        """Isola credencial WebPosto por filial — evita merge multi-tenant no client padrão."""
        if empresa_codigo is None or is_network_wide_empresa(empresa_codigo):
            return self._cash
        codes = parse_empresa_codigos(empresa_codigo)
        if len(codes) != 1:
            return self._cash

        from src.core.webposto_credentials import list_webposto_credentials
        from src.services.tenant_discovery_service import TenantDiscoveryService

        discovery = TenantDiscoveryService()
        result = await discovery.discover_tenants(empresa_codigo_filter=codes[0])
        tenant = next((t for t in result.tenants_discovered if t.empresa_codigo == codes[0]), None)
        if not tenant:
            return self._cash

        api_key = None
        for cred in list_webposto_credentials():
            if cred.env_key == tenant.credential_alias:
                api_key = cred.api_key
                break
        if not api_key:
            return self._cash

        return CashOperationsService(WebPostoClient.for_api_key(api_key))

    @staticmethod
    def _rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [r for r in payload if isinstance(r, dict)]
        if isinstance(payload, dict):
            for key in ("resultados", "data", "items", "content"):
                chunk = payload.get(key)
                if isinstance(chunk, list):
                    return [r for r in chunk if isinstance(r, dict)]
        return []

    @staticmethod
    def _consolidation_status(row: dict[str, Any], ap_row: dict[str, Any]) -> tuple[str, str | None]:
        merged = {**row, **ap_row}
        explicit_fields = (
            "consolidado", "consolidada", "caixaConsolidado", "fechamentoConsolidado",
            "ap_consolidado", "ap_consolidada", "dataConsolidacao", "ap_dataConsolidacao",
        )
        for field in explicit_fields:
            value = merged.get(field)
            if value in (None, ""):
                continue
            if field.casefold().startswith("data") or "dataconsolidacao" in field.casefold():
                return "CONSOLIDATED", f"{field}={value}"
            if isinstance(value, bool):
                return ("CONSOLIDATED" if value else "NOT_CONSOLIDATED"), f"{field}={value}"
            normalized = _norm(value)
            if normalized in {"1", "S", "SIM", "TRUE", "CONSOLIDADO", "CONSOLIDADA"}:
                return "CONSOLIDATED", f"{field}={value}"
            if normalized in {"0", "N", "NAO", "NÃO", "FALSE", "NAO CONSOLIDADO", "NÃO CONSOLIDADO"}:
                return "NOT_CONSOLIDATED", f"{field}={value}"
        for field in ("situacao", "status", "ap_situacao", "ap_status"):
            value = merged.get(field)
            normalized = _norm(value)
            if "NAO CONSOLID" in normalized or "NÃO CONSOLID" in normalized:
                return "NOT_CONSOLIDATED", f"{field}={value}"
            if "CONSOLID" in normalized:
                return "CONSOLIDATED", f"{field}={value}"
        return "UNKNOWN", None

    async def _fetch_vfp(self, filters: FinancialOverviewFilters, cash: CashOperationsService) -> list[dict[str, Any]]:
        overview = cash._overview
        rows = await overview._fetch_paginated_endpoint("venda_forma_pagamento", filters)
        if not rows:
            rows = await overview._fetch_paginated_endpoint("venda_forma_pagamento_rede", filters)
        if filters.empresa_codigo is not None:
            code = int(filters.empresa_codigo)
            rows = [r for r in rows if int(r.get("empresaCodigo") or 0) == code]
        elif filters.empresa_codigos:
            rows = [r for r in rows if int(r.get("empresaCodigo") or 0) in filters.empresa_codigos]
        return rows

    async def _fetch_bank_credits(self, filters: FinancialOverviewFilters, cash: CashOperationsService) -> list[dict[str, Any]]:
        rows = await cash._overview._fetch_paginated_endpoint("movimento_conta", filters)
        output: list[dict[str, Any]] = []
        for row in rows:
            if not cash._matches_empresa(row, filters):
                continue
            movement_type = _norm(row.get("tipo"))
            if "CREDITO" not in movement_type and "CRÉDITO" not in movement_type:
                continue
            description = str(row.get("descricao") or row.get("historico") or "")
            origin = str(row.get("tipoDocumentoOrigem") or "")
            blob = _norm(f"{description} {origin}")
            markers = [marker for marker in DEPOSIT_MARKERS if _norm(marker) in blob]
            output.append({
                "codigo": row.get("movimentoContaCodigo") or row.get("codigo"),
                "dataMovimento": str(row.get("dataMovimento") or "")[:10],
                "valor": _round2(_dec(row.get("valor"))),
                "descricao": description,
                "tipoDocumentoOrigem": origin,
                "candidatoDepositoEspecie": bool(markers),
                "evidencias": markers,
            })
        return output

    async def _fetch_sangria_total(self, filters: FinancialOverviewFilters, cash: CashOperationsService) -> float:
        from src.services.expense_lineage_service import ExpenseLineageService
        from src.services.expense_semantic_service import ExpenseSemanticService
        from src.services.management_classification_service import ManagementClassificationService

        lineage = ExpenseLineageService()
        semantic = ExpenseSemanticService()
        mgmt = ManagementClassificationService()
        ctx = await lineage.build_context(cash._overview, filters)
        rows, err = await cash._overview._load_screen_expenses(filters)
        if err:
            return 0.0

        enriched = [
            mgmt.classify_row(semantic.classify_row(lineage.enrich_row(r, ctx)))
            for r in (rows or [])
        ]
        empresa = int(filters.empresa_codigo) if filters.empresa_codigo is not None else None
        total = 0.0

        for row in enriched:
            if empresa is not None and int(row.get("empresaCodigo") or 0) != empresa:
                continue
            blob = _norm(
                f"{row.get('descricao')} {row.get('planoConta')} {row.get('expenseManagementClass')}"
            )
            if any(m in blob for m in SANGRIA_MARKERS) or str(row.get("expenseManagementClass") or "") == "SANGRIA":
                total += _dec(row.get("valor"))

        for mov in ctx.movimentos:
            if empresa is not None and int(mov.get("empresaCodigo") or 0) != empresa:
                continue
            hist = _norm(mov.get("historico") or mov.get("descricao") or "")
            if any(m in hist for m in SANGRIA_MARKERS):
                total += _dec(mov.get("valor"))

        for row in ctx.closure_by_key.values():
            if empresa is not None and int(row.get("empresaCodigo") or row.get("ap_empresaCodigo") or 0) != empresa:
                continue
            total += _dec(row.get("ap_transfDebApurado") or row.get("transfDebApurado"))

        return _round2(total)

    async def _load_caixa_data(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
        cash: CashOperationsService,
    ) -> tuple[list[dict[str, Any]], float]:
        filters = build_finance_center_filters(data_inicial, data_final, empresa_codigo)
        overview = cash._overview
        t0 = time.perf_counter()

        caixa_rede, caixa, apresentado, apresentado_rede = await asyncio.gather(
            overview._fetch_paginated_endpoint("caixa_rede", filters),
            overview._fetch_paginated_endpoint("caixa", filters),
            overview._fetch_paginated_endpoint("caixa_apresentado", filters),
            overview._fetch_paginated_endpoint("caixa_apresentado_rede", filters),
        )

        caixa_rows = caixa_rede or caixa
        if caixa_rede and caixa:
            seen = {(r.get("empresaCodigo"), r.get("caixaCodigo")) for r in caixa_rede}
            caixa_rows = caixa_rede + [
                r for r in caixa if (r.get("empresaCodigo"), r.get("caixaCodigo")) not in seen
            ]

        ap_rows = apresentado + apresentado_rede
        caixa_rows = overview._dedupe_closure_source_rows(caixa_rows)
        caixa_rows = [r for r in caixa_rows if cash._matches_empresa(r, filters)]
        ap_rows = [r for r in ap_rows if cash._matches_empresa(r, filters)]

        ap_map = {(r.get("empresaCodigo"), r.get("caixaCodigo")): r for r in ap_rows}
        merged: list[dict[str, Any]] = []
        for row in caixa_rows:
            key = (row.get("empresaCodigo"), row.get("caixaCodigo"))
            ap = ap_map.get(key, {})
            merged.append({**row, **{f"ap_{k}": v for k, v in ap.items()}})

        merged = overview._dedupe_closure_source_rows(merged)

        ms = round((time.perf_counter() - t0) * 1000, 1)
        return merged, ms

    def _build_item_from_row(
        self,
        nature: PaymentNatureCode,
        row: dict[str, Any],
        ap_row: dict[str, Any],
        periodo_inicio: str,
        periodo_fim: str,
        sangria: float | None = None,
        card_breakdown: list | None = None,
    ) -> ReconciliationItem:
        fields = NATURE_FIELD_MAP[nature]
        apresentado = _dec(ap_row.get(fields["apresentado"]))
        apurado = _dec(ap_row.get(fields["apurado"]))
        diff_field = ap_row.get(fields["diferenca"])
        diferenca = _dec(diff_field) if diff_field not in (None, "") else _round2(apresentado - apurado)
        empresa = row.get("empresaCodigo") or ap_row.get("empresaCodigo")
        caixa = row.get("caixaCodigo") or ap_row.get("caixaCodigo")
        item_id = f"{empresa}:{caixa}:{nature.value}"
        consolidation_status, consolidation_evidence = self._consolidation_status(row, ap_row)

        return ReconciliationItem(
            id=item_id,
            filial=empresa,
            caixaCodigo=caixa,
            turno=str(row.get("turno") or row.get("turnoCodigo") or ""),
            consolidationStatus=consolidation_status,
            consolidationEvidence=consolidation_evidence,
            periodoInicio=periodo_inicio,
            periodoFim=periodo_fim,
            paymentNature=nature,
            captureOrigin=CaptureOrigin.CASH_REGISTER,
            valorApresentado=_round2(apresentado),
            valorApurado=_round2(apurado),
            valorEsperado=_round2(apurado),
            diferenca=_round2(diferenca),
            sangria=_round2(sangria) if nature == PaymentNatureCode.DINHEIRO and sangria else None,
            expectedDestination=EXPECTED_DESTINATION[nature],
            evidences=[
                ReconciliationEvidence(
                    source="CAIXA_APRESENTADO",
                    externalReference=str(ap_row.get("codigo") or caixa),
                    amount=_round2(apurado),
                    effectiveDate=str(row.get("dataMovimento") or row.get("fechamento") or "")[:10] or None,
                )
            ],
            cardBreakdown=card_breakdown or [],
        )

    async def build_items(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> tuple[list[ReconciliationItem], dict[str, Any]]:
        cash = await self._resolve_cash_ops(empresa_codigo)
        merged, ms = await self._load_caixa_data(data_inicial, data_final, empresa_codigo, cash)
        filters = build_finance_center_filters(data_inicial, data_final, empresa_codigo)
        vfp_rows, sangria_total, bank_credits = await asyncio.gather(
            self._fetch_vfp(filters, cash),
            self._fetch_sangria_total(filters, cash),
            self._fetch_bank_credits(filters, cash),
        )
        card_vfp = card_rows_from_vfp(vfp_rows)
        card_breakdown = aggregate_card_breakdown(card_vfp) if card_vfp else []

        ap_map = {}
        for row in merged:
            key = cash._overview._closure_key(row)
            ap_map[key] = row

        items: list[ReconciliationItem] = []
        nature_totals: dict[PaymentNatureCode, dict[str, float]] = defaultdict(lambda: {"ap": 0.0, "au": 0.0})

        for key, row in ap_map.items():
            for nature in PaymentNatureCode:
                fields = NATURE_FIELD_MAP[nature]
                ap_val = _dec(row.get(f"ap_{fields['apresentado']}") or row.get(fields["apresentado"]))
                au_val = _dec(row.get(f"ap_{fields['apurado']}") or row.get(fields["apurado"]))
                if ap_val == 0 and au_val == 0:
                    continue
                sangria = None
                cards = card_breakdown if nature == PaymentNatureCode.CARTAO else []
                ap_row = {k.replace("ap_", ""): v for k, v in row.items() if k.startswith("ap_")}
                ap_row.update({k: v for k, v in row.items() if not k.startswith("ap_")})
                item = self._build_item_from_row(
                    nature,
                    row,
                    ap_row,
                    data_inicial,
                    data_final,
                    sangria=sangria,
                    card_breakdown=cards,
                )
                if nature == PaymentNatureCode.CARTAO and card_vfp:
                    origins = {c.captureOrigin for c in cards}
                    item.captureOrigin = next(iter(origins)) if len(origins) == 1 else CaptureOrigin.UNKNOWN
                items.append(item)
                nature_totals[nature]["ap"] += ap_val
                nature_totals[nature]["au"] += au_val

        meta = {
            "performanceMs": ms,
            "caixaTurnos": len(ap_map),
            "vfpRows": len(vfp_rows),
            "cardVfpRows": len(card_vfp),
            "sangriaTotal": sangria_total,
            "bankCredits": bank_credits,
            "natureTotals": {k.value: v for k, v in nature_totals.items()},
        }
        return items, meta

    async def build_summary(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        try:
            items, meta = await self.build_items(data_inicial, data_final, empresa_codigo)
            state_key = self._state.state_key(empresa_codigo, data_inicial, data_final)
            persisted = self._state.load(state_key).get("items") or {}

            for item in items:
                justs = self._state.list_justifications(state_key, item.id)
                item.justifications = justs

            items, pre_check = self._pre.run(items, persisted)
            signals = self._audit.evaluate(items)

            cards: list[NatureSummaryCard] = []
            by_nature: dict[PaymentNatureCode, list[ReconciliationItem]] = defaultdict(list)
            for item in items:
                by_nature[item.paymentNature].append(item)

            for nature, group in by_nature.items():
                ap = _round2(sum(i.valorApresentado for i in group))
                au = _round2(sum(i.valorApurado for i in group))
                diff = _round2(ap - au)
                sangria = (
                    _round2(meta.get("sangriaTotal") or 0)
                    if nature == PaymentNatureCode.DINHEIRO
                    else None
                )
                reviewed = sum(
                    1
                    for i in group
                    if i.status
                    in {
                        ReconciliationStatus.CONFIRMED,
                        ReconciliationStatus.AUTO_MATCHED,
                        ReconciliationStatus.JUSTIFIED,
                    }
                )
                open_count = len(group) - reviewed
                auto_matched_count = sum(1 for i in group if i.status == ReconciliationStatus.AUTO_MATCHED)
                human_confirmed_count = sum(1 for i in group if i.status == ReconciliationStatus.CONFIRMED)
                worst = max(group, key=lambda i: abs(i.diferenca))
                cards.append(
                    NatureSummaryCard(
                        paymentNature=nature,
                        label=NATURE_FIELD_MAP[nature]["label"],
                        valorApurado=au,
                        valorApresentado=ap,
                        sangria=sangria,
                        diferenca=diff,
                        status=worst.status,
                        itemsCount=len(group),
                        reviewedCount=reviewed,
                        openCount=open_count,
                        autoMatchedCount=auto_matched_count,
                        humanConfirmedCount=human_confirmed_count,
                    )
                )
            cards.sort(key=lambda c: abs(c.diferenca), reverse=True)

            valor_apurado = _round2(sum(c.valorApurado for c in cards))
            valor_apresentado = _round2(sum(c.valorApresentado for c in cards))
            valor_divergente = _round2(sum(abs(c.diferenca) for c in cards if abs(c.diferenca) > TOLERANCE))
            valor_conferido = _round2(
                sum(i.valorApurado for i in items if i.status in {ReconciliationStatus.CONFIRMED, ReconciliationStatus.AUTO_MATCHED})
            )
            valor_pendente = _round2(valor_apurado - valor_conferido)
            naturezas_total = len(cards)
            naturezas_conferidas = sum(1 for c in cards if c.openCount == 0)

            summary = ReconciliationSummary(
                filial=empresa_codigo,
                periodoInicio=data_inicial,
                periodoFim=data_final,
                valorApurado=valor_apurado,
                valorApresentado=valor_apresentado,
                valorConferido=valor_conferido,
                valorDivergente=valor_divergente,
                valorPendente=valor_pendente,
                naturezasConferidas=naturezas_conferidas,
                naturezasTotal=naturezas_total,
                natureCards=cards,
                preCheck=pre_check,
                auditSignals=[s.model_dump() for s in signals],
            )

            return WebPostoResponse.ok(
                {
                    "summary": summary.model_dump(),
                    "items": [i.model_dump() for i in items],
                    "exceptions": [
                        i.model_dump()
                        for i in items
                        if i.status in {ReconciliationStatus.NEEDS_REVIEW, ReconciliationStatus.DIVERGENT}
                    ],
                    "meta": meta,
                    "stateKey": state_key,
                    "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
            )
        except Exception as exc:
            return WebPostoResponse.fail(WebPostoError(message=str(exc), type="RECONCILIATION_ERROR"))

    async def justify_item(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
        item_id: str,
        reason_category: str,
        description: str,
        responsible_user: str,
        expected_resolution_date: str | None = None,
    ) -> dict[str, Any]:
        from src.domain.reconciliation.models import JustificationCategory

        state_key = self._state.state_key(empresa_codigo, data_inicial, data_final)
        record = self._state.append_justification(
            state_key,
            item_id,
            JustificationCategory(reason_category),
            description,
            responsible_user,
            expected_resolution_date,
        )
        return {"success": True, "justification": record.model_dump()}

    async def confirm_item(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
        item_id: str,
        user: str | None = None,
    ) -> dict[str, Any]:
        state_key = self._state.state_key(empresa_codigo, data_inicial, data_final)
        from src.domain.reconciliation.models import ReconciliationStatus

        self._state.set_item_status(state_key, item_id, ReconciliationStatus.CONFIRMED, user)
        return {"success": True, "itemId": item_id, "status": ReconciliationStatus.CONFIRMED.value}

    async def parity_report(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int,
        reference: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Caso POSTO VIP — compara API vs referência PDF (não hardcoded na UI)."""
        resp = await self.build_summary(data_inicial, data_final, str(empresa_codigo))
        if not resp.success:
            return {"success": False, "error": resp.error}
        data = resp.data or {}
        summary = data.get("summary") or {}
        cards = {c["paymentNature"]: c for c in summary.get("natureCards") or []}

        ref = reference or {}
        lines = []
        matched_amount = 0.0
        total_ref = sum(abs(v) for v in ref.values()) or 1.0
        for nature_key, ref_diff in ref.items():
            card = cards.get(nature_key) or cards.get(nature_key.replace(" ", "_").upper())
            api_diff = card.get("diferenca") if card else None
            delta = None if api_diff is None else _round2(float(api_diff) - float(ref_diff))
            if delta is not None and abs(delta) <= 0.05:
                matched_amount += abs(ref_diff)
            lines.append(
                {
                    "nature": nature_key,
                    "referenceDiff": ref_diff,
                    "apiDiff": api_diff,
                    "delta": delta,
                    "status": "MATCH" if delta is not None and abs(delta) <= 0.05 else "GAP",
                }
            )

        pct_reconstructed = _round2(100 * matched_amount / total_ref) if ref else 0.0
        pre = summary.get("preCheck") or {}
        auto_pct = _round2(100 * (pre.get("autoMatched") or 0) / max(pre.get("totalAnalyzed") or 1, 1))

        return {
            "success": True,
            "empresaCodigo": empresa_codigo,
            "periodo": {"inicio": data_inicial, "fim": data_final},
            "lines": lines,
            "summaryTotals": {
                "valorApurado": summary.get("valorApurado"),
                "valorApresentado": summary.get("valorApresentado"),
                "valorDivergente": summary.get("valorDivergente"),
            },
            "parityPct": pct_reconstructed,
            "autoMatchedPct": auto_pct,
            "humanIntervention": (pre.get("needsReview") or 0) + (pre.get("divergent") or 0),
            "source": "CAIXA_APRESENTADO+DESPESAS+VFP",
        }
