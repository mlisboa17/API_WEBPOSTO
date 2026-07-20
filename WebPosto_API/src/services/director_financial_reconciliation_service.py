"""Conciliacao de fatos financeiros sem somas ou matches especulativos."""

from collections import defaultdict
from decimal import Decimal

from src.core.financial_vocabulary import FinancialConcept
from src.domain.financial_reconciliation import (
    FinancialFact,
    FinancialMatch,
    FinancialReconciliationResult,
    FinancialSource,
    MatchStatus,
)


class DirectorFinancialReconciliationService:
    @staticmethod
    def _exact_key(fact: FinancialFact) -> tuple[int, object, Decimal]:
        return fact.company_code, fact.effective_date, fact.amount.quantize(Decimal("0.01"))

    @staticmethod
    def _duplicate_key(fact: FinancialFact) -> tuple[object, ...]:
        return (
            fact.source,
            fact.company_code,
            fact.effective_date,
            fact.amount.quantize(Decimal("0.01")),
            fact.document or "",
            fact.management_account_code or "",
            fact.cash_register_code or "",
        )

    def reconcile(
        self,
        facts: list[FinancialFact],
        *,
        complete_source_coverage: bool,
    ) -> FinancialReconciliationResult:
        matches: list[FinancialMatch] = []
        consumed: set[str] = set()
        duplicate_groups: dict[tuple[object, ...], list[FinancialFact]] = defaultdict(list)
        for fact in facts:
            duplicate_groups[self._duplicate_key(fact)].append(fact)
        for group in duplicate_groups.values():
            if len(group) < 2:
                continue
            ids = tuple(item.fact_id for item in group)
            consumed.update(ids)
            matches.append(FinancialMatch(
                status=MatchStatus.DUPLICATE,
                fact_ids=ids,
                confidence=Decimal("1"),
                reason="Mesma origem, empresa, data, valor e referencias.",
            ))

        exact: dict[tuple[int, object, Decimal], list[FinancialFact]] = defaultdict(list)
        for fact in facts:
            if fact.fact_id not in consumed:
                exact[self._exact_key(fact)].append(fact)
        for group in exact.values():
            sources = {item.source for item in group}
            if FinancialSource.EXPENSES not in sources or len(sources) < 2 or len(group) != 2:
                continue
            first, second = group
            document_match = bool(first.document and second.document and first.document == second.document)
            account_match = bool(first.management_account_code and second.management_account_code
                                 and first.management_account_code == second.management_account_code)
            status = MatchStatus.CONFIRMED if document_match or account_match else MatchStatus.PROBABLE
            ids = (first.fact_id, second.fact_id)
            consumed.update(ids)
            matches.append(FinancialMatch(
                status=status,
                fact_ids=ids,
                confidence=Decimal("1.00") if status == MatchStatus.CONFIRMED else Decimal("0.70"),
                reason=("Empresa, data e valor iguais, com documento/plano coincidente."
                        if status == MatchStatus.CONFIRMED
                        else "Empresa, data e valor iguais; referencias insuficientes."),
                may_enter_dre=status == MatchStatus.CONFIRMED,
            ))

        for fact in facts:
            if fact.fact_id in consumed:
                continue
            if (fact.department is None and not fact.allocation_percentages
                    and fact.concept == FinancialConcept.FINANCIAL_EXPENSE):
                status = MatchStatus.QUARANTINED
                reason = "Despesa sem departamento comprovado."
            else:
                status = MatchStatus.UNMATCHED
                reason = "Nenhuma evidencia suficiente em outra origem."
            matches.append(FinancialMatch(
                status=status,
                fact_ids=(fact.fact_id,),
                confidence=Decimal("0"),
                reason=reason,
            ))

        warnings = (() if complete_source_coverage else
                    ("Cobertura integral das fontes nao comprovada; totais executivos bloqueados.",))
        return FinancialReconciliationResult(
            matches=tuple(matches),
            complete_source_coverage=complete_source_coverage,
            warnings=warnings,
        )
