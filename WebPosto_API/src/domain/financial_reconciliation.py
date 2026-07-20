"""Contratos conservadores para conciliacao financeira da Diretoria."""

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.core.financial_vocabulary import FinancialConcept


class FinancialSource(str, Enum):
    EXPENSES = "DESPESAS_FINANCEIRO_REDE"
    PAYABLE = "TITULO_PAGAR"
    CASH_EXPENSE = "CAIXA_APRESENTADO"
    ACCOUNT_MOVEMENT = "MOVIMENTO_CONTA"


class MatchStatus(str, Enum):
    CONFIRMED = "CONFIRMADO"
    PROBABLE = "PROVAVEL_CORRESPONDENCIA"
    UNMATCHED = "SEM_CORRESPONDENCIA"
    DUPLICATE = "DUPLICIDADE"
    QUARANTINED = "AGUARDANDO_CLASSIFICACAO"


class FinancialFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    fact_id: str
    source: FinancialSource
    concept: FinancialConcept
    company_code: int
    effective_date: date
    amount: Decimal = Field(gt=0)
    document: str | None = None
    description: str | None = None
    management_account_code: str | None = None
    management_category: str | None = None
    cost_center: str | None = None
    supplier: str | None = None
    cash_register_code: str | None = None
    source_status: str | None = None
    department: str | None = None
    department_method: str = "UNCLASSIFIED"
    department_evidence: tuple[str, ...] = ()
    department_confidence: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    allocation_percentages: dict[str, Decimal] = Field(default_factory=dict)


class FinancialMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: MatchStatus
    fact_ids: tuple[str, ...]
    confidence: Decimal = Field(ge=0, le=1)
    reason: str
    may_enter_dre: bool = False


class FinancialReconciliationResult(BaseModel):
    matches: tuple[FinancialMatch, ...]
    complete_source_coverage: bool
    warnings: tuple[str, ...] = ()


class FinancialCoverage(BaseModel):
    source: FinancialSource
    complete: bool
    records: int = 0
    strategy: str
    warning: str | None = None


class ExecutiveAlertSeverity(str, Enum):
    MEDIUM = "MEDIA"
    HIGH = "ALTA"
    CRITICAL = "CRITICA"


class ExecutiveFinancialAlert(BaseModel):
    model_config = ConfigDict(frozen=True)

    alert_id: str
    alert_type: str
    severity: ExecutiveAlertSeverity
    company_code: int | None = None
    department: str | None = None
    occurrences: int = Field(ge=1)
    explanation: str
    recommended_action: str
    affects_dre: bool = False
