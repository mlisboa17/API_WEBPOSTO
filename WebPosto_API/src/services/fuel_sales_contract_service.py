"""Normalização e quarentena de VENDA_ITEM para o departamento Combustíveis."""

from __future__ import annotations

from typing import Any, Iterable

from pydantic import ValidationError

from src.domain.fuel.models import FuelSaleItemFact


class FuelSalesContractService:
    @staticmethod
    def _integer(row: dict[str, Any], *keys: str) -> int | None:
        for key in keys:
            value = row.get(key)
            if value in (None, ""):
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return None

    @classmethod
    def normalize_item(
        cls,
        row: dict[str, Any],
        *,
        group_by_product: dict[int, int] | None = None,
    ) -> FuelSaleItemFact:
        product_code = cls._integer(row, "produtoCodigo", "codigoProduto")
        group_code = cls._integer(row, "grupoCodigo", "codigoGrupo", "grupoProdutoCodigo")
        if group_code is None and product_code is not None:
            group_code = (group_by_product or {}).get(product_code)

        return FuelSaleItemFact(
            empresa_codigo=cls._integer(row, "empresaCodigo") or 0,
            venda_codigo=cls._integer(row, "vendaCodigo") or 0,
            venda_item_codigo=cls._integer(row, "vendaItemCodigo", "codigo") or 0,
            produto_codigo=product_code or 0,
            grupo_codigo=group_code,
            produto_lmc_codigo=cls._integer(row, "produtoLmcCodigo"),
            bico_codigo=cls._integer(row, "bicoCodigo"),
            tanque_codigo=cls._integer(row, "tanqueCodigo"),
            data_movimento=str(row.get("dataMovimento") or row.get("data") or ""),
            litros=row.get("quantidade") or row.get("litros") or 0,
            preco_venda=row.get("precoVenda") or 0,
            preco_custo=row.get("precoCusto") or 0,
            faturamento=row.get("totalVenda") or 0,
            custo_total=row.get("totalCusto") or 0,
            desconto_total=row.get("totalDesconto") or 0,
            acrescimo_total=row.get("totalAcrescimo") or 0,
        )

    @classmethod
    def normalize_batch(
        cls,
        rows: Iterable[dict[str, Any]],
        *,
        group_by_product: dict[int, int] | None = None,
    ) -> dict[str, Any]:
        accepted: list[FuelSaleItemFact] = []
        quarantine: list[dict[str, Any]] = []
        seen: set[tuple[int, int, int]] = set()
        duplicate_count = 0

        for row in rows:
            key = (
                cls._integer(row, "empresaCodigo") or 0,
                cls._integer(row, "vendaCodigo") or 0,
                cls._integer(row, "vendaItemCodigo", "codigo") or 0,
            )
            if key in seen:
                duplicate_count += 1
                continue
            seen.add(key)
            try:
                accepted.append(cls.normalize_item(row, group_by_product=group_by_product))
            except ValidationError as exc:
                quarantine.append({"key": key, "reason": exc.errors()[0]["msg"]})

        return {
            "accepted": accepted,
            "quarantine": quarantine,
            "duplicates": duplicate_count,
            "total": len(seen),
        }
