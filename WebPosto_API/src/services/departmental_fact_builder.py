"""Constrói fatos departamentais sem inferência silenciosa."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable

from src.core.management_scope import (
    department_for_group,
    is_licensed_company,
    quarantine_reason_for_group,
)
from src.domain.departmental_facts import (
    DepartmentalFact,
    DepartmentalFactBatch,
    DepartmentalFactKind,
    DepartmentalFactStatus,
    FactLineage,
)


class DepartmentalFactBuilder:
    VALUE_FIELDS = {
        DepartmentalFactKind.SALE: ("totalVenda", "valorTotal", "valor"),
        DepartmentalFactKind.COST: ("totalCusto", "custoTotal", "precoCusto"),
        DepartmentalFactKind.EXPENSE: ("valor",),
        DepartmentalFactKind.STOCK: ("saldoEstoque", "saldo", "quantidade"),
        DepartmentalFactKind.CASH: ("apurado", "fechamento", "valor"),
    }
    ID_FIELDS = (
        "vendaItemCodigo",
        "vendaCodigo",
        "despesaCodigo",
        "estoqueCodigo",
        "caixaCodigo",
        "movimentoCodigo",
        "codigo",
    )

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except Exception:
            return Decimal("0")

    @classmethod
    def _first(cls, row: dict[str, Any], fields: Iterable[str]) -> Any:
        for field in fields:
            if row.get(field) is not None:
                return row[field]
        return None

    @classmethod
    def _source_id(cls, kind: DepartmentalFactKind, row: dict[str, Any]) -> str:
        if kind == DepartmentalFactKind.STOCK:
            stock = row.get("estoqueCodigo")
            product = row.get("produtoCodigo") or row.get("codigoProduto")
            if stock not in (None, "") and product not in (None, ""):
                return f"{stock}:{product}"
        if kind in {DepartmentalFactKind.SALE, DepartmentalFactKind.COST}:
            sale = row.get("vendaCodigo")
            item = row.get("vendaItemCodigo")
            if sale not in (None, "") and item not in (None, ""):
                return f"{sale}:{item}"
        value = cls._first(row, cls.ID_FIELDS)
        if value not in (None, ""):
            return str(value)
        canonical = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None

    @classmethod
    def build(
        cls,
        kind: DepartmentalFactKind,
        rows: list[dict[str, Any]],
        *,
        endpoint: str,
        logical_token: str,
        product_groups: dict[int, int] | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
        collected_at: datetime | None = None,
    ) -> DepartmentalFactBatch:
        product_groups = product_groups or {}
        lineage = FactLineage(
            logical_token=logical_token,
            endpoint=endpoint,
            period_start=period_start,
            period_end=period_end,
            collected_at=collected_at or datetime.now(timezone.utc),
        )
        facts: list[DepartmentalFact] = []
        quarantine: list[DepartmentalFact] = []
        seen: dict[tuple[str, str, int], str] = {}
        duplicates = 0
        identity_conflicts = 0
        rejected = 0
        source_total = Decimal("0")

        for row in rows:
            company_raw = row.get("empresaCodigo")
            if not is_licensed_company(company_raw):
                rejected += 1
                continue
            company = int(company_raw)
            source_id = cls._source_id(kind, row)
            marker = (kind.value, source_id, company)
            canonical = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
            if marker in seen:
                if seen[marker] == canonical:
                    duplicates += 1
                else:
                    identity_conflicts += 1
                continue
            seen[marker] = canonical

            value = cls._decimal(cls._first(row, cls.VALUE_FIELDS[kind]))
            source_total += value
            product_raw = row.get("produtoCodigo") or row.get("codigoProduto")
            product = int(product_raw) if str(product_raw or "").isdigit() else None
            group_raw = row.get("grupoCodigo")
            if group_raw is None and product is not None:
                group_raw = product_groups.get(product)
            group = int(group_raw) if str(group_raw or "").isdigit() else None
            department = department_for_group(group)
            reason = quarantine_reason_for_group(group)
            if department is None and reason is None:
                reason = "SEM_GRUPO" if group is None else "GRUPO_NAO_CLASSIFICADO"
            status = (
                DepartmentalFactStatus.CLASSIFIED
                if department is not None
                else DepartmentalFactStatus.QUARANTINED
            )
            fact = DepartmentalFact(
                fact_id=f"{kind.value}:{company}:{source_id}",
                kind=kind,
                empresa_codigo=company,
                departamento=department,
                status=status,
                quarantine_reason=reason,
                source_record_id=source_id,
                produto_codigo=product,
                grupo_codigo=group,
                data_movimento=cls._parse_datetime(
                    row.get("dataMovimento") or row.get("dataHora") or row.get("data")
                ),
                turno_codigo=row.get("turnoCodigo"),
                quantidade=cls._decimal(row.get("quantidade")),
                valor=value,
                lineage=lineage,
            )
            (facts if department is not None else quarantine).append(fact)

        reconciled = sum((fact.valor for fact in facts + quarantine), Decimal("0"))
        return DepartmentalFactBatch(
            facts=facts,
            quarantine=quarantine,
            rejected_unlicensed=rejected,
            duplicates_removed=duplicates,
            identity_conflicts=identity_conflicts,
            source_total=source_total,
            reconciled_total=reconciled,
            reconciliation_difference=source_total - reconciled,
        )
