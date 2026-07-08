"""Constrói evidence_items a partir de lançamentos reais de despesa."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from src.services.decision_evidence.models import DecisionEvidenceItem

EXPENSE_SOURCE = "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE"


def _stable_item_id(tenant_id: str, row: dict[str, Any]) -> str:
    raw = row.get("raw") or {}
    key = "|".join(
        str(part)
        for part in (
            tenant_id,
            row.get("empresaCodigo"),
            row.get("data"),
            row.get("planoContaCodigo"),
            row.get("valor"),
            row.get("origem"),
            raw.get("descricaoDocumento"),
        )
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    return str(uuid.UUID(digest))


def _person_name(row: dict[str, Any]) -> str | None:
    raw = row.get("raw") or {}
    for key in ("funcionarioNome", "nomeFuncionario", "employeeName", "beneficiario"):
        val = row.get(key) or raw.get(key)
        if val not in (None, "", 0):
            return str(val)
    code = row.get("funcionarioCodigo") or raw.get("funcionarioCodigo")
    if code not in (None, "", 0):
        return f"Funcionário {code}"
    return None


def _optional_str(value: Any) -> str | None:
    if value in (None, "", 0, "desconhecido"):
        return None
    return str(value)


def build_expense_evidence_items(
    rows: list[dict[str, Any]],
    *,
    category: str,
    tenant_id: str,
    tenant_name: str | None,
    source: str = EXPENSE_SOURCE,
) -> list[DecisionEvidenceItem]:
    filtered = [
        row
        for row in rows
        if str(row.get("planoConta") or "SEM_CATEGORIA") == category
    ]
    filtered.sort(
        key=lambda row: float(row.get("valor") or 0),
        reverse=True,
    )

    items: list[DecisionEvidenceItem] = []
    for row in filtered:
        raw = row.get("raw") or {}
        try:
            amount = float(row.get("valor") or 0)
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue

        desc = (
            raw.get("descricaoDocumento")
            or row.get("planoConta")
            or row.get("centroCusto")
        )
        items.append(
            DecisionEvidenceItem(
                id=_stable_item_id(tenant_id, row),
                tenant_id=tenant_id,
                empresa_codigo=_optional_str(row.get("empresaCodigo")),
                tenant_name=tenant_name,
                source=source,
                category=category,
                person_name=_person_name(row),
                date=_optional_str(row.get("data")),
                amount=round(amount, 2),
                description=_optional_str(desc),
                origin=_optional_str(row.get("origem")),
                cash_register=_optional_str(row.get("caixaCodigo") or raw.get("caixaCodigo")),
                shift=_optional_str(row.get("turnoCodigo") or raw.get("turnoCodigo")),
                document_reference=_optional_str(
                    raw.get("numeroDocumento")
                    or raw.get("documento")
                    or raw.get("descricaoDocumento")
                ),
                status=_optional_str(row.get("status")),
                raw_reference={
                    "planoContaCodigo": row.get("planoContaCodigo"),
                    "funcionarioCodigo": row.get("funcionarioCodigo") or raw.get("funcionarioCodigo"),
                    "origem": row.get("origem"),
                },
            )
        )
    return items


def evidence_items_summary(items: list[DecisionEvidenceItem]) -> dict[str, Any]:
    total = round(sum(item.amount for item in items), 2)
    return {
        "evidence_items": [item.model_dump() for item in items],
        "evidence_items_count": len(items),
        "evidence_items_total": total,
    }


def attach_expense_evidence_items(
    evidence: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    category: str,
    tenant_id: str,
    tenant_name: str | None,
) -> dict[str, Any]:
    items = build_expense_evidence_items(
        rows,
        category=category,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
    )
    enriched = dict(evidence)
    enriched.update(evidence_items_summary(items))
    return enriched
