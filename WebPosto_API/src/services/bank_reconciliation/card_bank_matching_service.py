"""D02+ — Motor de cruzamento cartão (WebPosto/VFP) x extrato bancário (OFX).

Não existe identificador comum (NSU/FITID) entre a venda registrada no WebPosto e o crédito
recebido do adquirente/banco, então o casamento é heurístico. Dois modelos de extrato foram
observados na prática, cada um com sua estratégia de comparação:

1. PagBank/PagSeguro (Posto Doze, Casa Caiada): cada venda de cartão gera um lançamento
   individual no extrato -> ``match_card_settlements`` casa transação a transação (bandeira +
   método + janela de data + valor mais próximo dentro de tolerância). Granularidade escolhida
   pelo negócio, aceitando ruído de taxa entre o bruto da venda e o líquido ("Disponível")
   depositado.
2. Itaú + adquirente (Rede/Cielo, ex.: Posto Vip): a liquidação é agregada por dia + bandeira +
   método (um único crédito por lote diário) -> ``compare_daily_card_settlements`` soma as
   vendas do WebPosto no mesmo balde e reporta o delta contra o único lançamento bancário
   correspondente (sem tentar casar transação a transação, pois essa granularidade não existe
   nesse extrato).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from src.domain.reconciliation.bank_statement import BankTransaction, BankTransactionCategory

DEFAULT_AMOUNT_TOLERANCE = 0.05  # tolerância absoluta em R$ por lançamento
DEFAULT_DATE_WINDOW_DAYS = 1  # liquidação pode cair em D ou D+1 na conta

# OFX usa convenções distintas por banco: PagBank usa IN/OUT, Itaú usa CREDIT/DEBIT.
_CREDIT_TRN_TYPES = {"IN", "CREDIT"}


@dataclass
class CardSaleEvent:
    """Uma venda de cartão individual (WebPosto/VFP), normalizada para casamento com o banco."""

    reference: str  # identificador de origem (ex.: vendaCodigo) apenas para rastreabilidade
    occurredAt: datetime
    amount: float
    brand: str  # normalizedBrand (ex.: MASTERCARD, VISA, ELO, AMEX)
    method: str  # normalizedMethod (ex.: CREDITO, DEBITO)
    costCenter: str | None = None  # "PISTA"/"LOJA" (centroCustoDescricao real de /INTEGRACAO/CARTAO), None quando não disponível


@dataclass
class CardBankMatch:
    sale: CardSaleEvent
    bankTransaction: BankTransaction
    delta: float  # bankTransaction.amount - sale.amount (negativo = taxa/desconto no banco)


@dataclass
class CardBankMatchResult:
    matched: list[CardBankMatch] = field(default_factory=list)
    unmatchedSales: list[CardSaleEvent] = field(default_factory=list)  # venda sem evidência bancária
    unmatchedBankTransactions: list[BankTransaction] = field(default_factory=list)  # crédito sem venda correspondente

    @property
    def matchedSalesTotal(self) -> float:
        return round(sum(m.sale.amount for m in self.matched), 2)

    @property
    def matchedBankTotal(self) -> float:
        return round(sum(m.bankTransaction.amount for m in self.matched), 2)

    @property
    def unmatchedSalesTotal(self) -> float:
        return round(sum(s.amount for s in self.unmatchedSales), 2)

    @property
    def unmatchedBankTotal(self) -> float:
        return round(sum(t.amount for t in self.unmatchedBankTransactions), 2)


def match_card_settlements(
    sales: list[CardSaleEvent],
    bank_transactions: list[BankTransaction],
    *,
    amount_tolerance: float = DEFAULT_AMOUNT_TOLERANCE,
    date_window_days: int = DEFAULT_DATE_WINDOW_DAYS,
) -> CardBankMatchResult:
    """Casa cada venda de cartão com um lançamento de crédito no extrato bancário (guloso,
    ordenado do maior para o menor valor de venda para reduzir colisões em lotes com valores
    repetidos)."""
    available = [
        t
        for t in bank_transactions
        if t.category == BankTransactionCategory.CARD_SETTLEMENT and t.trnType.upper() in _CREDIT_TRN_TYPES
    ]
    matched: list[CardBankMatch] = []
    unmatched_sales: list[CardSaleEvent] = []

    for sale in sorted(sales, key=lambda s: s.amount, reverse=True):
        candidates = [
            t
            for t in available
            if t.cardBrand == sale.brand.upper()
            and t.cardMethod == sale.method.upper()
            and abs((t.postedAt.date() - sale.occurredAt.date()).days) <= date_window_days
        ]
        if not candidates:
            unmatched_sales.append(sale)
            continue

        best = min(candidates, key=lambda t: abs(t.amount - sale.amount))
        if abs(best.amount - sale.amount) > amount_tolerance:
            unmatched_sales.append(sale)
            continue

        matched.append(CardBankMatch(sale=sale, bankTransaction=best, delta=round(best.amount - sale.amount, 2)))
        available.remove(best)

    return CardBankMatchResult(matched=matched, unmatchedSales=unmatched_sales, unmatchedBankTransactions=available)


def extract_premmia_settlements(bank_transactions: list[BankTransaction]) -> list[BankTransaction]:
    """Retorna os PIX recebidos identificados como liquidação Premmia (cartão da Vibra que entra
    como 'Pix recebido - Vibra Energia S.a', não como MEMO de cartão)."""
    return [
        t
        for t in bank_transactions
        if t.category == BankTransactionCategory.PIX_RECEIVED and t.likelyPremmia and t.trnType.upper() in _CREDIT_TRN_TYPES
    ]


@dataclass
class DailyCardSettlementComparison:
    """Comparação agregada (dia + bandeira + método) entre vendas WebPosto e crédito bancário.

    Usado para extratos que liquidam por lote diário (ex.: Itaú + Rede/Cielo), onde não existe
    um lançamento bancário por venda individual para casar transação a transação.
    """

    settlementDate: date
    brand: str
    method: str
    salesTotal: float
    bankTotal: float | None  # None se não há lançamento bancário nesse balde (dia/bandeira/método)
    bankTransactions: list[BankTransaction] = field(default_factory=list)

    @property
    def delta(self) -> float | None:
        if self.bankTotal is None:
            return None
        return round(self.bankTotal - self.salesTotal, 2)


def compare_daily_card_settlements(
    sales: list[CardSaleEvent],
    bank_transactions: list[BankTransaction],
) -> list[DailyCardSettlementComparison]:
    """Agrupa vendas e créditos bancários por (dia, bandeira, método) e retorna a comparação de
    cada balde, incluindo baldes só do lado do WebPosto (sem crédito bancário ainda) e só do lado
    do banco (crédito sem venda WebPosto correspondente nesse dia/bandeira/método)."""
    sales_totals: dict[tuple[date, str, str], float] = {}
    for sale in sales:
        key = (sale.occurredAt.date(), sale.brand.upper(), sale.method.upper())
        sales_totals[key] = round(sales_totals.get(key, 0.0) + sale.amount, 2)

    bank_buckets: dict[tuple[date, str, str], list[BankTransaction]] = {}
    for txn in bank_transactions:
        if txn.category != BankTransactionCategory.CARD_SETTLEMENT or txn.trnType.upper() not in _CREDIT_TRN_TYPES:
            continue
        if not txn.cardBrand or not txn.cardMethod:
            continue
        key = (txn.postedAt.date(), txn.cardBrand, txn.cardMethod)
        bank_buckets.setdefault(key, []).append(txn)

    all_keys = set(sales_totals) | set(bank_buckets)
    comparisons: list[DailyCardSettlementComparison] = []
    for key in sorted(all_keys):
        settlement_date, brand, method = key
        bank_txns = bank_buckets.get(key, [])
        bank_total = round(sum(t.amount for t in bank_txns), 2) if bank_txns else None
        comparisons.append(
            DailyCardSettlementComparison(
                settlementDate=settlement_date,
                brand=brand,
                method=method,
                salesTotal=sales_totals.get(key, 0.0),
                bankTotal=bank_total,
                bankTransactions=bank_txns,
            )
        )
    return comparisons


def _previous_business_day(reference: date, business_days: int) -> date:
    """Retrocede `business_days` dias ÚTEIS a partir de `reference` (pula sábado/domingo; não
    considera feriados, pois o calendário de feriados não está disponível nesta integração)."""
    current = reference
    remaining = business_days
    while remaining > 0:
        current -= timedelta(days=1)
        if current.weekday() < 5:  # 0=segunda .. 4=sexta
            remaining -= 1
    return current


def _weekend_bundled_sale_date(sale_date: date) -> date:
    """Sábado/domingo retrocedem pra sexta-feira anterior (o adquirente não liquida no fim de
    semana; a venda de sábado/domingo cai no mesmo lote de sexta que é creditado junto em D+1
    útil na segunda). Dias úteis retornam inalterados."""
    weekday = sale_date.weekday()
    if weekday >= 5:  # 5=sábado, 6=domingo
        return sale_date - timedelta(days=weekday - 4)
    return sale_date


def compare_daily_card_settlements_with_lag(
    sales: list[CardSaleEvent],
    bank_transactions: list[BankTransaction],
    *,
    acquirer_lag_business_days: dict[str, int] | None = None,
    default_lag_business_days: int = 0,
) -> list[DailyCardSettlementComparison]:
    """Igual a ``compare_daily_card_settlements``, mas desloca o balde do lançamento bancário para
    trás em dias ÚTEIS antes de comparar, conforme o prazo de liquidação do adquirente
    (``txn.acquirer``, ex.: REDE deposita em D+1 útil). Assim o crédito bancário de terça-feira
    (D+1 útil da venda de segunda) é comparado contra as vendas de segunda-feira, não contra
    vendas de terça. Adquirentes sem lag configurado usam ``default_lag_business_days`` (0 =
    mesmo dia, comportamento de ``compare_daily_card_settlements``).

    FIM DE SEMANA: quando há QUALQUER adquirente com lag > 0 configurado, vendas de sábado/domingo
    são "empurradas" pro balde de sexta-feira anterior (``_weekend_bundled_sale_date``), pois o
    adquirente não liquida no fim de semana e bate tudo junto no crédito de segunda (D+1 útil de
    sexta). Aplicado de forma UNIFORME a todas as vendas da bandeira/método (não há, hoje, um jeito
    confiável de saber por venda qual adquirente processou -- ver nota em
    ``card_sale_event_builder`` sobre a heurística de sufixo " ITAU" ter se mostrado inconsistente
    entre bandeiras). Não há risco de contagem duplicada: cada venda cai em EXATAMENTE um balde,
    nunca numa janela sobreposta."""
    lags = acquirer_lag_business_days or {}
    bundle_weekends = default_lag_business_days > 0 or any(lag > 0 for lag in lags.values())

    sales_totals: dict[tuple[date, str, str], float] = {}
    for sale in sales:
        sale_date = sale.occurredAt.date()
        bucket_date = _weekend_bundled_sale_date(sale_date) if bundle_weekends else sale_date
        key = (bucket_date, sale.brand.upper(), sale.method.upper())
        sales_totals[key] = round(sales_totals.get(key, 0.0) + sale.amount, 2)

    bank_buckets: dict[tuple[date, str, str], list[BankTransaction]] = {}
    for txn in bank_transactions:
        if txn.category != BankTransactionCategory.CARD_SETTLEMENT or txn.trnType.upper() not in _CREDIT_TRN_TYPES:
            continue
        if not txn.cardBrand or not txn.cardMethod:
            continue
        lag = lags.get((txn.acquirer or "").upper(), default_lag_business_days)
        sale_equivalent_date = _previous_business_day(txn.postedAt.date(), lag) if lag > 0 else txn.postedAt.date()
        key = (sale_equivalent_date, txn.cardBrand, txn.cardMethod)
        bank_buckets.setdefault(key, []).append(txn)

    all_keys = set(sales_totals) | set(bank_buckets)
    comparisons: list[DailyCardSettlementComparison] = []
    for key in sorted(all_keys):
        settlement_date, brand, method = key
        bank_txns = bank_buckets.get(key, [])
        bank_total = round(sum(t.amount for t in bank_txns), 2) if bank_txns else None
        comparisons.append(
            DailyCardSettlementComparison(
                settlementDate=settlement_date,
                brand=brand,
                method=method,
                salesTotal=sales_totals.get(key, 0.0),
                bankTotal=bank_total,
                bankTransactions=bank_txns,
            )
        )
    return comparisons
