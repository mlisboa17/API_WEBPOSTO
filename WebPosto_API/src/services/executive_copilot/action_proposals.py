"""Propostas de ação do Copiloto. Preview DRAFT apenas — sem persistir e sem WebPosto.

Reusa os campos dos contratos existentes:
- ProductDraft (cadastro)
- LifecycleProposal / despesas (lançamento)
- ActionTask (Action Hub)
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.services.ai_ops.action_hub_service import SETORES
from src.services.catalog.schemas import ProductDraft
from src.services.executive_copilot.contracts import WEBPOSTO_WRITES
from src.services.executive_copilot.intent import ActionIntent, InterpretedQuestion, QuestionIntent
from src.services.executive_copilot.unit_capabilities import (
    is_copilot_unit,
    public_name,
    select_requested_units,
)
from src.services.proposals.schemas import LifecycleProposal

ACTION_EXECUTION_NOT_ENABLED = "ACTION_EXECUTION_NOT_ENABLED"

_EXPENSE_REQUIRED = ("valor", "descricao", "unitPublicName")
_RECLASSIFY_REQUIRED = ("lancamentoId", "planoContas", "unitPublicName")
_AUDIT_REQUIRED = ("descricao", "unitPublicName")
_PRODUCT_REQUIRED = ("descricaoPadronizada", "unitPublicName", "ean")

_UNIT_RE = re.compile(r"unidade\s+(\d{3,6})", re.IGNORECASE)
_MONEY_RE = re.compile(r"r\$\s*(-?[\d.]*\d(?:,\d{1,2})?)", re.IGNORECASE)
_PRODUCT_NAME_RE = re.compile(r"produto\s+(.+)$", re.IGNORECASE)
_EXPENSE_DESC_RE = re.compile(
    r"despesa(?:\s+de\s+r\$\s*-?[\d.,]+)?\s+de\s+(.+?)(?:\s+na\s+|\s*$)",
    re.IGNORECASE,
)
_LANCAMENTO_RE = re.compile(r"lan[cç]amento\s+(\w+)", re.IGNORECASE)
_PLANO_RE = re.compile(r"plano(?:\s+de\s+contas)?\s+(\w+)", re.IGNORECASE)


class ActionProposal(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    action_type: ActionIntent = Field(alias="actionType")
    status: Literal["DRAFT"] = "DRAFT"
    unit: int | None = Field(None, alias="unidade")
    unit_public_name: str | None = Field(None, alias="unitPublicName")
    filled: dict[str, Any] = Field(default_factory=dict, alias="camposPreenchidos")
    filled_fields: dict[str, Any] = Field(default_factory=dict, alias="filledFields")
    missing: list[str] = Field(default_factory=list, alias="camposObrigatoriosAusentes")
    missing_fields: list[str] = Field(default_factory=list, alias="missingFields")
    auto_classified: list[dict[str, Any]] = Field(default_factory=list, alias="autoClassifiedFields")
    justification: str = Field(alias="justificativa")
    risk: str = Field(alias="risco")
    requires_confirmation: bool = Field(True, alias="requiresConfirmation")
    requires_approval: bool = Field(alias="requiresApproval")
    can_execute: bool = Field(False, alias="canExecute")
    webposto_writes: int = Field(WEBPOSTO_WRITES, alias="webpostoWrites")
    source_contract: str = Field(alias="sourceContract")
    duplicate: bool = False
    persisted: bool = False
    execution_code: str | None = Field(ACTION_EXECUTION_NOT_ENABLED, alias="executionCode")


def public_filled(filled: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in filled.items():
        if key in {"empresaCodigo", "empresa_codigo"}:
            continue
        out[key] = value
    return out


def classify_expense_description(descricao: str) -> dict[str, Any] | None:
    blob = (descricao or "").casefold()
    if "gelo" in blob:
        return {
            "campo": "categoria",
            "status": "AUTO_CLASSIFIED",
            "valor": "Gelo",
            "evidencia": "regra: palavra-chave gelo",
        }
    return None


def extract_unit_from_text(question: str) -> int | None:
    named = select_requested_units(question, None)
    if named.ambiguous:
        return None
    if len(named.codes) == 1:
        return named.codes[0]
    match = _UNIT_RE.search(question or "")
    if not match:
        return None
    return int(match.group(1))


def _parse_money(question: str) -> tuple[float | None, bool]:
    match = _MONEY_RE.search(question or "")
    if not match:
        return None, False
    raw = match.group(1).replace(".", "").replace(",", ".")
    try:
        value = float(raw)
    except ValueError:
        return None, True
    if value <= 0:
        return None, True
    return round(value, 2), False


def _product_name(question: str) -> str:
    match = _PRODUCT_NAME_RE.search((question or "").strip())
    if not match:
        return ""
    return match.group(1).strip(" .")


def _expense_desc(question: str) -> str:
    match = _EXPENSE_DESC_RE.search(question or "")
    if not match:
        return ""
    text = match.group(1).strip(" .")
    named = select_requested_units(text, None)
    if named.from_text and named.names:
        for name in named.names:
            text = re.sub(re.escape(name), "", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(conveniencia|conveniência|loja)\b.*$", "", text, flags=re.IGNORECASE)
    return text.strip(" .")


def _missing(required: tuple[str, ...], filled: dict[str, Any]) -> list[str]:
    return [key for key in required if filled.get(key) in (None, "", [])]


def _licensed_unit(unit: int | None) -> int | None:
    if unit is None:
        return None
    return unit if is_copilot_unit(unit) else None


def _with_public_fields(proposal: ActionProposal) -> ActionProposal:
    filled = public_filled(dict(proposal.filled))
    if proposal.unit_public_name:
        filled["unitPublicName"] = proposal.unit_public_name
    missing = [item for item in proposal.missing if item != "empresaCodigo"]
    return proposal.model_copy(
        update={
            "filled": filled,
            "filled_fields": filled,
            "missing": missing,
            "missing_fields": list(missing),
            "can_execute": False,
            "execution_code": proposal.execution_code or ACTION_EXECUTION_NOT_ENABLED,
            "webposto_writes": WEBPOSTO_WRITES,
        }
    )


def _resolve_unit(question: str, requested: list[int]) -> int | None:
    extracted = extract_unit_from_text(question)
    if extracted is not None:
        return _licensed_unit(extracted)
    if len(requested) == 1:
        return _licensed_unit(requested[0])
    return None


def _unit_fields(unit: int | None) -> dict[str, Any]:
    if unit is None:
        return {}
    return {"unitPublicName": public_name(unit)}


def build_action_proposal(
    interpreted: InterpretedQuestion,
    *,
    requested_units: list[int],
    seen: set[str],
) -> ActionProposal:
    if interpreted.intent == QuestionIntent.CONFIRM_ACTION:
        unit = _resolve_unit(interpreted.raw, requested_units)
        return _with_public_fields(
            ActionProposal(
                actionType=ActionIntent.CONFIRM_ACTION,
                unidade=unit,
                unitPublicName=public_name(unit) if unit else None,
                camposPreenchidos={},
                camposObrigatoriosAusentes=[],
                justificativa="Confirmação recebida. Executor de escrita não está habilitado nesta sprint.",
                risco="Nenhuma mutação foi aplicada.",
                requiresConfirmation=True,
                requiresApproval=True,
                webpostoWrites=WEBPOSTO_WRITES,
                sourceContract="ActionTask",
                executionCode=ACTION_EXECUTION_NOT_ENABLED,
            )
        )
    builders = {
        QuestionIntent.CREATE_PRODUCT_DRAFT: _product_preview,
        QuestionIntent.CREATE_EXPENSE_DRAFT: _expense_preview,
        QuestionIntent.RECLASSIFY_EXPENSE_DRAFT: _reclassify_preview,
        QuestionIntent.CREATE_AUDIT_TASK: _audit_preview,
    }
    return builders[interpreted.intent](interpreted.raw, requested_units, seen)


def _fingerprint(action: ActionIntent, unit: int | None, filled: dict[str, Any]) -> str:
    return "|".join(
        [
            action.value,
            str(unit or ""),
            str(filled.get("descricaoPadronizada") or filled.get("descricao") or ""),
            str(filled.get("valor") or ""),
            str(filled.get("ean") or ""),
            str(filled.get("lancamentoId") or ""),
        ]
    )


def _mark_duplicate(proposal: ActionProposal, seen: set[str]) -> ActionProposal:
    key = _fingerprint(proposal.action_type, proposal.unit, proposal.filled)
    duplicate = key in seen
    seen.add(key)
    if not duplicate:
        return proposal
    return proposal.model_copy(
        update={
            "duplicate": True,
            "risk": f"{proposal.risk} Duplicidade simulada: proposta idêntica já foi pré-visualizada.",
        }
    )


def _product_preview(question: str, units: list[int], seen: set[str]) -> ActionProposal:
    unit = _resolve_unit(question, units)
    filled: dict[str, Any] = {"descricaoPadronizada": _product_name(question), **_unit_fields(unit)}
    missing = _missing(_PRODUCT_REQUIRED, filled)
    _ = ProductDraft.model_fields
    proposal = ActionProposal(
        actionType=ActionIntent.CREATE_PRODUCT_DRAFT,
        unidade=unit,
        unitPublicName=public_name(unit) if unit else None,
        camposPreenchidos={k: v for k, v in filled.items() if v not in (None, "")},
        camposObrigatoriosAusentes=missing,
        justificativa="Preview de cadastro alinhado a ProductDraft. Campos ausentes não foram inventados.",
        risco="Sem EAN/NCM homologados o rascunho não pode ir à esteira de propostas.",
        requiresConfirmation=True,
        requiresApproval=True,
        webpostoWrites=WEBPOSTO_WRITES,
        sourceContract="ProductDraft",
    )
    return _with_public_fields(_mark_duplicate(proposal, seen))


def _expense_preview(question: str, units: list[int], seen: set[str]) -> ActionProposal:
    unit = _resolve_unit(question, units)
    amount, invalid = _parse_money(question)
    filled: dict[str, Any] = {"descricao": _expense_desc(question), **_unit_fields(unit)}
    if invalid:
        filled["valorInvalido"] = True
    elif amount is not None:
        filled["valor"] = amount
    missing = _missing(_EXPENSE_REQUIRED, filled)
    if invalid:
        missing = [item for item in missing if item != "valor"]
        if "valor" not in missing:
            missing.insert(0, "valor")
    auto = []
    suggested = classify_expense_description(str(filled.get("descricao") or ""))
    if suggested:
        auto.append(suggested)
    _ = LifecycleProposal.model_fields
    risk = "Lançamento de caixa exige homologação. Nenhuma escrita local ou WebPosto."
    if invalid:
        risk = "Valor inválido informado. Não inventei substituto."
    proposal = ActionProposal(
        actionType=ActionIntent.CREATE_EXPENSE_DRAFT,
        unidade=unit,
        unitPublicName=public_name(unit) if unit else None,
        camposPreenchidos={k: v for k, v in filled.items() if v not in (None, "")},
        camposObrigatoriosAusentes=missing,
        autoClassifiedFields=auto,
        justificativa="Preview de despesa alinhado à esteira de propostas/despesas. Sem persistência.",
        risco=risk,
        requiresConfirmation=True,
        requiresApproval=True,
        webpostoWrites=WEBPOSTO_WRITES,
        sourceContract="LifecycleProposal",
        persisted=False,
    )
    return _with_public_fields(_mark_duplicate(proposal, seen))


def _reclassify_preview(question: str, units: list[int], seen: set[str]) -> ActionProposal:
    unit = _resolve_unit(question, units)
    lancamento = _LANCAMENTO_RE.search(question or "")
    plano = _PLANO_RE.search(question or "")
    filled: dict[str, Any] = dict(_unit_fields(unit))
    if lancamento:
        filled["lancamentoId"] = lancamento.group(1)
    if plano:
        filled["planoContas"] = plano.group(1)
    proposal = ActionProposal(
        actionType=ActionIntent.RECLASSIFY_EXPENSE_DRAFT,
        unidade=unit,
        unitPublicName=public_name(unit) if unit else None,
        camposPreenchidos=filled,
        camposObrigatoriosAusentes=_missing(_RECLASSIFY_REQUIRED, filled),
        justificativa="Preview de reclassificação. Não chama ExpenseReclassifyService.",
        risco="Override persistido só existirá em sprint futura com aprovação.",
        requiresConfirmation=True,
        requiresApproval=True,
        webpostoWrites=WEBPOSTO_WRITES,
        sourceContract="ExpenseReclassify",
    )
    return _with_public_fields(_mark_duplicate(proposal, seen))


def _audit_preview(question: str, units: list[int], seen: set[str]) -> ActionProposal:
    unit = _resolve_unit(question, units)
    filled: dict[str, Any] = {
        "descricao": (question or "").strip(),
        "agenteOrigem": "FinanceiroIA",
        "responsavelSetor": SETORES["FinanceiroIA"],
        **_unit_fields(unit),
    }
    proposal = ActionProposal(
        actionType=ActionIntent.CREATE_AUDIT_TASK,
        unidade=unit,
        unitPublicName=public_name(unit) if unit else None,
        camposPreenchidos=filled,
        camposObrigatoriosAusentes=_missing(_AUDIT_REQUIRED, filled),
        justificativa="Preview de ActionTask. Action Hub não foi gravado.",
        risco="Tarefa interna sem impacto financeiro executado.",
        requiresConfirmation=True,
        requiresApproval=False,
        webpostoWrites=WEBPOSTO_WRITES,
        sourceContract="ActionTask",
    )
    return _with_public_fields(_mark_duplicate(proposal, seen))

