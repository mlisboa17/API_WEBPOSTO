"""FR-01 — FuelingSettlementTrace: reconstrução factual Abastecimento→Baixa→Venda→Pagamentos→TEF.

FATOS PRIMEIRO → SCORE DEPOIS.
Não decide fraude. Não colapsa N pagamentos/cartões em 1.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal

from pydantic import BaseModel, Field

LOGGER = logging.getLogger(__name__)

MONEY_TOLERANCE = Decimal("0.02")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

TraceStatus = Literal[
    "UNSETTLED",
    "SETTLED",
    "PARTIALLY_EXPLAINED",
    "EXPLAINED",
    "MISMATCH",
    "UNKNOWN",
]
ReconcileStatus = Literal["EXACT", "MISMATCH", "UNKNOWN"]
PaymentMode = Literal[
    "NONE",
    "SINGLE_CASH",
    "SINGLE_ELECTRONIC",
    "MULTI_ELECTRONIC",
    "MIXED",
    "UNKNOWN",
]
NsuKind = Literal["TEF_CLASSIC", "RAW_UUID_OR_TOKEN", "EMPTY", "UNKNOWN"]


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value is not None else 0))
    except Exception:
        return Decimal("0")


def _money(value: Any) -> float:
    return float(_dec(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _money_eq(a: Any, b: Any, tol: Decimal = MONEY_TOLERANCE) -> bool:
    return abs(_dec(a) - _dec(b)) <= tol


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        if "T" not in text and " " in text:
            text = text.replace(" ", "T", 1)
        # dataFiscal+horaFiscal sem offset (ex.: 2026-08-10T18:16:11)
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _retention_minutes(start: str | None, end: str | None) -> int | None:
    a = _parse_dt(start)
    b = _parse_dt(end)
    if not a or not b or b < a:
        return None
    # naive vs aware: strip tz for delta if mixed
    if a.tzinfo is not None and b.tzinfo is None:
        a = a.replace(tzinfo=None)
    elif b.tzinfo is not None and a.tzinfo is None:
        b = b.replace(tzinfo=None)
    return int((b - a).total_seconds() / 60)


def _classify_nsu(raw_nsu: str | None, nsu_tef: str | None) -> NsuKind:
    tef = (nsu_tef or "").strip()
    raw = (raw_nsu or "").strip()
    if tef:
        return "TEF_CLASSIC"
    if not raw:
        return "EMPTY"
    if _UUID_RE.match(raw) or any(c.isalpha() for c in raw):
        return "RAW_UUID_OR_TOKEN"
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) >= 4:
        return "TEF_CLASSIC"
    return "UNKNOWN"


def _is_cash_payment(nome: str | None, tipo: str | None = None) -> bool:
    blob = f"{nome or ''} {tipo or ''}".upper()
    return any(k in blob for k in ("DINHEIRO", "ESPECIE", "ESPÉCIE", "SPECIE")) or (
        (tipo or "").upper() == "D"
    )


class SaleFact(BaseModel):
    sale_id: int
    cupom: str | None = None
    timestamp: str | None = None
    employee_id: int | None = None
    employee_name: str | None = None
    total: float = 0.0
    empresa_codigo: int = 0
    cancelada: bool = False


class FuelingFact(BaseModel):
    fueling_id: int
    venda_item_id: int | None = None
    sale_id: int | None = None
    timestamp: str | None = None
    settlement_timestamp: str | None = None
    nozzle: int | None = None
    bomba: int | None = None
    product: str | None = None
    product_codigo: int | str | None = None
    volume: float = 0.0
    unit_price: float = 0.0
    amount: float = 0.0
    employee_id: int | None = None
    employee_name: str | None = None
    retention_minutes: int | None = None
    status: str = "UNKNOWN"


class PaymentComponentFact(BaseModel):
    payment_id: str | None = None
    type: str = ""
    amount: float = 0.0
    financeiro_codigo: int | None = None
    forma_pagamento_codigo: int | None = None
    administrator_codigo: int | None = None
    tipo_forma_pagamento: str | None = None
    is_cash: bool = False
    card_id: int | None = None


class CardComponentFact(BaseModel):
    card_id: int
    financeiro_codigo: int | None = None
    amount: float = 0.0
    administrator: str | None = None
    administrator_codigo: int | None = None
    raw_nsu: str | None = None
    raw_authorization: str | None = None
    nsu_tef: str | None = None
    nsu_kind: NsuKind = "UNKNOWN"
    inclusion_type: str | None = None
    sale_id: int | None = None


class ReconciliationFact(BaseModel):
    fueling_total: float = 0.0
    sale_total: float = 0.0
    payment_total: float = 0.0
    fueling_to_sale_status: ReconcileStatus = "UNKNOWN"
    sale_to_payment_status: ReconcileStatus = "UNKNOWN"
    money_tolerance: float = float(MONEY_TOLERANCE)


class RetentionSummary(BaseModel):
    max_retention_minutes: int | None = None
    min_retention_minutes: int | None = None
    per_fueling: list[int] = Field(default_factory=list)


class LegacyProjectionNote(BaseModel):
    """Campos legados N→1 ainda expostos em OcorrenciaFraudeDTO — NÃO usar como verdade FR-01."""

    formaPagamento: str = "DEPRECATED_PROJECTION"
    cartaoBandeira: str = "DEPRECATED_PROJECTION"
    cartaoNsu: str = "DEPRECATED_PROJECTION"
    cartaoAutorizacao: str = "DEPRECATED_PROJECTION"
    valorTotalCartao: str = "DEPRECATED_PROJECTION"
    note: str = (
        "Projeção legada N→1 do pipeline pista/antifraude. "
        "Source of truth FR-01 = payments[] + cards[]."
    )


class FuelingSettlementTrace(BaseModel):
    """Cadeia factual por venda (ou UNSETTLED por abastecimento sem baixa)."""

    sale: SaleFact | None = None
    fuelings: list[FuelingFact] = Field(default_factory=list)
    payments: list[PaymentComponentFact] = Field(default_factory=list)
    cards: list[CardComponentFact] = Field(default_factory=list)
    reconciliation: ReconciliationFact = Field(default_factory=ReconciliationFact)
    retention: RetentionSummary = Field(default_factory=RetentionSummary)
    trace_status: TraceStatus = "UNKNOWN"
    payment_mode: PaymentMode = "UNKNOWN"
    legacy_projection: LegacyProjectionNote = Field(default_factory=LegacyProjectionNote)
    source: str = "FR01_FuelingSettlementTrace"
    # EXPLAINED ≠ NO_FRAUD
    explained_means: str = (
        "Cadeia financeira/fiscal reconstruída; não implica ausência de fraude."
    )


def _payment_mode(payments: list[PaymentComponentFact]) -> PaymentMode:
    if not payments:
        return "NONE"
    cash = [p for p in payments if p.is_cash]
    elec = [p for p in payments if not p.is_cash]
    if cash and elec:
        return "MIXED"
    if cash and not elec:
        return "SINGLE_CASH" if len(cash) == 1 else "MIXED"
    if len(elec) == 1:
        return "SINGLE_ELECTRONIC"
    if len(elec) > 1:
        return "MULTI_ELECTRONIC"
    return "UNKNOWN"


def _card_from_row(row: dict[str, Any], sale_id: int | None) -> CardComponentFact:
    card_id = int(row.get("cartaoCodigo") or row.get("codigo") or 0)
    raw_nsu = str(row.get("nsu") or "").strip() or None
    nsu_tef = str(row.get("nsuTef") or "").strip() or None
    raw_auth = str(row.get("autorizacao") or "").strip() or None
    admin = str(
        row.get("adiministradoraDescricao")
        or row.get("administradoraDescricao")
        or ""
    ).strip() or None
    return CardComponentFact(
        card_id=card_id,
        financeiro_codigo=card_id or None,
        amount=_money(row.get("valor")),
        administrator=admin,
        administrator_codigo=int(row["administradoraCodigo"])
        if row.get("administradoraCodigo") not in (None, "")
        else None,
        raw_nsu=raw_nsu,
        raw_authorization=raw_auth,
        nsu_tef=nsu_tef,
        nsu_kind=_classify_nsu(raw_nsu, nsu_tef),
        inclusion_type=str(row.get("tipoInclusao") or "").strip() or None,
        sale_id=sale_id,
    )


def _payment_from_row(
    row: dict[str, Any],
    cards_by_financeiro: dict[int, CardComponentFact],
) -> PaymentComponentFact:
    fin = row.get("financeiroCodigo")
    financeiro = int(fin) if fin not in (None, "") else None
    nome = str(row.get("nomeFormaPagamento") or row.get("formaPagamento") or "").strip()
    tipo = str(row.get("tipoFormaPagamento") or "").strip() or None
    is_cash = _is_cash_payment(nome, tipo)
    card = cards_by_financeiro.get(financeiro) if financeiro else None
    # Dinheiro nunca herda NSU
    card_id = None if is_cash else (card.card_id if card else None)
    pid = None
    if financeiro is not None:
        pid = str(financeiro)
    elif row.get("codigo") not in (None, ""):
        pid = f"{row.get('codigo')}:{_money(row.get('valorPagamento') or row.get('valor'))}"
    return PaymentComponentFact(
        payment_id=pid,
        type=nome or "N/I",
        amount=_money(row.get("valorPagamento") or row.get("valor")),
        financeiro_codigo=financeiro,
        forma_pagamento_codigo=int(row["formaPagamentoCodigo"])
        if row.get("formaPagamentoCodigo") not in (None, "")
        else None,
        administrator_codigo=int(row["administradoraCodigo"])
        if row.get("administradoraCodigo") not in (None, "")
        else None,
        tipo_forma_pagamento=tipo,
        is_cash=is_cash,
        card_id=card_id,
    )


def build_fueling_settlement_trace(
    *,
    sale: SaleFact | None,
    fuelings: list[FuelingFact],
    payment_rows: list[dict[str, Any]] | None = None,
    card_rows: list[dict[str, Any]] | None = None,
) -> FuelingSettlementTrace:
    """Constrói trace factual. Não faz matching fueling↔payment por valor."""
    sale_id = sale.sale_id if sale else None

    cards = [_card_from_row(r, sale_id) for r in (card_rows or []) if r]
    cards = [c for c in cards if c.card_id]
    cards_by_fin = {int(c.financeiro_codigo or c.card_id): c for c in cards}

    payments = [_payment_from_row(r, cards_by_fin) for r in (payment_rows or []) if r]

    # Retenção individual (já pode vir preenchida)
    enriched_fuelings: list[FuelingFact] = []
    for f in fuelings:
        ret = f.retention_minutes
        if ret is None:
            ret = _retention_minutes(f.timestamp, f.settlement_timestamp)
        enriched_fuelings.append(f.model_copy(update={"retention_minutes": ret}))

    rets = [int(f.retention_minutes) for f in enriched_fuelings if f.retention_minutes is not None]
    retention = RetentionSummary(
        max_retention_minutes=max(rets) if rets else None,
        min_retention_minutes=min(rets) if rets else None,
        per_fueling=rets,
    )

    fueling_total = _money(sum((_dec(f.amount) for f in enriched_fuelings), Decimal("0")))
    sale_total = _money(sale.total) if sale else 0.0
    payment_total = _money(sum((_dec(p.amount) for p in payments), Decimal("0")))

    if sale is None and not any(f.sale_id for f in enriched_fuelings):
        f2s: ReconcileStatus = "UNKNOWN"
    elif sale is None:
        f2s = "UNKNOWN"
    elif not enriched_fuelings:
        f2s = "UNKNOWN"
    else:
        f2s = "EXACT" if _money_eq(fueling_total, sale_total) else "MISMATCH"

    if sale is None:
        s2p: ReconcileStatus = "UNKNOWN"
    elif not payments:
        s2p = "UNKNOWN"
    else:
        s2p = "EXACT" if _money_eq(sale_total, payment_total) else "MISMATCH"

    recon = ReconciliationFact(
        fueling_total=fueling_total,
        sale_total=sale_total,
        payment_total=payment_total,
        fueling_to_sale_status=f2s,
        sale_to_payment_status=s2p,
    )

    mode = _payment_mode(payments)
    status = _resolve_trace_status(
        sale=sale,
        fuelings=enriched_fuelings,
        payments=payments,
        recon=recon,
    )

    return FuelingSettlementTrace(
        sale=sale,
        fuelings=enriched_fuelings,
        payments=payments,
        cards=cards,
        reconciliation=recon,
        retention=retention,
        trace_status=status,
        payment_mode=mode,
    )


def _resolve_trace_status(
    *,
    sale: SaleFact | None,
    fuelings: list[FuelingFact],
    payments: list[PaymentComponentFact],
    recon: ReconciliationFact,
) -> TraceStatus:
    if not fuelings:
        return "UNKNOWN"
    settled = [f for f in fuelings if f.sale_id or f.venda_item_id]
    if not sale and not settled:
        return "UNSETTLED"
    if sale and not settled:
        return "PARTIALLY_EXPLAINED"
    if (
        sale
        and settled
        and recon.fueling_to_sale_status == "EXACT"
        and recon.sale_to_payment_status == "EXACT"
        and payments
    ):
        return "EXPLAINED"
    if recon.fueling_to_sale_status == "MISMATCH" or recon.sale_to_payment_status == "MISMATCH":
        return "MISMATCH"
    if sale and settled and payments:
        return "PARTIALLY_EXPLAINED"
    if sale and settled:
        return "SETTLED"
    return "UNKNOWN"


def fueling_fact_from_abastecimento(item: Any) -> FuelingFact:
    """Mapeia AbastecimentoRestV1 (ou duck-type) → FuelingFact."""
    bico = int(getattr(item, "bico", 0) or 0)
    bomba = getattr(item, "bomba", None)
    if bomba is None and bico:
        bomba = ((max(1, bico) - 1) // 2) + 1
    sale_id = getattr(item, "idVenda", None)
    vic = getattr(item, "vendaItemCodigo", None)
    try:
        vic_i = int(vic) if vic not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        vic_i = None
    return FuelingFact(
        fueling_id=int(getattr(item, "idAbastecimento", 0) or 0),
        venda_item_id=vic_i,
        sale_id=int(sale_id) if sale_id not in (None, 0, "0") else None,
        timestamp=getattr(item, "dataHora", None),
        settlement_timestamp=getattr(item, "dataHoraBaixa", None),
        nozzle=bico or None,
        bomba=int(bomba) if bomba not in (None, "") else None,
        product=getattr(item, "descricaoProduto", None) or getattr(item, "tipoCombustivel", None),
        product_codigo=getattr(item, "idProduto", None),
        volume=round(float(getattr(item, "litros", 0) or 0), 3),
        unit_price=float(getattr(item, "precoUnitario", 0) or 0),
        amount=_money(getattr(item, "valorTotal", 0)),
        employee_id=getattr(item, "idFrentista", None),
        employee_name=getattr(item, "nomeFrentista", None),
        status=str(getattr(item, "status", "UNKNOWN") or "UNKNOWN"),
    )


def index_cartoes_by_venda(
    rows: list[dict[str, Any]],
) -> dict[tuple[int, int], list[dict[str, Any]]]:
    """vendaCodigo → lista completa de CARTAO (preserva N)."""
    out: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for r in rows:
        try:
            vc = int(r.get("vendaCodigo") or 0)
            emp = int(r.get("empresaCodigo") or 0)
        except (TypeError, ValueError):
            continue
        if not vc:
            continue
        out.setdefault((emp, vc), []).append(r)
    return out


def index_cartoes_by_financeiro(
    rows: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """financeiro/cartaoCodigo → CARTAO (chave estruturada VFP↔TEF)."""
    out: dict[int, dict[str, Any]] = {}
    for r in rows:
        try:
            code = int(r.get("cartaoCodigo") or r.get("codigo") or 0)
        except (TypeError, ValueError):
            continue
        if code:
            out[code] = r
    return out


def build_traces_for_baixados(
    *,
    baixados: list[Any],
    vendas: dict[tuple[int, int], dict[str, Any]],
    pagamentos: dict[tuple[int, int], list[dict[str, Any]]],
    cartoes_por_venda: dict[tuple[int, int], list[dict[str, Any]]],
    employee_names: dict[int, str] | None = None,
) -> dict[tuple[int, int], FuelingSettlementTrace]:
    """Agrupa baixados por venda e monta um trace por (empresa, venda)."""
    names = employee_names or {}
    by_sale: dict[tuple[int, int], list[Any]] = {}
    for item in baixados:
        emp = int(getattr(item, "idEmpresa", 0) or 0)
        vc = int(getattr(item, "idVenda", 0) or 0)
        if not vc:
            continue
        by_sale.setdefault((emp, vc), []).append(item)

    traces: dict[tuple[int, int], FuelingSettlementTrace] = {}
    for key, items in by_sale.items():
        emp, vc = key
        vrow = vendas.get(key) or vendas.get((0, vc)) or {}
        sale_emp = vrow.get("funcionarioCodigo")
        try:
            sale_emp_i = int(sale_emp) if sale_emp not in (None, "") else None
        except (TypeError, ValueError):
            sale_emp_i = None
        sale = SaleFact(
            sale_id=vc,
            cupom=str(vrow.get("notaNumero") or vrow.get("numeroNota") or "").strip() or None,
            timestamp=str(vrow.get("dataHora") or "").strip() or None,
            employee_id=sale_emp_i,
            employee_name=names.get(sale_emp_i) if sale_emp_i else None,
            total=_money(vrow.get("totalVenda") or vrow.get("valorTotal") or 0),
            empresa_codigo=emp,
            cancelada=str(vrow.get("cancelada") or "N").upper() in {"S", "Y", "1", "TRUE"},
        )
        # fallback total from fuelings if venda row thin
        fuelings = [fueling_fact_from_abastecimento(i) for i in items]
        if sale.total == 0 and fuelings:
            sale.total = _money(sum((_dec(f.amount) for f in fuelings), Decimal("0")))
        if not sale.timestamp and fuelings:
            # settlement time from fuelings
            stamps = [f.settlement_timestamp for f in fuelings if f.settlement_timestamp]
            sale.timestamp = max(stamps) if stamps else None

        pags = pagamentos.get(key) or pagamentos.get((0, vc)) or []
        cards = cartoes_por_venda.get(key) or cartoes_por_venda.get((0, vc)) or []
        traces[key] = build_fueling_settlement_trace(
            sale=sale,
            fuelings=fuelings,
            payment_rows=pags,
            card_rows=cards,
        )
    return traces
