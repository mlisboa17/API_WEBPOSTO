"""
Adelaide Tax Engine — margem líquida com PIS/COFINS monofásico e taxas de cartão.
Precisão via Decimal em todo o fluxo.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.domain.reconciliation.acquirer_fee_model import PAGBANK_TAXAS_OFICIAIS

TWOPLACES = Decimal("0.01")
MONOFASICO_PIS_COFINS_RATE = Decimal("0.0137")  # ~1,37% combustíveis monofásico


def _default_card_fee_rate() -> Decimal:
    """Estimativa de taxa média de cartão para simulação de margem (Adelaide), calculada a
    partir das taxas REAIS validadas em ``acquirer_fee_model.PAGBANK_TAXAS_OFICIAIS`` (não é
    mais um percentual fixo escrito no código). Só serve de fallback quando o chamador não sabe
    a bandeira/adquirente real da venda -- sempre que possível, resolva a taxa exata via
    ``resolver_taxa()`` (empresa + adquirente + bandeira + modalidade) e passe ``card_fee_rate``
    explicitamente ao construir o perfil.
    """
    taxas = [t.percentual for t in PAGBANK_TAXAS_OFICIAIS]
    return (sum(taxas, Decimal("0")) / Decimal(len(taxas)) / Decimal("100")).quantize(
        Decimal("0.0001")
    )


class AdelaideTaxProfile(BaseModel):
    """Perfil fiscal Adelaide para um produto/período."""

    model_config = ConfigDict(frozen=True)

    codigo_produto: str
    nome_produto: str
    litros: Decimal = Field(default=Decimal("0"))
    faturamento_bruto: Decimal = Field(default=Decimal("0"))
    custo_aquisicao_litro: Decimal = Field(default=Decimal("0"))
    pis_cofins_rate: Decimal = Field(default=MONOFASICO_PIS_COFINS_RATE)
    card_fee_rate: Decimal = Field(default_factory=_default_card_fee_rate)

    @property
    def custo_total(self) -> Decimal:
        return (self.litros * self.custo_aquisicao_litro).quantize(
            TWOPLACES, rounding=ROUND_HALF_UP
        )

    @property
    def pis_cofins(self) -> Decimal:
        return (self.faturamento_bruto * self.pis_cofins_rate).quantize(
            TWOPLACES, rounding=ROUND_HALF_UP
        )

    @property
    def taxa_cartao(self) -> Decimal:
        return (self.faturamento_bruto * self.card_fee_rate).quantize(
            TWOPLACES, rounding=ROUND_HALF_UP
        )

    @property
    def margem_liquida(self) -> Decimal:
        return (
            self.faturamento_bruto
            - self.custo_total
            - self.pis_cofins
            - self.taxa_cartao
        ).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    @property
    def margem_pct(self) -> Decimal:
        if self.faturamento_bruto <= 0:
            return Decimal("0")
        return (
            (self.margem_liquida / self.faturamento_bruto) * Decimal("100")
        ).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


class ExecutiveKpiSummary(BaseModel):
    """KPIs executivos agregados por período."""

    model_config = ConfigDict(frozen=True)

    periodo: str
    faturamento_total: Decimal = Decimal("0")
    custo_total: Decimal = Decimal("0")
    pis_cofins_total: Decimal = Decimal("0")
    taxas_cartao_total: Decimal = Decimal("0")
    margem_liquida_total: Decimal = Decimal("0")
    litros_total: Decimal = Decimal("0")
    despesas_caixa: Decimal = Decimal("0")
    faturamento_nao_combustivel: Decimal = Decimal("0")
    produtos: list[AdelaideTaxProfile] = Field(default_factory=list)
    masked: bool = False
    fallback: bool = False
    mensagem: Optional[str] = None


def _d(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def agregar_abastecimentos(
    registros: list[dict[str, Any]],
    custo_por_codigo: Optional[dict[str, Decimal]] = None,
) -> ExecutiveKpiSummary:
    """Agrega abastecimentos em perfis Adelaide."""
    from src.domain.adelaide.fuel_catalog import (
        custo_aquisicao_litro,
        rotulo_combustivel,
    )

    buckets: dict[str, AdelaideTaxProfile] = {}
    for row in registros:
        codigo = str(row.get("codigoProduto") or "").strip()
        if not codigo:
            continue
        nome = rotulo_combustivel(codigo)
        for campo in (
            "descricaoProduto",
            "nomeProduto",
            "produtoNome",
        ):
            if row.get(campo):
                nome = rotulo_combustivel(codigo, str(row[campo]))
                break
        litros = _d(row.get("quantidade") or row.get("litros") or 0)
        valor = _d(row.get("valorTotal") or row.get("valor") or 0)
        custo_litro = (
            custo_por_codigo.get(codigo)
            if custo_por_codigo and codigo in custo_por_codigo
            else custo_aquisicao_litro(codigo)
        )
        from src.domain.adelaide.fuel_catalog import eh_combustivel_codigo

        pis_rate = (
            MONOFASICO_PIS_COFINS_RATE
            if eh_combustivel_codigo(codigo)
            else Decimal("0")
        )
        if codigo not in buckets:
            buckets[codigo] = AdelaideTaxProfile(
                codigo_produto=codigo,
                nome_produto=nome,
                custo_aquisicao_litro=custo_litro,
                pis_cofins_rate=pis_rate,
            )
        p = buckets[codigo]
        buckets[codigo] = p.model_copy(
            update={
                "litros": p.litros + litros,
                "faturamento_bruto": p.faturamento_bruto + valor,
            }
        )

    produtos = list(buckets.values())
    return ExecutiveKpiSummary(
        periodo="custom",
        faturamento_total=sum((p.faturamento_bruto for p in produtos), Decimal("0")),
        custo_total=sum((p.custo_total for p in produtos), Decimal("0")),
        pis_cofins_total=sum((p.pis_cofins for p in produtos), Decimal("0")),
        taxas_cartao_total=sum((p.taxa_cartao for p in produtos), Decimal("0")),
        margem_liquida_total=sum((p.margem_liquida for p in produtos), Decimal("0")),
        litros_total=sum((p.litros for p in produtos), Decimal("0")),
        produtos=produtos,
    )
