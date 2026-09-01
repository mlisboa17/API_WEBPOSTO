"""D02+ — Modelos de extrato bancário (OFX) para conciliação cartão x banco."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class BankTransactionCategory(str, Enum):
    CARD_SETTLEMENT = "CARD_SETTLEMENT"
    """Liquidação de vendas (MEMO: 'Vendas - Disponivel {DEBITO|CREDITO} {BANDEIRA}' ou
    'Vendas - Disponivel PIX' para Pix capturado na maquininha)."""
    PIX_RECEIVED = "PIX_RECEIVED"
    """PIX recebido de terceiros (MEMO: 'Pix recebido - {origem}'). Inclui liquidações Premmia/Vibra."""
    PIX_SENT = "PIX_SENT"
    """PIX/QR Code enviado a terceiros (MEMO: 'Pix enviado - {destino}' / 'QR Code Pix enviado - {destino}')."""
    BILL_PAYMENT = "BILL_PAYMENT"
    """Pagamento de contas/fornecedores (MEMO: 'Pagamento de conta - {fornecedor}')."""
    ACCOUNT_FEE = "ACCOUNT_FEE"
    """Tarifas/cobranças da conta (ex.: 'Cobrança Seguro Cartão Protegido - ...')."""
    ACCOUNT_YIELD = "ACCOUNT_YIELD"
    """Rendimento sobre saldo em conta (MEMO: 'Rendimento da conta - ...')."""
    AUTOMATIC_TRANSFER = "AUTOMATIC_TRANSFER"
    """Transferência automática (sweep) entre contas (MEMO: 'Transferência Autom. Enviada ...'),
    formato observado em extratos Itaú. Não é Pix nem pagamento de fornecedor."""
    BALANCE_INFO = "BALANCE_INFO"
    """Linha informativa de saldo (MEMO: 'Saldo Total Disponível Dia' / 'Saldo Anterior'), sem
    movimentação real — deve ser ignorada em totais de conciliação."""
    OTHER = "OTHER"


class BankTransaction(BaseModel):
    """Um lançamento (STMTTRN) extraído de um extrato OFX."""

    bankId: str
    acctId: str
    fitId: str
    trnType: str  # IN / OUT (conforme OFX)
    postedAt: datetime
    amount: float
    memo: str
    category: BankTransactionCategory = BankTransactionCategory.OTHER
    cardMethod: str | None = None  # CREDITO / DEBITO (apenas quando category == CARD_SETTLEMENT)
    cardBrand: str | None = None  # MASTERCARD / VISA / ELO / AMEX ... (idem)
    acquirer: str | None = None  # REDE / CIELO / ... (quando o extrato identifica o adquirente, ex.: Itaú)
    settlementCode: str | None = None
    """Código bruto de liquidação do adquirente quando aplicável (ex.: AT/DB/CD nos extratos
    Itaú+Rede). AT/CD foram normalizados para CREDITO por ora; DB para DEBITO. O significado
    exato de AT (crédito à vista vs. antecipação de recebíveis) ainda não foi confirmado pelo
    negócio — mantido aqui para permitir reclassificação futura sem reparsing."""
    counterparty: str | None = None  # origem/destino (PIX_RECEIVED / PIX_SENT / BILL_PAYMENT / AUTOMATIC_TRANSFER)
    likelyPremmia: bool = False
    """Heurística: PIX recebido cuja contraparte contém 'VIBRA' — Premmia é um cartão da Vibra
    e liquida como PIX, não como MEMO de cartão (confirmado pelo negócio)."""


class BankStatement(BaseModel):
    """Extrato bancário completo (um arquivo OFX) já parseado e classificado."""

    org: str | None = None
    fid: str | None = None
    bankId: str
    acctId: str
    acctType: str | None = None
    periodStart: datetime | None = None
    periodEnd: datetime | None = None
    transactions: list[BankTransaction] = Field(default_factory=list)
