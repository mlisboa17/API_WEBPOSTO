"""D02+ — Parser de extrato bancário OFX sem dependências externas.

Suporta dois formatos observados na prática:

1. PagBank/PagSeguro (Posto Doze, Casa Caiada): tags de folha devidamente fechadas, cada venda de
   cartão gera um lançamento individual (MEMO ``'Vendas - Disponivel {DEBITO|CREDITO} {BANDEIRA}'``).
2. Itaú + adquirentes Rede/Cielo (Posto Vip): tags de folha SEM fechamento (SGML puro), e a
   liquidação de cartão é agregada por dia + bandeira + método (MEMO
   ``'RECEBIMENTO {REDE|CIELO} {BANDEIRA} {AT|DB|CD}{codigo} {razao social do adquirente}'``).

Em ambos os casos o corpo não é XML estrito (conteúdo pode ter caracteres como ``&``), então o
parsing é feito via regex por tag em vez de um parser XML/SGML formal.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from src.domain.reconciliation.bank_statement import (
    BankStatement,
    BankTransaction,
    BankTransactionCategory,
)

_STMTTRN_BLOCK_RE = re.compile(r"<STMTTRN>(.*?)</STMTTRN>", re.DOTALL | re.IGNORECASE)
_DTPOSTED_RE = re.compile(r"^(\d{14})")

# --- PagBank/PagSeguro ---
_CARD_SETTLEMENT_RE = re.compile(r"^Vendas\s*-\s*Dispon[ií]vel\s+(CREDITO|DEBITO)\s+(.+)$", re.IGNORECASE)
_PIX_SETTLEMENT_RE = re.compile(r"^Vendas\s*-\s*Dispon[ií]vel\s+PIX\s*$", re.IGNORECASE)
_PIX_RECEIVED_RE = re.compile(r"^Pix\s+recebido\s*-\s*(.+)$", re.IGNORECASE)
_PIX_SENT_RE = re.compile(r"^(?:QR\s+Code\s+)?Pix\s+enviado\s*-\s*(.+)$", re.IGNORECASE)
_BILL_PAYMENT_RE = re.compile(r"^Pagamento\s+de\s+conta\s*-\s*(.+)$", re.IGNORECASE)
_ACCOUNT_FEE_RE = re.compile(r"^Cobran[çc]a\s+(.+)$", re.IGNORECASE)
_ACCOUNT_YIELD_RE = re.compile(r"^Rendimento\s+da\s+conta\s*-\s*(.+)$", re.IGNORECASE)

# --- Itaú + adquirente (Rede/Cielo) ---
_ACQUIRER_SETTLEMENT_RE = re.compile(
    r"^RECEBIMENTO\s+(REDE|CIELO|GETNET|STONE)\s+(VISA|MAST(?:ERCARD)?|ELO|AMEX|HIPER\w*)\s+"
    r"(AT|DB|CD|PARC)\d+\s+(.+)$",
    re.IGNORECASE,
)
_AUTOMATIC_TRANSFER_RE = re.compile(r"^Transfer[êe]ncia\s+Autom\.?\s+Enviada\s*(.*)$", re.IGNORECASE)
_BALANCE_INFO_RE = re.compile(r"^Saldo\s+(Total\s+Dispon[íi]vel\s+Dia|Anterior)\s*$", re.IGNORECASE)

# Códigos de liquidação da Rede: DB=débito, CD=crédito, AT=crédito (à vista ou antecipação de
# recebíveis — significado exato ainda não confirmado pelo negócio, ver bank_statement.py).
_ACQUIRER_METHOD_MAP = {"DB": "DEBITO", "CD": "CREDITO", "AT": "CREDITO", "PARC": "CREDITO"}
_ACQUIRER_BRAND_MAP = {"MAST": "MASTERCARD", "MASTERCARD": "MASTERCARD", "VISA": "VISA", "ELO": "ELO", "AMEX": "AMEX"}

# Premmia é um cartão de fidelidade da Vibra que liquida como PIX (não como MEMO de cartão),
# confirmado pelo negócio. Sinalizamos heuristicamente pela contraparte do PIX.
_PREMMIA_COUNTERPARTY_HINTS = ("VIBRA",)


@dataclass
class _Classification:
    category: BankTransactionCategory
    cardMethod: str | None = None
    cardBrand: str | None = None
    acquirer: str | None = None
    settlementCode: str | None = None
    counterparty: str | None = None
    likelyPremmia: bool = False


def _tag(block: str, tag: str) -> str | None:
    match = re.search(rf"<{tag}>([^<\r\n]*)", block, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _parse_ofx_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    match = _DTPOSTED_RE.match(raw)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y%m%d%H%M%S")


def _classify(memo: str) -> _Classification:
    memo = memo.strip()

    card_match = _CARD_SETTLEMENT_RE.match(memo)
    if card_match:
        method = card_match.group(1).upper()
        brand = card_match.group(2).strip().upper()
        return _Classification(BankTransactionCategory.CARD_SETTLEMENT, cardMethod=method, cardBrand=brand)

    if _PIX_SETTLEMENT_RE.match(memo):
        # Pix capturado na maquininha, liquidado igual a cartão (sem bandeira).
        return _Classification(BankTransactionCategory.CARD_SETTLEMENT, cardMethod="PIX", cardBrand="PIX")

    acquirer_match = _ACQUIRER_SETTLEMENT_RE.match(memo)
    if acquirer_match:
        acquirer = acquirer_match.group(1).upper()
        raw_brand = acquirer_match.group(2).upper()
        settlement_code = acquirer_match.group(3).upper()
        brand = _ACQUIRER_BRAND_MAP.get(raw_brand, raw_brand)
        method = _ACQUIRER_METHOD_MAP.get(settlement_code, "UNKNOWN")
        return _Classification(
            BankTransactionCategory.CARD_SETTLEMENT,
            cardMethod=method,
            cardBrand=brand,
            acquirer=acquirer,
            settlementCode=settlement_code,
            counterparty=acquirer_match.group(4).strip(),
        )

    pix_match = _PIX_RECEIVED_RE.match(memo)
    if pix_match:
        counterparty = pix_match.group(1).strip()
        likely_premmia = any(hint in counterparty.upper() for hint in _PREMMIA_COUNTERPARTY_HINTS)
        return _Classification(BankTransactionCategory.PIX_RECEIVED, counterparty=counterparty, likelyPremmia=likely_premmia)

    pix_sent_match = _PIX_SENT_RE.match(memo)
    if pix_sent_match:
        return _Classification(BankTransactionCategory.PIX_SENT, counterparty=pix_sent_match.group(1).strip())

    bill_match = _BILL_PAYMENT_RE.match(memo)
    if bill_match:
        return _Classification(BankTransactionCategory.BILL_PAYMENT, counterparty=bill_match.group(1).strip())

    if _ACCOUNT_YIELD_RE.match(memo):
        return _Classification(BankTransactionCategory.ACCOUNT_YIELD)

    fee_match = _ACCOUNT_FEE_RE.match(memo)
    if fee_match:
        return _Classification(BankTransactionCategory.ACCOUNT_FEE, counterparty=fee_match.group(1).strip())

    transfer_match = _AUTOMATIC_TRANSFER_RE.match(memo)
    if transfer_match:
        counterparty = transfer_match.group(1).strip() or None
        return _Classification(BankTransactionCategory.AUTOMATIC_TRANSFER, counterparty=counterparty)

    if _BALANCE_INFO_RE.match(memo):
        return _Classification(BankTransactionCategory.BALANCE_INFO)

    return _Classification(BankTransactionCategory.OTHER)


def parse_ofx(raw_text: str) -> BankStatement:
    """Extrai e classifica as transações (STMTTRN) de um extrato OFX PagBank/PagSeguro."""
    bank_id = _tag(raw_text, "BANKID") or ""
    acct_id = _tag(raw_text, "ACCTID") or ""
    acct_type = _tag(raw_text, "ACCTTYPE")
    org = _tag(raw_text, "ORG")
    fid = _tag(raw_text, "FID")
    period_start = _parse_ofx_datetime(_tag(raw_text, "DTSTART"))
    period_end = _parse_ofx_datetime(_tag(raw_text, "DTEND"))

    transactions: list[BankTransaction] = []
    for block in _STMTTRN_BLOCK_RE.findall(raw_text):
        posted_at = _parse_ofx_datetime(_tag(block, "DTPOSTED"))
        amount_raw = _tag(block, "TRNAMT")
        if posted_at is None or amount_raw is None:
            continue

        memo = _tag(block, "MEMO") or ""
        classification = _classify(memo)

        transactions.append(
            BankTransaction(
                bankId=bank_id,
                acctId=acct_id,
                fitId=_tag(block, "FITID") or "",
                trnType=_tag(block, "TRNTYPE") or "",
                postedAt=posted_at,
                amount=float(amount_raw),
                memo=memo,
                category=classification.category,
                cardMethod=classification.cardMethod,
                cardBrand=classification.cardBrand,
                acquirer=classification.acquirer,
                settlementCode=classification.settlementCode,
                counterparty=classification.counterparty,
                likelyPremmia=classification.likelyPremmia,
            )
        )

    return BankStatement(
        org=org,
        fid=fid,
        bankId=bank_id,
        acctId=acct_id,
        acctType=acct_type,
        periodStart=period_start,
        periodEnd=period_end,
        transactions=transactions,
    )


def parse_ofx_file(path: str) -> BankStatement:
    """Lê e parseia um arquivo OFX do disco (encoding tolerante a Windows-1252/UTF-8)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw_text = fh.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="cp1252") as fh:
            raw_text = fh.read()
    return parse_ofx(raw_text)
