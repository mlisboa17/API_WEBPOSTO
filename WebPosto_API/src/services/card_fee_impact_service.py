"""Serviço de Impacto de Taxas de Cartão — Sprint 48."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CardBrandFee(BaseModel):
    """Taxa por bandeira/método de cartão."""

    model_config = ConfigDict(frozen=True)

    brand: str
    method: str
    taxa_percentual: float
    volume_vendas: float = 0.0
    valor_taxa_rs: float = 0.0
    transacoes: int = 0


class CardFeeImpactSummary(BaseModel):
    """Resumo do impacto das taxas de cartão na margem."""

    model_config = ConfigDict(frozen=True)

    period_start: str
    period_end: str
    empresa_codigo: int | None = None

    receita_bruta_cartoes: float
    total_taxas_cartao_rs: float
    taxa_media_ponderada_pct: float
    receita_liquida_cartoes: float

    receita_total: float = 0.0
    cmv_total: float = 0.0
    margem_bruta: float = 0.0
    margem_bruta_pct: float = 0.0
    margem_liquida_pos_cartoes: float = 0.0
    margem_liquida_pct: float = 0.0

    impacto_taxas_na_margem_pct: float = 0.0

    by_brand: list[CardBrandFee] = Field(default_factory=list)
    by_method: dict[str, float] = Field(default_factory=dict)

    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


DEFAULT_CARD_FEES: dict[str, dict[str, float]] = {
    "VISA": {"CREDITO": 2.49, "DEBITO": 1.49},
    "MASTERCARD": {"CREDITO": 2.49, "DEBITO": 1.49},
    "ELO": {"CREDITO": 2.69, "DEBITO": 1.59},
    "AMEX": {"CREDITO": 3.19, "DEBITO": 2.19},
    "HIPERCARD": {"CREDITO": 2.89, "DEBITO": 1.69},
    "DEFAULT": {"CREDITO": 2.50, "DEBITO": 1.50},
}


class CardFeeImpactService:
    """Calcula impacto das taxas de cartão na margem líquida."""

    def __init__(
        self,
        custom_fees: dict[str, dict[str, float]] | None = None,
    ) -> None:
        self._fees = custom_fees or DEFAULT_CARD_FEES

    def _get_fee_rate(self, brand: str, method: str) -> float:
        brand_upper = brand.upper().strip()
        method_upper = method.upper().strip()
        if method_upper in {"CREDIT", "CREDITO", "CARTAO_CREDITO"}:
            method_key = "CREDITO"
        elif method_upper in {"DEBIT", "DEBITO", "CARTAO_DEBITO"}:
            method_key = "DEBITO"
        else:
            method_key = method_upper

        brand_fees = self._fees.get(brand_upper, self._fees.get("DEFAULT", {}))
        return brand_fees.get(method_key, 2.0)

    def calculate_fee(
        self,
        valor: float,
        brand: str,
        method: str,
        taxa_percentual: float | None = None,
    ) -> dict[str, float]:
        if taxa_percentual is not None and taxa_percentual > 0:
            taxa = taxa_percentual
        else:
            taxa = self._get_fee_rate(brand, method)

        valor_taxa = valor * (taxa / 100)
        valor_liquido = valor - valor_taxa

        return {
            "valor_bruto": round(valor, 2),
            "taxa_percentual": round(taxa, 4),
            "valor_taxa": round(valor_taxa, 2),
            "valor_liquido": round(valor_liquido, 2),
        }

    def analyze_card_sales(
        self,
        card_transactions: list[dict[str, Any]],
        period_start: str,
        period_end: str,
        empresa_codigo: int | None = None,
        receita_total: float | None = None,
        cmv_total: float | None = None,
    ) -> CardFeeImpactSummary:
        by_brand_method: dict[tuple[str, str], dict[str, Any]] = {}
        total_vendas = 0.0
        total_taxas = 0.0

        for tx in card_transactions:
            brand = str(tx.get("bandeira") or tx.get("brand") or "DEFAULT").upper()
            method = str(tx.get("metodo") or tx.get("method") or tx.get("tipoPagamento") or "CREDITO").upper()
            valor = float(tx.get("valor") or tx.get("amount") or 0)
            taxa_webposto = tx.get("taxaPercentual")

            if valor <= 0:
                continue

            fee_info = self.calculate_fee(valor, brand, method, taxa_webposto)
            key = (brand, method)

            if key not in by_brand_method:
                by_brand_method[key] = {
                    "brand": brand,
                    "method": method,
                    "taxa_percentual": fee_info["taxa_percentual"],
                    "volume_vendas": 0.0,
                    "valor_taxa_rs": 0.0,
                    "transacoes": 0,
                }

            by_brand_method[key]["volume_vendas"] += valor
            by_brand_method[key]["valor_taxa_rs"] += fee_info["valor_taxa"]
            by_brand_method[key]["transacoes"] += 1
            total_vendas += valor
            total_taxas += fee_info["valor_taxa"]

        taxa_media = (total_taxas / total_vendas * 100) if total_vendas > 0 else 0
        receita_liquida = total_vendas - total_taxas

        brand_fees = [
            CardBrandFee(
                brand=data["brand"],
                method=data["method"],
                taxa_percentual=data["taxa_percentual"],
                volume_vendas=round(data["volume_vendas"], 2),
                valor_taxa_rs=round(data["valor_taxa_rs"], 2),
                transacoes=data["transacoes"],
            )
            for data in sorted(by_brand_method.values(), key=lambda x: -x["volume_vendas"])
        ]

        by_method: dict[str, float] = {}
        for bf in brand_fees:
            method = "CREDITO" if "CRED" in bf.method else "DEBITO" if "DEB" in bf.method else bf.method
            by_method[method] = by_method.get(method, 0) + bf.volume_vendas

        margem_bruta = 0.0
        margem_bruta_pct = 0.0
        margem_liquida = 0.0
        margem_liquida_pct = 0.0
        impacto_na_margem = 0.0

        if receita_total and receita_total > 0:
            if cmv_total is not None:
                margem_bruta = receita_total - cmv_total
                margem_bruta_pct = (margem_bruta / receita_total) * 100
                margem_liquida = margem_bruta - total_taxas
                margem_liquida_pct = (margem_liquida / receita_total) * 100
                impacto_na_margem = (total_taxas / margem_bruta * 100) if margem_bruta > 0 else 0

        return CardFeeImpactSummary(
            period_start=period_start,
            period_end=period_end,
            empresa_codigo=empresa_codigo,
            receita_bruta_cartoes=round(total_vendas, 2),
            total_taxas_cartao_rs=round(total_taxas, 2),
            taxa_media_ponderada_pct=round(taxa_media, 4),
            receita_liquida_cartoes=round(receita_liquida, 2),
            receita_total=round(receita_total or total_vendas, 2),
            cmv_total=round(cmv_total or 0, 2),
            margem_bruta=round(margem_bruta, 2),
            margem_bruta_pct=round(margem_bruta_pct, 4),
            margem_liquida_pos_cartoes=round(margem_liquida, 2),
            margem_liquida_pct=round(margem_liquida_pct, 4),
            impacto_taxas_na_margem_pct=round(impacto_na_margem, 4),
            by_brand=brand_fees,
            by_method=by_method,
        )

    def calculate_margin_after_fees(
        self,
        receita: float,
        cmv: float,
        total_taxas_cartao: float,
    ) -> dict[str, float]:
        margem_bruta = receita - cmv
        margem_liquida = margem_bruta - total_taxas_cartao

        return {
            "receita": round(receita, 2),
            "cmv": round(cmv, 2),
            "margem_bruta": round(margem_bruta, 2),
            "margem_bruta_pct": round((margem_bruta / receita * 100) if receita > 0 else 0, 4),
            "taxas_cartao": round(total_taxas_cartao, 2),
            "margem_liquida": round(margem_liquida, 2),
            "margem_liquida_pct": round((margem_liquida / receita * 100) if receita > 0 else 0, 4),
        }
