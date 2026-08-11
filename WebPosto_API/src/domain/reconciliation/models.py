"""D02 — Domínio de Conferência Financeira de Caixa."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PaymentNatureCode(str, Enum):
    DINHEIRO = "DINHEIRO"
    NOTAS = "NOTAS"
    CHEQUE_VISTA = "CHEQUE_VISTA"
    CHEQUE_PRE = "CHEQUE_PRE"
    CARTAO = "CARTAO"
    CARTA_FRETE = "CARTA_FRETE"
    VALE_CLIENTE = "VALE_CLIENTE"
    DESPESA = "DESPESA"
    EMPRESTIMO = "EMPRESTIMO"
    PRE_PAGO = "PRE_PAGO"
    VALE_FUNCIONARIO = "VALE_FUNCIONARIO"
    TRANSFERENCIA_CREDITO = "TRANSFERENCIA_CREDITO"
    TRANSFERENCIA_DEBITO = "TRANSFERENCIA_DEBITO"
    CHEQUE_PAGAR = "CHEQUE_PAGAR"
    FUNDO_CAIXA_DEBITO = "FUNDO_CAIXA_DEBITO"


class CaptureOrigin(str, Enum):
    TEF = "TEF"
    POS_MANUAL = "POS_MANUAL"
    CASH_REGISTER = "CASH_REGISTER"
    BANK_TRANSFER = "BANK_TRANSFER"
    INTERNAL = "INTERNAL"
    UNKNOWN = "UNKNOWN"


class ExpectedDestination(str, Enum):
    CASH = "CASH"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    ACQUIRER_RECEIVABLE = "ACQUIRER_RECEIVABLE"
    EMPLOYEE_BALANCE = "EMPLOYEE_BALANCE"
    CUSTOMER_BALANCE = "CUSTOMER_BALANCE"
    EXPENSE_LEDGER = "EXPENSE_LEDGER"
    INTERNAL_ACCOUNT = "INTERNAL_ACCOUNT"
    OTHER = "OTHER"


class ReconciliationStatus(str, Enum):
    NOT_REVIEWED = "NOT_REVIEWED"
    IN_REVIEW = "IN_REVIEW"
    AUTO_MATCHED = "AUTO_MATCHED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    DIVERGENT = "DIVERGENT"
    JUSTIFIED = "JUSTIFIED"
    CONFIRMED = "CONFIRMED"


class PreCheckOutcome(str, Enum):
    AUTO_MATCHED = "AUTO_MATCHED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    DIVERGENT = "DIVERGENT"
    JUSTIFIED = "JUSTIFIED"
    CONFIRMED = "CONFIRMED"


class JustificationCategory(str, Enum):
    NEXT_BUSINESS_DAY = "NEXT_BUSINESS_DAY"
    BANK_PROCESSING = "BANK_PROCESSING"
    ACQUIRER_DELAY = "ACQUIRER_DELAY"
    MANUAL_ENTRY_ERROR = "MANUAL_ENTRY_ERROR"
    CASH_SHORTAGE = "CASH_SHORTAGE"
    CASH_SURPLUS = "CASH_SURPLUS"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    OPERATIONAL_ERROR = "OPERATIONAL_ERROR"
    OTHER = "OTHER"


class AuditSignalType(str, Enum):
    UNJUSTIFIED_DIVERGENCE = "UNJUSTIFIED_DIVERGENCE"
    THRESHOLD_EXCEEDED = "THRESHOLD_EXCEEDED"
    RECURRING_NATURE = "RECURRING_NATURE"
    RECURRING_CAIXA = "RECURRING_CAIXA"
    RECURRING_OPERATOR = "RECURRING_OPERATOR"
    RECLASSIFICATION_PATTERN = "RECLASSIFICATION_PATTERN"
    EXCESSIVE_OTHER = "EXCESSIVE_OTHER"
    OVERDUE_OPEN = "OVERDUE_OPEN"


class AuditSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReconciliationEvidence(BaseModel):
    source: str
    externalReference: str | None = None
    amount: float
    effectiveDate: str | None = None
    status: str = "AVAILABLE"


class JustificationRecord(BaseModel):
    id: str
    reasonCategory: JustificationCategory
    description: str
    expectedResolutionDate: str | None = None
    responsibleUser: str
    createdAt: str
    createdBy: str | None = None


class CardBreakdown(BaseModel):
    rawPaymentLabel: str
    normalizedBrand: str = "UNKNOWN"
    normalizedMethod: str = "UNKNOWN"
    normalizedAcquirer: str = "UNKNOWN"
    captureOrigin: CaptureOrigin = CaptureOrigin.UNKNOWN
    grossAmount: float = 0.0
    feeRate: float | None = None
    expectedNet: float | None = None
    settlementDate: str | None = None
    destinationAccount: str | None = None


class ReconciliationItem(BaseModel):
    id: str
    filial: int | str
    caixaCodigo: int | str | None = None
    turno: str | None = None
    consolidationStatus: str = "UNKNOWN"
    consolidationEvidence: str | None = None
    # WebPosto `fechado` — distinto de consolidado (CASH-01S).
    # True/False quando o campo raw existe; None = ausente (não inventar CLOSED).
    caixaFechado: bool | None = None
    periodoInicio: str
    periodoFim: str
    paymentNature: PaymentNatureCode
    captureOrigin: CaptureOrigin = CaptureOrigin.CASH_REGISTER
    valorApresentado: float = 0.0
    valorApurado: float = 0.0
    valorEsperado: float = 0.0
    valorRealizado: float | None = None
    sangria: float | None = None
    diferenca: float = 0.0
    expectedDestination: ExpectedDestination = ExpectedDestination.OTHER
    evidences: list[ReconciliationEvidence] = Field(default_factory=list)
    cardBreakdown: list[CardBreakdown] = Field(default_factory=list)
    status: ReconciliationStatus = ReconciliationStatus.NOT_REVIEWED
    preCheckOutcome: PreCheckOutcome | None = None
    justifications: list[JustificationRecord] = Field(default_factory=list)
    responsibleUser: str | None = None
    updatedAt: str | None = None


class NatureSummaryCard(BaseModel):
    paymentNature: PaymentNatureCode
    label: str
    valorApurado: float
    valorApresentado: float
    sangria: float | None = None
    diferenca: float
    status: ReconciliationStatus
    itemsCount: int
    reviewedCount: int
    openCount: int
    autoMatchedCount: int = 0
    humanConfirmedCount: int = 0


class PreCheckSummary(BaseModel):
    totalAnalyzed: int
    autoMatched: int
    needsReview: int
    divergent: int
    justified: int
    confirmed: int
    divergentAmount: float


class ReconciliationSummary(BaseModel):
    filial: int | str | None
    periodoInicio: str
    periodoFim: str
    valorApurado: float
    valorApresentado: float = 0.0
    valorConferido: float
    valorDivergente: float
    valorPendente: float
    naturezasConferidas: int
    naturezasTotal: int
    natureCards: list[NatureSummaryCard]
    preCheck: PreCheckSummary
    auditSignals: list[dict[str, Any]] = Field(default_factory=list)


class AuditSignal(BaseModel):
    signalType: AuditSignalType
    severity: AuditSeverity
    entityType: str
    entityId: str
    amount: float
    occurrenceCount: int
    firstOccurrence: str
    lastOccurrence: str
    explanation: str
    status: str = "OPEN"
