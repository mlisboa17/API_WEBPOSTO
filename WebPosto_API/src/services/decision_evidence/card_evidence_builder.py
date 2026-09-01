"""Constrói evidence_items (DIR-01) a partir de transações reais de cartão vindas de
/INTEGRACAO/CARTAO -- usado pelo sinal LEVEL 2 (CARD_SETTLEMENT_GAP_V2) do
CardReceivableDetector, para expor NSU/autorização/centro de custo por venda na tela de
evidência da decisão (GET /api/v1/decisions/{id}/evidence)."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from src.services.decision_evidence.expense_evidence_builder import evidence_items_summary
from src.services.decision_evidence.models import DecisionEvidenceItem

CARTAO_SOURCE = "/INTEGRACAO/CARTAO"

# Limite de itens materializados na evidência -- evita payload gigante quando o período tem
# milhares de transações; prioriza as de maior valor (ver build_card_evidence_items).
MAX_EVIDENCE_ITEMS = 100


def _stable_item_id(tenant_id: str, row: dict[str, Any]) -> str:
    key = "|".join(
        str(part)
        for part in (
            tenant_id,
            row.get("codigo"),
            row.get("vendaCodigo"),
            row.get("valor"),
            row.get("nsu"),
        )
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    return str(uuid.UUID(digest))


def _optional_str(value: Any) -> str | None:
    if value in (None, "", 0):
        return None
    return str(value)


def build_card_evidence_items(
    rows: list[dict[str, Any]],
    *,
    tenant_id: str,
    tenant_name: str | None,
    source: str = CARTAO_SOURCE,
    limit: int = MAX_EVIDENCE_ITEMS,
) -> list[DecisionEvidenceItem]:
    valid_rows = []
    for row in rows:
        try:
            amount = float(row.get("valor") or 0)
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        valid_rows.append((amount, row))

    valid_rows.sort(key=lambda pair: pair[0], reverse=True)

    items: list[DecisionEvidenceItem] = []
    for amount, row in valid_rows[:limit]:
        pendente = row.get("pendente")
        status = "pendente" if pendente in (True, "true", "True", 1, "1") else "liquidado"
        descricao_admin = row.get("adiministradoraDescricao") or row.get("administradoraDescricao")
        centro_custo = row.get("centroCustoDescricao")
        descricao = " / ".join(part for part in (descricao_admin, centro_custo) if part)

        items.append(
            DecisionEvidenceItem(
                id=_stable_item_id(tenant_id, row),
                tenant_id=tenant_id,
                empresa_codigo=_optional_str(row.get("empresaCodigo")),
                tenant_name=tenant_name,
                source=source,
                category="cartao",
                date=_optional_str(row.get("dataMovimento") or row.get("dataFiscal")),
                amount=round(amount, 2),
                description=_optional_str(descricao) or "Venda de cartão",
                origin=_optional_str(row.get("tipoInclusao")),
                document_reference=_optional_str(row.get("nsu") or row.get("autorizacao")),
                status=status,
                raw_reference={
                    "vendaCodigo": row.get("vendaCodigo"),
                    "nsu": row.get("nsu"),
                    "nsuTef": row.get("nsuTef"),
                    "autorizacao": row.get("autorizacao"),
                    "administradoraCodigo": row.get("administradoraCodigo"),
                    "codigoBandeira": row.get("codigoBandeira"),
                    "taxaPercentual": row.get("taxaPercentual"),
                    "centroCustoDescricao": centro_custo,
                    "parcela": row.get("parcela"),
                    "vencimento": row.get("vencimento"),
                    "dataPagamento": row.get("dataPagamento"),
                },
            )
        )
    return items


def attach_card_evidence_items(
    evidence: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    tenant_id: str,
    tenant_name: str | None,
) -> dict[str, Any]:
    """Mescla evidence_items de cartão (NSU/autorização/centro de custo por venda) no dict
    de evidência de uma DecisionCandidate, seguindo o mesmo formato de attach_expense_evidence_items."""
    items = build_card_evidence_items(rows, tenant_id=tenant_id, tenant_name=tenant_name)
    enriched = dict(evidence)
    enriched.update(evidence_items_summary(items))
    return enriched
