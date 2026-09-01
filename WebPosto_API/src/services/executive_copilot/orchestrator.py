"""Orquestração do Copiloto Executivo. Interpreta, lê local, calcula e valida."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.services.executive_copilot.access import NETWORK_ROLES, restrict_requested_units
from src.services.executive_copilot.contracts import (
    WEBPOSTO_WRITES,
    ClaimStatus,
    CopilotAnswer,
    Impact,
    SourceNature,
    SpecialistId,
)
from src.services.executive_copilot.coverage import (
    CheckpointSdsCoverageProvider,
    CheckpointStore,
    MemoryCheckpointStore,
    common_checkpoint_coverage,
    empty_common_coverage,
)
from src.services.executive_copilot.action_proposals import (
    ACTION_EXECUTION_NOT_ENABLED,
    build_action_proposal,
    extract_unit_from_text,
)
from src.services.executive_copilot.http_models import AskRequest
from src.services.executive_copilot.intent import (
    ACTION_QUESTION_INTENTS,
    InterpretedQuestion,
    QuestionIntent,
    interpret_question,
    is_comparative,
)
from src.services.executive_copilot.llm_port import DeterministicNarrator, NarrativePort
from src.services.executive_copilot.metrics import (
    FuelFactsStore,
    LocalSourceError,
    MemoryFuelFactsStore,
    UnitMetric,
    aggregate_network,
)
from src.services.executive_copilot.source_registry import TruthGate
from src.services.executive_copilot.unit_capabilities import (
    ACTION_NETWORK_SCOPE_FORBIDDEN,
    MANAGER_NETWORK_SCOPE_FORBIDDEN,
    UNIT_NAME_AMBIGUOUS,
    UNIT_REQUIRED_FOR_ACTION,
    UNIT_SOURCE_NOT_APPLICABLE,
    UNIT_SOURCE_NOT_APPLICABLE_MESSAGE,
    compatible_units,
    is_fuel_capability,
    public_name,
    public_names,
    select_requested_units,
    source_for_intent,
    user_role,
)
from src.services.sds_sanitize import sanitize_text

COMPARISON_REQUIRES_MULTIPLE_UNITS = "COMPARISON_REQUIRES_MULTIPLE_UNITS"
COMPARISON_MIN_UNITS = 2
COMPARISON_BLOCKED_MESSAGE = (
    "Selecione pelo menos duas unidades ou Todas as Filiais para realizar uma comparação."
)


class ExecutiveCopilotOrchestrator:
    def __init__(
        self,
        checkpoint_store: CheckpointStore | None = None,
        facts_store: FuelFactsStore | None = None,
        narrator: NarrativePort | None = None,
    ) -> None:
        self._checkpoints = checkpoint_store or MemoryCheckpointStore()
        self._facts = facts_store or MemoryFuelFactsStore()
        self._narrator = narrator or DeterministicNarrator()
        self._action_previews: set[str] = set()

    def ask(self, request: AskRequest, user: dict[str, Any] | None) -> CopilotAnswer:
        specialist = request.specialist
        gate = TruthGate()

        # 1. Resolver nomes e aliases.
        selection = select_requested_units(request.question, request.units)
        if selection.ambiguous:
            return _named_blocked(
                specialist,
                UNIT_NAME_AMBIGUOUS,
                "Informe a unidade completa. “Loja” isolado é ambíguo.",
                [],
            )

        # 2. Verificar autorização.
        role = user_role(user)
        todas = selection.all_units
        if todas and role not in NETWORK_ROLES:
            return _named_blocked(
                specialist,
                MANAGER_NETWORK_SCOPE_FORBIDDEN,
                "Manager não opera em Todas as Unidades.",
                [],
            )
        if todas:
            resolved = restrict_requested_units(None, user)
        elif selection.from_text and selection.codes:
            resolved = restrict_requested_units(selection.codes, user)
        else:
            resolved = restrict_requested_units(request.units, user)
        if resolved.blocked:
            return gate.blocked_answer(
                specialist=specialist,
                question=request.question,
                reason=resolved.blocked["message"],
                code=resolved.blocked["code"],
            )

        # 3. Detectar intenção e métrica.
        interpreted = interpret_question(request.question, specialist)
        comparative = is_comparative(interpreted)
        capability = source_for_intent(interpreted.intent)

        if interpreted.intent in ACTION_QUESTION_INTENTS:
            return self._action_answer(request, user, resolved.units, interpreted, todas=todas)

        explicit = list(selection.codes if selection.from_text else (request.units or []))
        if comparative and not todas and len(explicit) < COMPARISON_MIN_UNITS:
            return _comparison_blocked(specialist, explicit)

        # 4. Filtrar unidades compatíveis com a fonte.
        compatible = compatible_units(resolved.units, capability)
        if is_fuel_capability(capability) and not compatible:
            return _source_not_applicable(specialist, resolved.units)
        if not todas and explicit and not compatible:
            return _source_not_applicable(specialist, resolved.units)
        units = compatible if is_fuel_capability(capability) else list(resolved.units)
        if not units:
            units = list(resolved.units)

        # 5. Validar cardinalidade semântica.
        if comparative and len(units) < COMPARISON_MIN_UNITS:
            return _comparison_blocked(specialist, units)

        start, end = request.period.start, request.period.end
        try:
            coverage_units = compatible_units(units, "LITROS") if is_fuel_capability(capability) else units
            coverage = CheckpointSdsCoverageProvider(self._checkpoints, coverage_units, start, end)
        except LocalSourceError as exc:
            return self._unavailable(
                gate,
                specialist,
                units,
                start,
                end,
                sanitize_text(str(exc) or "Falha na fonte local."),
                "LOCAL_SOURCE_FAILED",
            )
        except Exception:
            return self._unavailable(
                gate,
                specialist,
                units,
                start,
                end,
                "Falha na fonte local.",
                "LOCAL_SOURCE_FAILED",
            )
        gate = TruthGate(sds_complete_provider=coverage)
        if is_fuel_capability(capability) and not coverage.period_complete():
            if coverage.gaps:
                gap = coverage.gaps[0]
                day = gap["data"].isoformat() if hasattr(gap["data"], "isoformat") else str(gap["data"])
                reason = sanitize_text(f"Cobertura SDS incompleta em {day}. Catch-up não autorizado.")
            elif coverage.last_complete_date() is None:
                reason = "Nenhuma data SDS completa comprovada para o período e unidades."
            else:
                reason = f"Período posterior a {coverage.last_complete_date().isoformat()} sem catch-up autorizado."
            return gate.blocked_answer(
                specialist=specialist,
                question=request.question,
                reason=reason,
                code="PERIOD_BLOCKED",
            )

        if interpreted.intent == QuestionIntent.UNSUPPORTED:
            return self._unavailable(
                gate,
                specialist,
                units,
                start,
                end,
                "Pergunta não suportada. Não invento resposta livre.",
                "QUESTION_UNSUPPORTED",
            )
        if interpreted.intent in {QuestionIntent.PROFIT, QuestionIntent.EXPENSE, QuestionIntent.CASH}:
            draft = self._narrator.compose(interpreted, None, start=start.isoformat(), end=end.isoformat())
            answer = gate.build_answer(
                specialist=specialist,
                question=request.question,
                fact=draft.fact,
                inference=draft.inference,
                recommendation=draft.recommendation,
                impact=Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE),
                units=units,
                suggested_action={
                    "engine": draft.engine,
                    "llm": draft.llm,
                    "webpostoWrites": WEBPOSTO_WRITES,
                    "unitPublicNames": public_names(units),
                },
            )
            if draft.llm and draft.answer:
                answer.answer = draft.answer
            return answer
        if interpreted.intent == QuestionIntent.ECONOMY:
            draft = self._narrator.compose(interpreted, None, start=start.isoformat(), end=end.isoformat())
            answer = gate.build_answer(
                specialist=specialist,
                question=request.question,
                fact="",
                inference=draft.inference,
                recommendation=draft.recommendation,
                impact=Impact(amount=None, currency="BRL", status=ClaimStatus.ESTIMATED),
                units=units,
                simulation={"nota": "Diferença observada não é economia comprovada.", "engine": draft.engine},
                suggested_action={"engine": draft.engine, "llm": draft.llm},
            )
            if draft.llm and draft.answer:
                answer.answer = draft.answer
            return answer

        try:
            facts = self._facts.list_facts(units, start, end)
            metrics = aggregate_network(facts, units, start, end)
        except LocalSourceError as exc:
            return self._unavailable(
                gate,
                specialist,
                units,
                start,
                end,
                sanitize_text(str(exc) or "Falha na fonte local."),
                "LOCAL_SOURCE_FAILED",
            )
        except Exception:
            return self._unavailable(
                gate,
                specialist,
                units,
                start,
                end,
                "Falha na fonte local.",
                "LOCAL_SOURCE_FAILED",
            )

        impact = _impact_for(interpreted, metrics)
        draft = self._narrator.compose(interpreted, metrics, start=start.isoformat(), end=end.isoformat())
        evidence, lineage = _evidence_lineage(units, start, end, interpreted, metrics, impact.status)
        answer = gate.build_answer(
            specialist=specialist,
            question=request.question,
            fact=draft.fact,
            inference=draft.inference,
            recommendation=draft.recommendation,
            impact=impact,
            units=units,
            evidence=evidence,
            lineage=lineage,
            period_end=end,
            suggested_action={
                "engine": draft.engine,
                "llm": draft.llm,
                "webpostoWrites": WEBPOSTO_WRITES,
                "unitPublicNames": public_names(units),
                "scope": public_names(units),
            },
        )
        if draft.llm and draft.answer:
            answer.answer = draft.answer
        return answer

    def coverage(self, units: list[int] | None, user: dict[str, Any] | None) -> dict[str, Any]:
        resolved = restrict_requested_units(units, user)
        if resolved.blocked:
            payload = empty_common_coverage([]).to_public_payload()
            payload["blocked"] = dict(resolved.blocked)
            return payload
        pista = compatible_units(resolved.units, "LITROS")
        if not pista:
            payload = empty_common_coverage([]).to_public_payload()
            payload["blocked"] = {
                "code": UNIT_SOURCE_NOT_APPLICABLE,
                "message": UNIT_SOURCE_NOT_APPLICABLE_MESSAGE,
            }
            payload["missingPairs"] = []
            return payload
        try:
            report = common_checkpoint_coverage(self._checkpoints, pista)
        except LocalSourceError as exc:
            return empty_common_coverage(
                pista,
                [{"code": "LOCAL_SOURCE_FAILED", "message": sanitize_text(str(exc) or "Falha na fonte local.")}],
            ).to_public_payload()
        except Exception:
            return empty_common_coverage(
                pista,
                [{"code": "LOCAL_SOURCE_FAILED", "message": "Falha na fonte local."}],
            ).to_public_payload()
        return report.to_public_payload()

    def _action_answer(
        self,
        request: AskRequest,
        user: dict[str, Any] | None,
        fallback_units: list[int],
        interpreted: InterpretedQuestion,
        *,
        todas: bool = False,
    ) -> CopilotAnswer:
        gate = TruthGate()
        if todas:
            return _named_blocked(
                request.specialist,
                ACTION_NETWORK_SCOPE_FORBIDDEN,
                "Ação DRAFT não opera em Todas as Unidades. Selecione uma unidade.",
                [],
            )
        extracted = extract_unit_from_text(request.question)
        units = list(fallback_units)
        if extracted is not None:
            scoped = restrict_requested_units([extracted], user)
            if scoped.blocked:
                return gate.blocked_answer(
                    specialist=request.specialist,
                    question=request.question,
                    reason=scoped.blocked["message"],
                    code=scoped.blocked["code"],
                )
            units = scoped.units
        if interpreted.intent == QuestionIntent.CREATE_EXPENSE_DRAFT and len(units) != 1:
            return _named_blocked(
                request.specialist,
                UNIT_REQUIRED_FOR_ACTION,
                "Informe a unidade da despesa. Ex.: Conveniência 24 Horas.",
                units,
            )
        proposal = build_action_proposal(
            interpreted,
            requested_units=units,
            seen=self._action_previews,
        )
        answer_units = [proposal.unit] if proposal.unit is not None else units
        if proposal.execution_code == ACTION_EXECUTION_NOT_ENABLED and interpreted.intent == QuestionIntent.CONFIRM_ACTION:
            fact = "Confirmação não executa nesta sprint: ACTION_EXECUTION_NOT_ENABLED."
        elif proposal.missing:
            fact = f"Proposta DRAFT incompleta. Informe: {', '.join(proposal.missing)}."
        else:
            fact = f"Proposta {proposal.action_type.value} em DRAFT. Nenhuma escrita foi feita."
        payload = proposal.model_dump(by_alias=True)
        payload["engine"] = "deterministic"
        payload["llm"] = False
        payload["persisted"] = False
        payload["canExecute"] = False
        payload["executionCode"] = ACTION_EXECUTION_NOT_ENABLED
        payload["webpostoWrites"] = WEBPOSTO_WRITES
        if "empresaCodigo" in (payload.get("camposPreenchidos") or {}):
            payload["camposPreenchidos"].pop("empresaCodigo", None)
        if "empresaCodigo" in (payload.get("filledFields") or {}):
            payload["filledFields"].pop("empresaCodigo", None)
        return gate.build_answer(
            specialist=request.specialist,
            question=request.question,
            fact=fact,
            inference="Camada de intenção e proposta. Executor desligado. WEBPOSTO_WRITES=0. Preview não persistida.",
            recommendation="Use Salvar proposta para gravar o DRAFT localmente. Confirmar não executa no ERP.",
            impact=Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE),
            units=answer_units,
            suggested_action=payload,
        )

    def _unavailable(
        self,
        gate: TruthGate,
        specialist: SpecialistId,
        units: list[int],
        start: date,
        end: date,
        reason: str,
        code: str,
    ) -> CopilotAnswer:
        return gate.build_answer(
            specialist=specialist,
            question="",
            fact=reason,
            inference="Resposta determinística. Nenhuma chamada a LLM foi feita.",
            recommendation="Ajustar a pergunta ou a cobertura local.",
            impact=Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE),
            units=units,
            suggested_action={"engine": "deterministic", "llm": False, "code": code},
        )


def _comparison_blocked(specialist: SpecialistId, current_units: list[int]) -> CopilotAnswer:
    current = list(current_units)
    names = public_names(current)
    return CopilotAnswer(
        specialist=specialist,
        answer=COMPARISON_BLOCKED_MESSAGE,
        fact="",
        inference="",
        recommendation="",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.BLOCKED),
        units=current,
        blocked={
            "code": COMPARISON_REQUIRES_MULTIPLE_UNITS,
            "message": COMPARISON_BLOCKED_MESSAGE,
        },
        suggestedAction={
            "engine": "deterministic",
            "llm": False,
            "code": COMPARISON_REQUIRES_MULTIPLE_UNITS,
            "requiredMinimumUnits": COMPARISON_MIN_UNITS,
            "currentUnits": current,
            "currentUnitPublicNames": names,
            "webpostoWrites": WEBPOSTO_WRITES,
        },
        webpostoWrites=WEBPOSTO_WRITES,
    )


def _named_blocked(specialist: SpecialistId, code: str, message: str, units: list[int]) -> CopilotAnswer:
    return CopilotAnswer(
        specialist=specialist,
        answer=message,
        fact="",
        inference="",
        recommendation="",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.BLOCKED),
        units=list(units),
        blocked={"code": code, "message": message},
        suggestedAction={
            "engine": "deterministic",
            "llm": False,
            "code": code,
            "currentUnits": list(units),
            "currentUnitPublicNames": public_names(units),
            "webpostoWrites": WEBPOSTO_WRITES,
        },
        webpostoWrites=WEBPOSTO_WRITES,
    )


def _source_not_applicable(specialist: SpecialistId, units: list[int]) -> CopilotAnswer:
    return CopilotAnswer(
        specialist=specialist,
        answer=UNIT_SOURCE_NOT_APPLICABLE_MESSAGE,
        fact="",
        inference="",
        recommendation="",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.BLOCKED),
        units=list(units),
        blocked={
            "code": UNIT_SOURCE_NOT_APPLICABLE,
            "message": UNIT_SOURCE_NOT_APPLICABLE_MESSAGE,
        },
        suggestedAction={
            "engine": "deterministic",
            "llm": False,
            "code": UNIT_SOURCE_NOT_APPLICABLE,
            "currentUnits": list(units),
            "currentUnitPublicNames": public_names(units),
            "webpostoWrites": WEBPOSTO_WRITES,
        },
        webpostoWrites=WEBPOSTO_WRITES,
    )


def _impact_for(interpreted: InterpretedQuestion, metrics: dict[int, UnitMetric]) -> Impact:
    if interpreted.intent == QuestionIntent.TICKET:
        tickets = [item.ticket_reais for item in metrics.values()]
        if any(item is None for item in tickets) or not tickets:
            return Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE)
        if len(tickets) == 1:
            return Impact(amount=tickets[0], currency="BRL", status=ClaimStatus.FACT)
        return Impact(amount=None, currency="BRL", status=ClaimStatus.FACT)
    if interpreted.intent == QuestionIntent.ABASTECIMENTOS:
        if any(not item.contagem_confiavel or item.quantidade is None for item in metrics.values()):
            return Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE)
        return Impact(amount=None, currency="BRL", status=ClaimStatus.FACT)
    if interpreted.intent in {QuestionIntent.LITERS, QuestionIntent.VOLUME_COUNT}:
        return Impact(amount=None, currency="BRL", status=ClaimStatus.FACT)
    total = round(sum(item.faturamento for item in metrics.values()), 2)
    return Impact(amount=total, currency="BRL", status=ClaimStatus.FACT)


def _evidence_summary(intent: QuestionIntent, unit: int, metric: UnitMetric) -> str:
    if intent == QuestionIntent.VOLUME_COUNT:
        if metric.contagem_confiavel and metric.quantidade is not None:
            extra = f"{metric.quantidade} abastecimentos"
            if metric.ticket_reais is not None:
                extra += f" / ticket {metric.ticket_reais}"
        else:
            extra = "abastecimentos indisponíveis"
        return f"{public_name(unit)}: {metric.litros} L / {extra}"
    if intent == QuestionIntent.ABASTECIMENTOS:
        qty = metric.quantidade if metric.contagem_confiavel else None
        return f"{intent} {public_name(unit)}: {qty} abastecimentos"
    if intent == QuestionIntent.TICKET:
        return f"{intent} {public_name(unit)}: ticket {metric.ticket_reais}"
    if intent == QuestionIntent.LITERS:
        return f"{intent} {public_name(unit)}: {metric.litros} L"
    return f"{intent} {public_name(unit)}: {metric.litros} L / {metric.faturamento} BRL"


def _evidence_lineage(
    units: list[int],
    start: date,
    end: date,
    interpreted: InterpretedQuestion,
    metrics: dict[int, UnitMetric],
    status: ClaimStatus,
) -> tuple[list[dict], list[dict]]:
    period = {"inicio": start.isoformat(), "fim": end.isoformat()}
    evidence: list[dict] = []
    lineage: list[dict] = []
    claim = status if status != ClaimStatus.ESTIMATED else ClaimStatus.FACT
    if status in {ClaimStatus.UNAVAILABLE, ClaimStatus.BLOCKED}:
        return [], []
    for unit in units:
        metric = metrics[unit]
        evidence.append(
            {
                "id": f"sds-{unit}-{end.isoformat()}",
                "fonte": "SDS",
                "resumo": _evidence_summary(interpreted.intent, unit, metric),
                "claimStatus": claim,
                "periodo": period,
                "empresaCodigo": unit,
            }
        )
        lineage.append(
            {
                "origem": "sds",
                "fonte": "sds_day_status",
                "periodo": period,
                "empresaCodigo": unit,
                "referencia": f"sds-checkpoint-{unit}-{end.isoformat()}",
                "naturezaFonte": SourceNature.CHECKPOINT,
            }
        )
    return evidence, lineage
