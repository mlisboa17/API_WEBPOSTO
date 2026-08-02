"""Serviço de Quebra de Caixa — Sprint 48."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CashBreakSeverity(str, Enum):
    """Severidade da quebra de caixa."""

    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICO = "CRITICO"


class CashBreakItem(BaseModel):
    """Quebra individual de um fechamento de caixa."""

    model_config = ConfigDict(frozen=True)

    caixa_codigo: int
    empresa_codigo: int
    data_fechamento: str
    turno: str | None = None
    operador_codigo: int | None = None
    operador_nome: str | None = None
    pdv_codigo: int | None = None

    valor_esperado: float
    valor_informado: float
    diferenca: float
    diferenca_absoluta: float

    severity: CashBreakSeverity
    requires_justification: bool = False
    justificativa: str | None = None


class CashBreakSummary(BaseModel):
    """Resumo de quebras de caixa do período."""

    model_config = ConfigDict(frozen=True)

    period_start: str
    period_end: str
    empresa_codigo: int | None = None

    total_fechamentos: int = 0
    fechamentos_com_quebra: int = 0
    fechamentos_normais: int = 0
    fechamentos_warning: int = 0
    fechamentos_criticos: int = 0

    soma_quebras_positivas: float = 0.0
    soma_quebras_negativas: float = 0.0
    soma_quebras_absoluta: float = 0.0

    maior_quebra_positiva: float = 0.0
    maior_quebra_negativa: float = 0.0

    operadores_com_quebra_critica: list[str] = Field(default_factory=list)

    items: list[CashBreakItem] = Field(default_factory=list)
    overall_status: CashBreakSeverity = CashBreakSeverity.NORMAL

    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CashBreakService:
    """Analisa quebras de caixa e gera alertas conforme régua de tolerância."""

    TOLERANCE_NORMAL = 20.0
    TOLERANCE_WARNING = 100.0

    def __init__(
        self,
        tolerance_normal: float = TOLERANCE_NORMAL,
        tolerance_warning: float = TOLERANCE_WARNING,
    ) -> None:
        self._tol_normal = tolerance_normal
        self._tol_warning = tolerance_warning

    def classify_break(self, diferenca_absoluta: float) -> CashBreakSeverity:
        if diferenca_absoluta <= self._tol_normal:
            return CashBreakSeverity.NORMAL
        elif diferenca_absoluta <= self._tol_warning:
            return CashBreakSeverity.WARNING
        else:
            return CashBreakSeverity.CRITICO

    def analyze_closure(
        self,
        caixa_codigo: int,
        empresa_codigo: int,
        data_fechamento: str,
        valor_esperado: float,
        valor_informado: float,
        turno: str | None = None,
        operador_codigo: int | None = None,
        operador_nome: str | None = None,
        pdv_codigo: int | None = None,
        justificativa: str | None = None,
    ) -> CashBreakItem:
        diferenca = valor_informado - valor_esperado
        diferenca_abs = abs(diferenca)
        severity = self.classify_break(diferenca_abs)
        requires_just = severity != CashBreakSeverity.NORMAL

        return CashBreakItem(
            caixa_codigo=caixa_codigo,
            empresa_codigo=empresa_codigo,
            data_fechamento=data_fechamento,
            turno=turno,
            operador_codigo=operador_codigo,
            operador_nome=operador_nome,
            pdv_codigo=pdv_codigo,
            valor_esperado=round(valor_esperado, 2),
            valor_informado=round(valor_informado, 2),
            diferenca=round(diferenca, 2),
            diferenca_absoluta=round(diferenca_abs, 2),
            severity=severity,
            requires_justification=requires_just,
            justificativa=justificativa,
        )

    def analyze_batch(
        self,
        closures: list[dict[str, Any]],
        period_start: str,
        period_end: str,
        empresa_codigo: int | None = None,
    ) -> CashBreakSummary:
        items: list[CashBreakItem] = []

        for closure in closures:
            item = self.analyze_closure(
                caixa_codigo=int(closure.get("caixaCodigo") or closure.get("codigo") or 0),
                empresa_codigo=int(closure.get("empresaCodigo") or empresa_codigo or 0),
                data_fechamento=str(closure.get("dataFechamento") or closure.get("data") or ""),
                valor_esperado=float(closure.get("valorEsperado") or closure.get("esperado") or 0),
                valor_informado=float(closure.get("valorInformado") or closure.get("informado") or 0),
                turno=closure.get("turno"),
                operador_codigo=closure.get("operadorCodigo"),
                operador_nome=closure.get("operadorNome"),
                pdv_codigo=closure.get("pdvCodigo"),
                justificativa=closure.get("justificativa"),
            )
            items.append(item)

        com_quebra = [i for i in items if i.severity != CashBreakSeverity.NORMAL]
        normais = [i for i in items if i.severity == CashBreakSeverity.NORMAL]
        warnings = [i for i in items if i.severity == CashBreakSeverity.WARNING]
        criticos = [i for i in items if i.severity == CashBreakSeverity.CRITICO]

        positivas = sum(i.diferenca for i in items if i.diferenca > 0)
        negativas = sum(i.diferenca for i in items if i.diferenca < 0)
        absoluta = sum(i.diferenca_absoluta for i in com_quebra)

        maior_pos = max((i.diferenca for i in items if i.diferenca > 0), default=0)
        maior_neg = min((i.diferenca for i in items if i.diferenca < 0), default=0)

        operadores_criticos = list(set(
            i.operador_nome or f"Operador {i.operador_codigo}"
            for i in criticos
            if i.operador_codigo or i.operador_nome
        ))

        if criticos:
            overall = CashBreakSeverity.CRITICO
        elif warnings:
            overall = CashBreakSeverity.WARNING
        else:
            overall = CashBreakSeverity.NORMAL

        return CashBreakSummary(
            period_start=period_start,
            period_end=period_end,
            empresa_codigo=empresa_codigo,
            total_fechamentos=len(items),
            fechamentos_com_quebra=len(com_quebra),
            fechamentos_normais=len(normais),
            fechamentos_warning=len(warnings),
            fechamentos_criticos=len(criticos),
            soma_quebras_positivas=round(positivas, 2),
            soma_quebras_negativas=round(negativas, 2),
            soma_quebras_absoluta=round(absoluta, 2),
            maior_quebra_positiva=round(maior_pos, 2),
            maior_quebra_negativa=round(maior_neg, 2),
            operadores_com_quebra_critica=operadores_criticos,
            items=sorted(items, key=lambda x: -x.diferenca_absoluta),
            overall_status=overall,
        )

    def requires_investigation(self, summary: CashBreakSummary) -> bool:
        return summary.overall_status == CashBreakSeverity.CRITICO

    def calculate_risk_score(self, summary: CashBreakSummary) -> float:
        if summary.total_fechamentos == 0:
            return 0.0

        pct_quebra = summary.fechamentos_com_quebra / summary.total_fechamentos
        pct_critico = summary.fechamentos_criticos / summary.total_fechamentos

        base_score = pct_quebra * 50
        critical_penalty = pct_critico * 50

        return min(100, round(base_score + critical_penalty, 2))
