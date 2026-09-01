"""Interpretação determinística da pergunta. Sem LLM."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from src.services.executive_copilot.contracts import SpecialistId


class ActionIntent(StrEnum):
    CREATE_PRODUCT_DRAFT = "CREATE_PRODUCT_DRAFT"
    CREATE_EXPENSE_DRAFT = "CREATE_EXPENSE_DRAFT"
    RECLASSIFY_EXPENSE_DRAFT = "RECLASSIFY_EXPENSE_DRAFT"
    CREATE_AUDIT_TASK = "CREATE_AUDIT_TASK"
    EXECUTIVE_QUERY = "EXECUTIVE_QUERY"
    CONFIRM_ACTION = "CONFIRM_ACTION"


class QuestionIntent(StrEnum):
    SALES = "SALES"
    LITERS = "LITERS"
    ABASTECIMENTOS = "ABASTECIMENTOS"
    VOLUME_COUNT = "VOLUME_COUNT"
    TICKET = "TICKET"
    COMPARE = "COMPARE"
    PROFIT = "PROFIT"
    EXPENSE = "EXPENSE"
    CASH = "CASH"
    ECONOMY = "ECONOMY"
    CREATE_PRODUCT_DRAFT = "CREATE_PRODUCT_DRAFT"
    CREATE_EXPENSE_DRAFT = "CREATE_EXPENSE_DRAFT"
    RECLASSIFY_EXPENSE_DRAFT = "RECLASSIFY_EXPENSE_DRAFT"
    CREATE_AUDIT_TASK = "CREATE_AUDIT_TASK"
    CONFIRM_ACTION = "CONFIRM_ACTION"
    UNSUPPORTED = "UNSUPPORTED"


ACTION_QUESTION_INTENTS = frozenset(
    {
        QuestionIntent.CREATE_PRODUCT_DRAFT,
        QuestionIntent.CREATE_EXPENSE_DRAFT,
        QuestionIntent.RECLASSIFY_EXPENSE_DRAFT,
        QuestionIntent.CREATE_AUDIT_TASK,
        QuestionIntent.CONFIRM_ACTION,
    }
)


@dataclass(frozen=True)
class InterpretedQuestion:
    intent: QuestionIntent
    specialist: SpecialistId
    compare: bool
    raw: str
    action: ActionIntent = ActionIntent.EXECUTIVE_QUERY


_PROFIT = ("lucro", "margem", "cmv", "resultado operacional")
_EXPENSE = ("despesa", "despesas")
_CASH = ("quebra de caixa", "fechamento de caixa", "sangria")
_ECONOMY = ("economiz", "economia comprovada", "quanto poupar")
_TICKET = ("ticket",)
_COUNT = ("abastecimento", "abastecimentos")
_LITERS = ("litro", "litros", "volume", "volumetria")
_SALES = ("faturamento", "venda", "vendas", "receita")
_COMPARE = ("compar", "versus", " vs ", "qual unidade", "qual posto", "entre unidades")
_GENERIC = ("resumo", "panorama", "como estamos", "visao geral", "visão geral")
_CONFIRM = (" confirme", " confirmar", " confirma ", "confirmado")
_PRODUCT_ACTION = ("cadastr", "cadastre", "criar produto", "crie o produto", "novo produto")
_EXPENSE_ACTION = ("lance ", "lançar ", "lancar ", "registre uma despesa", "registrar despesa", "criar despesa")
_RECLASSIFY = ("reclassif",)
_AUDIT_TASK = ("tarefa de auditoria", "tarefa de auditor", "crie uma tarefa", "criar tarefa de auditoria")


def is_comparative(interpreted: InterpretedQuestion) -> bool:
    """Comparação exige intenção COMPARE ou flag compare (ex.: faturamento + 'entre unidades')."""
    return interpreted.compare or interpreted.intent == QuestionIntent.COMPARE


def _action(intent: QuestionIntent, specialist: SpecialistId, question: str, *, compare: bool = False) -> InterpretedQuestion:
    mapping = {
        QuestionIntent.CREATE_PRODUCT_DRAFT: ActionIntent.CREATE_PRODUCT_DRAFT,
        QuestionIntent.CREATE_EXPENSE_DRAFT: ActionIntent.CREATE_EXPENSE_DRAFT,
        QuestionIntent.RECLASSIFY_EXPENSE_DRAFT: ActionIntent.RECLASSIFY_EXPENSE_DRAFT,
        QuestionIntent.CREATE_AUDIT_TASK: ActionIntent.CREATE_AUDIT_TASK,
        QuestionIntent.CONFIRM_ACTION: ActionIntent.CONFIRM_ACTION,
    }
    return InterpretedQuestion(intent, specialist, compare, question, mapping[intent])


def interpret_question(question: str, specialist: SpecialistId) -> InterpretedQuestion:
    blob = f" {str(question or '').strip().casefold()} "
    if not blob.strip():
        return InterpretedQuestion(QuestionIntent.UNSUPPORTED, specialist, False, question)

    if any(token in blob for token in _CONFIRM):
        return _action(QuestionIntent.CONFIRM_ACTION, specialist, question)
    if any(token in blob for token in _RECLASSIFY):
        return _action(QuestionIntent.RECLASSIFY_EXPENSE_DRAFT, specialist, question)
    if any(token in blob for token in _PRODUCT_ACTION) and "produto" in blob:
        return _action(QuestionIntent.CREATE_PRODUCT_DRAFT, specialist, question)
    if any(token in blob for token in _EXPENSE_ACTION) and "despesa" in blob:
        return _action(QuestionIntent.CREATE_EXPENSE_DRAFT, specialist, question)
    if any(token in blob for token in _AUDIT_TASK):
        return _action(QuestionIntent.CREATE_AUDIT_TASK, specialist, question)

    if any(token in blob for token in _PROFIT):
        return InterpretedQuestion(QuestionIntent.PROFIT, specialist, False, question)
    if any(token in blob for token in _EXPENSE):
        return InterpretedQuestion(QuestionIntent.EXPENSE, specialist, False, question)
    if any(token in blob for token in _CASH):
        return InterpretedQuestion(QuestionIntent.CASH, specialist, False, question)
    if any(token in blob for token in _ECONOMY):
        return InterpretedQuestion(QuestionIntent.ECONOMY, specialist, False, question)

    compare = any(token in blob for token in _COMPARE)
    if any(token in blob for token in _TICKET):
        return InterpretedQuestion(QuestionIntent.TICKET, specialist, compare, question)
    wants_count = any(token in blob for token in _COUNT)
    wants_liters = any(token in blob for token in _LITERS)
    if wants_count and wants_liters:
        return InterpretedQuestion(QuestionIntent.VOLUME_COUNT, specialist, compare, question)
    if wants_count:
        return InterpretedQuestion(QuestionIntent.ABASTECIMENTOS, specialist, compare, question)
    if wants_liters:
        return InterpretedQuestion(QuestionIntent.LITERS, specialist, compare, question)
    if any(token in blob for token in _SALES):
        return InterpretedQuestion(QuestionIntent.SALES, specialist, compare, question)
    if compare:
        return InterpretedQuestion(QuestionIntent.COMPARE, specialist, True, question)

    if any(token in blob for token in _GENERIC):
        if specialist == "OPERACIONAL":
            return InterpretedQuestion(QuestionIntent.LITERS, specialist, False, question)
        if specialist == "FINANCEIRO":
            return InterpretedQuestion(QuestionIntent.SALES, specialist, False, question)
        return InterpretedQuestion(QuestionIntent.COMPARE, specialist, True, question)

    return InterpretedQuestion(QuestionIntent.UNSUPPORTED, specialist, False, question)
