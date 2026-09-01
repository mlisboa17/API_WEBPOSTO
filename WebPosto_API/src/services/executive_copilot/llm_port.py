"""Porta de narrativa. Nesta Frente B o motor é determinístico; LLM real permanece pendente.

Integrações existentes (não usadas aqui, sem chamada externa):
- /api/v1/ai/chat — RAG de conveniência (OpenRouter), não é cérebro executivo
- /api/v1/ai/health — health do roteador
- F05.3 executive-copilot — snapshots com unidades 5333/15880; não sustentam FACT
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.services.executive_copilot.intent import InterpretedQuestion, QuestionIntent
from src.services.executive_copilot.metrics import UnitMetric
from src.services.executive_copilot.unit_capabilities import public_name


@dataclass(frozen=True)
class NarrativeDraft:
    fact: str
    inference: str
    recommendation: str
    answer: str
    engine: str = "deterministic"
    llm: bool = False


class NarrativePort(Protocol):
    def compose(
        self,
        interpreted: InterpretedQuestion,
        metrics: dict[int, UnitMetric] | None,
        *,
        start: str,
        end: str,
    ) -> NarrativeDraft: ...


def _brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _liters(value: float) -> str:
    return f"{value:,.1f} L".replace(",", "X").replace(".", ",").replace("X", ".")


def _qty(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _counts_reliable(metrics: dict[int, UnitMetric]) -> bool:
    return bool(metrics) and all(
        item.contagem_confiavel and item.quantidade is not None for item in metrics.values()
    )


class DeterministicNarrator:
    """Texto fixo a partir dos números. Não é LLM."""

    def compose(
        self,
        interpreted: InterpretedQuestion,
        metrics: dict[int, UnitMetric] | None,
        *,
        start: str,
        end: str,
    ) -> NarrativeDraft:
        engine = (
            "Resposta determinística com dados locais SDS. "
            "Nenhuma chamada a LLM ou provedor externo foi feita."
        )
        if interpreted.intent == QuestionIntent.UNSUPPORTED:
            text = "Pergunta fora do escopo suportado nesta versão (vendas, litros, abastecimentos, ticket e comparação)."
            return NarrativeDraft(text, engine, "Reformule com um indicador suportado.", text)
        if interpreted.intent in {QuestionIntent.PROFIT, QuestionIntent.EXPENSE, QuestionIntent.CASH}:
            text = {
                QuestionIntent.PROFIT: "Lucro e margem não podem ser publicados: CMV homologado ausente. Faturamento não é lucro.",
                QuestionIntent.EXPENSE: "Despesas de caixa não têm fonte local homologada neste Copiloto.",
                QuestionIntent.CASH: "Fechamento/quebra de caixa não tem fonte local comprovada neste Copiloto.",
            }[interpreted.intent]
            return NarrativeDraft(text, engine, "Aguardar fonte local adequada.", text)
        if interpreted.intent == QuestionIntent.ECONOMY:
            text = "Diferença observada entre unidades não é economia comprovada."
            return NarrativeDraft(
                "",
                f"{text} {engine}",
                "Simulação, se houver, permanece ESTIMATED.",
                text,
            )

        assert metrics is not None
        period = f"{start} a {end}"
        fact = _fact_for(interpreted, metrics, period)
        inference = _inference_for(interpreted, metrics, engine)
        recommendation = _recommendation_for(interpreted, metrics)
        return NarrativeDraft(fact, inference, recommendation, fact)


def _fact_for(interpreted: InterpretedQuestion, metrics: dict[int, UnitMetric], period: str) -> str:
    parts: list[str] = []
    for unit, metric in metrics.items():
        if interpreted.intent == QuestionIntent.LITERS:
            parts.append(f"{public_name(unit)}: {_liters(metric.litros)}")
        elif interpreted.intent == QuestionIntent.ABASTECIMENTOS:
            qty = "indisponível" if not metric.contagem_confiavel or metric.quantidade is None else _qty(metric.quantidade)
            parts.append(f"{public_name(unit)}: {qty} abastecimentos")
        elif interpreted.intent == QuestionIntent.VOLUME_COUNT:
            parts.append(_volume_count_unit(metric))
        elif interpreted.intent == QuestionIntent.TICKET:
            ticket = "indisponível (contagem não confiável)" if metric.ticket_reais is None else _brl(metric.ticket_reais)
            parts.append(f"{public_name(unit)}: ticket {ticket}")
        else:
            parts.append(
                f"{public_name(unit)}: faturamento {_brl(metric.faturamento)} "
                f"(não é lucro) e {_liters(metric.litros)}"
            )
    body = f"No período {period}, " + "; ".join(parts) + "."
    if interpreted.intent == QuestionIntent.VOLUME_COUNT:
        body += " " + _volume_count_totals(metrics)
    return body


def _volume_count_unit(metric: UnitMetric) -> str:
    liters = f"{public_name(metric.empresa_codigo)}: {_liters(metric.litros)}"
    if metric.contagem_confiavel and metric.quantidade is not None:
        text = f"{liters} / {_qty(metric.quantidade)} abastecimentos"
        if metric.ticket_reais is not None:
            text += f" / ticket {_brl(metric.ticket_reais)}"
        return text
    return f"{liters} / abastecimentos indisponíveis (contagem não confiável)"


def _volume_count_totals(metrics: dict[int, UnitMetric]) -> str:
    total_liters = round(sum(item.litros for item in metrics.values()), 3)
    text = f"Total consolidado: {_liters(total_liters)}"
    if _counts_reliable(metrics):
        total_qty = sum(int(item.quantidade or 0) for item in metrics.values())
        text += f" / {_qty(total_qty)} abastecimentos"
    else:
        text += " / total de abastecimentos e ticket consolidado não publicados (contagem não confiável)"
    return text + "."


def _metric_point(intent: QuestionIntent, metric: UnitMetric) -> tuple[str, float | None]:
    if intent == QuestionIntent.TICKET:
        return "ticket", metric.ticket_reais
    if intent == QuestionIntent.ABASTECIMENTOS:
        qty = float(metric.quantidade) if metric.contagem_confiavel and metric.quantidade is not None else None
        return "abastecimentos", qty
    if intent == QuestionIntent.LITERS:
        return "litros", metric.litros
    if intent == QuestionIntent.VOLUME_COUNT:
        return "litros", metric.litros
    return "faturamento", metric.faturamento


def _inference_for(interpreted: InterpretedQuestion, metrics: dict[int, UnitMetric], engine: str) -> str:
    if len(metrics) < 2 or not (interpreted.compare or interpreted.intent == QuestionIntent.COMPARE):
        return engine
    label, _ = _metric_point(interpreted.intent, next(iter(metrics.values())))
    points: list[tuple[int, float]] = []
    for unit, metric in metrics.items():
        _, value = _metric_point(interpreted.intent, metric)
        if value is None:
            return (
                f"Comparação de {label} indisponível: métrica ausente em {public_name(unit)}. {engine}"
            )
        points.append((unit, value))
    ranked = sorted(points, key=lambda item: item[1], reverse=True)
    top_value = ranked[0][1]
    tied = [unit for unit, value in ranked if value == top_value]
    if len(tied) > 1:
        names = ", ".join(public_name(unit) for unit in tied)
        return f"Empate em {label} entre {names}. {engine}"
    low = ranked[-1]
    delta = top_value - low[1]
    return (
        f"{public_name(ranked[0][0])} ficou acima de {public_name(low[0])} em {label} "
        f"(diferença observada {_format_observed_delta(label, delta)}, "
        f"não é economia comprovada). {engine}"
    )


def _format_observed_delta(label: str, value: float) -> str:
    if label in {"faturamento", "ticket"}:
        return _brl(value)
    if label == "litros":
        return _liters(value)
    if value == int(value):
        return _qty(int(value))
    return _brl(value)


def _recommendation_for(interpreted: InterpretedQuestion, metrics: dict[int, UnitMetric]) -> str:
    disclaimer = "Sem causa, perda ou economia atribuída."
    if not metrics or not (interpreted.compare or interpreted.intent == QuestionIntent.COMPARE):
        return f"Conferir os números publicados no período. {disclaimer}"
    if len(metrics) < 2:
        return f"Conferir os números publicados no período. {disclaimer}"
    label, _ = _metric_point(interpreted.intent, next(iter(metrics.values())))
    points: list[tuple[int, float]] = []
    for unit, metric in metrics.items():
        _, value = _metric_point(interpreted.intent, metric)
        if value is None:
            return f"Conferir os números publicados no período. {disclaimer}"
        points.append((unit, value))
    low = min(points, key=lambda item: item[1])
    return f"{public_name(low[0])} teve o menor {label} no período. {disclaimer}"


class DisabledLlmNarrator:
    """Placeholder da IA real. Não chama rede."""

    def compose(self, *args: Any, **kwargs: Any) -> NarrativeDraft:
        raise RuntimeError("LLM executivo não autorizado nesta Frente B")


def narrative_payload(
    interpreted: InterpretedQuestion,
    metrics: dict[int, UnitMetric] | None,
    *,
    start: str,
    end: str,
) -> dict[str, Any]:
    """Somente agregados. Sem linhas SDS, tokens ou caminhos."""
    series: list[dict[str, Any]] = []
    for unit, metric in (metrics or {}).items():
        series.append(
            {
                "unidade": unit,
                "litros": metric.litros,
                "faturamento": metric.faturamento,
                "ticketReais": metric.ticket_reais,
                "abastecimentos": metric.quantidade,
                "contagemConfiavel": metric.contagem_confiavel,
            }
        )
    return {
        "intencao": interpreted.intent.value,
        "especialista": interpreted.specialist,
        "inicio": start,
        "fim": end,
        "comparar": interpreted.compare,
        "series": series,
        "regra": "Redigir prosa. Não inventar números, lucro, CMV ou unidades.",
    }


class InjectableLlmNarrator:
    """IA só redige. Fatos e números vêm do narrador determinístico. Sem rede implícita."""

    def __init__(
        self,
        *,
        complete: Any | None = None,
        enabled: bool = False,
        fallback: DeterministicNarrator | None = None,
    ) -> None:
        self._complete = complete
        self._enabled = enabled
        self._fallback = fallback or DeterministicNarrator()

    def compose(
        self,
        interpreted: InterpretedQuestion,
        metrics: dict[int, UnitMetric] | None,
        *,
        start: str,
        end: str,
    ) -> NarrativeDraft:
        base = self._fallback.compose(interpreted, metrics, start=start, end=end)
        if not self._enabled or self._complete is None:
            return base
        payload = narrative_payload(interpreted, metrics, start=start, end=end)
        try:
            prose = str(self._complete(payload) or "").strip()
        except Exception:
            return base
        if not prose:
            return base
        return NarrativeDraft(
            fact=base.fact,
            inference=base.inference,
            recommendation=base.recommendation,
            answer=prose,
            engine="llm",
            llm=True,
        )
