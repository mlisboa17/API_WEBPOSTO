"""Cálculos determinísticos de pista a partir de fatos locais. Sem rede."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol

from src.services.sds_identity import COMPLETE_STATUSES, STATUS_SEM_MOVIMENTO, summarize_abastecimentos


@dataclass(frozen=True)
class UnitDayFacts:
    empresa_codigo: int
    data_referencia: date
    status: str
    litros: float | None = None
    faturamento: float | None = None
    quantidade: int | None = None
    registros_sem_identidade: int = 0
    rows: tuple[dict, ...] = ()


@dataclass(frozen=True)
class UnitMetric:
    empresa_codigo: int
    litros: float
    faturamento: float
    quantidade: int | None
    ticket_reais: float | None
    ticket_litros: float | None
    contagem_confiavel: bool
    sem_movimento: bool


class FuelFactsStore(Protocol):
    def list_facts(self, units: list[int], start: date, end: date) -> list[UnitDayFacts]: ...


class MemoryFuelFactsStore:
    def __init__(self, rows: list[UnitDayFacts] | None = None) -> None:
        self._rows = list(rows or [])

    def list_facts(self, units: list[int], start: date, end: date) -> list[UnitDayFacts]:
        allowed = set(units)
        return [
            row
            for row in self._rows
            if row.empresa_codigo in allowed and start <= row.data_referencia <= end
        ]


class LocalSourceError(RuntimeError):
    """Falha de leitura local. Mensagem já sanitizada."""


def _ticket(num: float, den: int | None, confiavel: bool) -> float | None:
    if not confiavel or den in (None, 0):
        return None
    return round(num / den, 4)


def aggregate_unit_facts(days: list[UnitDayFacts]) -> UnitMetric:
    litros = 0.0
    faturamento = 0.0
    quantidade = 0
    has_qty = True
    confiavel = True
    raw_rows: list[dict] = []
    all_sem = True
    for day in days:
        if day.status not in COMPLETE_STATUSES:
            raise LocalSourceError("dia incompleto chegou ao cálculo")
        if day.status != STATUS_SEM_MOVIMENTO:
            all_sem = False
        if day.rows:
            raw_rows.extend(day.rows)
        if day.litros is not None:
            litros += float(day.litros)
        if day.faturamento is not None:
            faturamento += float(day.faturamento)
        if int(day.registros_sem_identidade or 0) > 0:
            confiavel = False
            has_qty = False
        if day.quantidade is None:
            has_qty = False
        else:
            quantidade += int(day.quantidade)

    missing_numbers = any(
        day.status != STATUS_SEM_MOVIMENTO and (day.litros is None or day.faturamento is None)
        for day in days
    )
    if missing_numbers and not raw_rows:
        raise LocalSourceError("fatos locais incompletos")

    if raw_rows:
        summary = summarize_abastecimentos(list(raw_rows))
        litros = float(summary["litrosVendidos"] or 0.0)
        faturamento = float(summary["faturamentoCombustivel"] or 0.0)
        confiavel = bool(summary["contagemConfiavel"])
        quantidade = int(summary["quantidadeAbastecimentos"] or 0) if confiavel else 0
        has_qty = confiavel
    elif not has_qty:
        confiavel = False

    qty = quantidade if has_qty else None
    return UnitMetric(
        empresa_codigo=days[0].empresa_codigo,
        litros=round(litros, 3),
        faturamento=round(faturamento, 2),
        quantidade=qty,
        ticket_reais=_ticket(faturamento, qty, confiavel),
        ticket_litros=_ticket(litros, qty, confiavel),
        contagem_confiavel=bool(confiavel and has_qty),
        sem_movimento=all_sem and litros == 0 and faturamento == 0,
    )


def _days(start: date, end: date) -> list[date]:
    cursor = start
    out: list[date] = []
    while cursor <= end:
        out.append(cursor)
        cursor += timedelta(days=1)
    return out


def aggregate_network(
    facts: list[UnitDayFacts],
    units: list[int],
    start: date | None = None,
    end: date | None = None,
) -> dict[int, UnitMetric]:
    by_key = {(row.empresa_codigo, row.data_referencia): row for row in facts}
    out: dict[int, UnitMetric] = {}
    if start is None or end is None:
        by_unit: dict[int, list[UnitDayFacts]] = {code: [] for code in units}
        for row in facts:
            if row.empresa_codigo in by_unit:
                by_unit[row.empresa_codigo].append(row)
        for code, days in by_unit.items():
            if not days:
                raise LocalSourceError("fatos locais ausentes para unidade coberta")
            out[code] = aggregate_unit_facts(days)
        return out
    for code in units:
        days = []
        for day in _days(start, end):
            row = by_key.get((code, day))
            if row is None:
                raise LocalSourceError("fatos locais ausentes para unidade/dia coberto")
            days.append(row)
        out[code] = aggregate_unit_facts(days)
    return out
