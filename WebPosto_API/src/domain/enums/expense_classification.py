"""Enum de classificação de despesas — Sprint 45."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExpenseClassificationStatus(str, Enum):
    """Status de classificação de uma despesa."""

    CLASSIFIED = "CLASSIFIED"
    PENDING = "PENDING_CLASSIFICATION"
    QUARANTINE = "QUARANTINE"
    REJECTED = "REJECTED"


class ExpenseClassification(str, Enum):
    """Categorias de despesas gerenciais — configurável."""

    COMBUSTIVEIS = "COMBUSTIVEIS"
    CONVENIENCIA = "CONVENIENCIA"
    LUBRIFICANTES = "LUBRIFICANTES"
    OPERACIONAL = "OPERACIONAL"
    ADMINISTRATIVA = "ADMINISTRATIVA"
    PESSOAL = "PESSOAL"
    TRIBUTARIA = "TRIBUTARIA"
    FINANCEIRA = "FINANCEIRA"
    MANUTENCAO = "MANUTENCAO"
    ENERGIA = "ENERGIA"
    ALUGUEL = "ALUGUEL"
    MARKETING = "MARKETING"
    COMPARTILHADA = "COMPARTILHADA"
    PENDENTE = "PENDENTE_CLASSIFICACAO"
    QUARENTENA = "QUARENTENA"

    @property
    def department(self) -> str | None:
        department_map = {
            ExpenseClassification.COMBUSTIVEIS: "combustiveis",
            ExpenseClassification.LUBRIFICANTES: "lubrificantes",
            ExpenseClassification.CONVENIENCIA: "conveniencia",
        }
        return department_map.get(self)

    @property
    def is_departmental(self) -> bool:
        return self.department is not None

    @property
    def requires_allocation(self) -> bool:
        return self in {
            ExpenseClassification.COMPARTILHADA,
            ExpenseClassification.OPERACIONAL,
            ExpenseClassification.ADMINISTRATIVA,
            ExpenseClassification.ENERGIA,
            ExpenseClassification.ALUGUEL,
        }

    @property
    def is_pending(self) -> bool:
        return self in {ExpenseClassification.PENDENTE, ExpenseClassification.QUARENTENA}

    @property
    def label(self) -> str:
        labels = {
            ExpenseClassification.COMBUSTIVEIS: "Despesas de Combustíveis",
            ExpenseClassification.CONVENIENCIA: "Despesas de Conveniência",
            ExpenseClassification.LUBRIFICANTES: "Despesas de Lubrificantes",
            ExpenseClassification.OPERACIONAL: "Despesas Operacionais",
            ExpenseClassification.ADMINISTRATIVA: "Despesas Administrativas",
            ExpenseClassification.PESSOAL: "Despesas de Pessoal",
            ExpenseClassification.TRIBUTARIA: "Despesas Tributárias",
            ExpenseClassification.FINANCEIRA: "Despesas Financeiras",
            ExpenseClassification.MANUTENCAO: "Manutenção e Reparos",
            ExpenseClassification.ENERGIA: "Energia e Utilidades",
            ExpenseClassification.ALUGUEL: "Aluguel e Ocupação",
            ExpenseClassification.MARKETING: "Marketing e Publicidade",
            ExpenseClassification.COMPARTILHADA: "Custos Compartilhados",
            ExpenseClassification.PENDENTE: "Pendente de Classificação",
            ExpenseClassification.QUARENTENA: "Em Quarentena",
        }
        return labels.get(self, self.value)

    @classmethod
    def from_plano_contas(cls, plano_contas_codigo: str | None) -> ExpenseClassification:
        if not plano_contas_codigo:
            return cls.PENDENTE
        code = str(plano_contas_codigo).strip()
        prefix_map = {
            "1.": cls.OPERACIONAL,
            "2.": cls.ADMINISTRATIVA,
            "3.": cls.PESSOAL,
            "4.": cls.TRIBUTARIA,
            "5.": cls.FINANCEIRA,
        }
        for prefix, classification in prefix_map.items():
            if code.startswith(prefix):
                return classification
        return cls.PENDENTE


class PendingExpenseGroup(BaseModel):
    """Agrupamento de despesas pendentes para visualização."""

    model_config = ConfigDict(frozen=True)

    plano_contas_codigo: str
    plano_contas_descricao: str | None = None
    empresa_codigo: int
    empresa_nome: str | None = None
    count: int = Field(ge=0)
    total_value: float = Field(ge=0)
    suggested_classification: ExpenseClassification = ExpenseClassification.PENDENTE
    status: ExpenseClassificationStatus = ExpenseClassificationStatus.PENDING

    @property
    def alert_level(self) -> str:
        if self.total_value >= 10000:
            return "CRITICAL"
        if self.total_value >= 1000:
            return "WARNING"
        return "INFO"


class ExpenseClassificationDecision(BaseModel):
    """Decisão de classificação de despesa — trilha de auditoria."""

    model_config = ConfigDict(frozen=True)

    expense_id: str
    plano_contas_codigo: str
    previous_classification: ExpenseClassification | None = None
    new_classification: ExpenseClassification
    reviewer: str = Field(min_length=2)
    rationale: str = Field(min_length=3)
    apply_as_rule: bool = False
    decided_at: str

    def to_audit_entry(self) -> dict[str, Any]:
        return {
            "expense_id": self.expense_id,
            "plano_contas_codigo": self.plano_contas_codigo,
            "from": self.previous_classification.value if self.previous_classification else None,
            "to": self.new_classification.value,
            "reviewer": self.reviewer,
            "rationale": self.rationale,
            "apply_as_rule": self.apply_as_rule,
            "decided_at": self.decided_at,
        }
