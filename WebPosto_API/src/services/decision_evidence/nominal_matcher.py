"""DIR-01 — matching nominal financeiro → CAIXA / valeFun turno."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

MATCH_EXACT = "EXACT"
MATCH_PROBABLE = "PROBABLE"
MATCH_AMBIGUOUS = "AMBIGUOUS"
MATCH_NO_MATCH = "NO_MATCH"

CONFIDENCE_BY_STATUS = {
    MATCH_EXACT: 100.0,
    MATCH_PROBABLE: 70.0,
    MATCH_AMBIGUOUS: 40.0,
    MATCH_NO_MATCH: 0.0,
}

NOMINAL_SOURCE_CAIXA = "CAIXA+CAIXA_APRESENTADO"
NOMINAL_SOURCE_VALE_FUN = "CAIXA_APRESENTADO.valeFunApurado"
NOMINAL_SOURCE_FINANCEIRO = "DESPESAS_FINANCEIRO_REDE"
NOMINAL_SOURCE_PRESTACAO = "PRESTACAO_CONTAS"
FINANCIAL_NATURE_VALE = "VALE_FUNCIONARIO"

MATCH_STATUS_UI_LABELS = {
    MATCH_EXACT: "Identificado",
    MATCH_PROBABLE: "Provável",
    MATCH_AMBIGUOUS: "Ambíguo",
    MATCH_NO_MATCH: "Não identificado",
}


def match_status_ui_label(status: str | None) -> str:
    if not status:
        return "Não identificado"
    return MATCH_STATUS_UI_LABELS.get(status, "Não identificado")


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0")


def _norm_date(value: Any) -> str:
    return str(value or "")[:10]


def _date_near(left: str, right: str, days: int = 2) -> bool:
    try:
        a = datetime.fromisoformat(left[:10])
        b = datetime.fromisoformat(right[:10])
        return abs((a - b).days) <= days
    except ValueError:
        return left == right


def _optional_code(value: Any) -> int | None:
    if value in (None, "", 0):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _norm_empresa(value: Any) -> str | None:
    if value in (None, "", 0):
        return None
    return str(value).strip()


@dataclass
class NominalCandidate:
    empresa_codigo: Any
    data: str
    valor: Decimal
    funcionario_codigo: int | None = None
    caixa_codigo: Any = None
    turno: str | None = None
    source: str = NOMINAL_SOURCE_CAIXA
    source_reference: str | None = None
    description: str | None = None
    kind: str = "DESPESA_TURNO"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class NominalMatchResult:
    status: str
    confidence: float
    candidate: NominalCandidate | None = None
    candidates: list[NominalCandidate] = field(default_factory=list)
    reason: str = ""
    limitations: list[str] = field(default_factory=list)


def build_nominal_candidates_from_screen_rows(rows: list[dict[str, Any]]) -> list[NominalCandidate]:
    """Extrai candidatos nominais de linhas operacionais (CAIXA + CAIXA_APRESENTADO)."""
    candidates: list[NominalCandidate] = []
    for row in rows:
        if str(row.get("origem") or "").casefold() == "financeiro":
            continue

        raw = row.get("raw") or {}
        empresa = row.get("empresaCodigo") or raw.get("empresaCodigo")
        data = _norm_date(row.get("data") or raw.get("dataMovimento") or raw.get("fechamento"))
        if not data or empresa is None:
            continue

        funcionario = _optional_code(row.get("funcionarioCodigo") or raw.get("funcionarioCodigo"))
        caixa = row.get("caixaCodigo") or raw.get("caixaCodigo") or raw.get("ap_caixaCodigo")
        turno = row.get("turno") or row.get("turnoCodigo") or raw.get("turno") or raw.get("turnoCodigo")
        base = {
            "empresa_codigo": empresa,
            "data": data,
            "funcionario_codigo": funcionario,
            "caixa_codigo": caixa,
            "turno": str(turno) if turno not in (None, "") else None,
            "description": row.get("descricao") or row.get("planoConta"),
            "raw": raw,
        }

        despesa_val = _money(row.get("valor") or row.get("despesaApurado"))
        if despesa_val > 0:
            candidates.append(
                NominalCandidate(
                    **base,
                    valor=despesa_val,
                    source=NOMINAL_SOURCE_CAIXA,
                    source_reference=f"caixaCodigo={caixa};turno={turno}",
                    kind="DESPESA_TURNO",
                )
            )

        vale_fun = raw.get("ap_valeFunApurado") or raw.get("valeFunApurado")
        vale_val = _money(vale_fun)
        if vale_val > 0:
            candidates.append(
                NominalCandidate(
                    **base,
                    valor=vale_val,
                    source=NOMINAL_SOURCE_VALE_FUN,
                    source_reference=f"caixaCodigo={caixa};valeFunApurado={vale_val};turno={turno}",
                    kind="VALE_FUN_TURNO",
                )
            )

    return candidates


class NominalMatcher:
    """Match reverso: lançamento financeiro → candidato operacional nominal."""

    def __init__(self, candidates: list[NominalCandidate]) -> None:
        self._candidates = candidates
        self._used: set[int] = set()

    def match_financial_row(
        self,
        *,
        empresa_codigo: Any,
        data: str | None,
        valor: float | Decimal,
        category: str | None = None,
        description: str | None = None,
    ) -> NominalMatchResult:
        dt = _norm_date(data)
        val = _money(valor)
        if not dt or val <= 0 or empresa_codigo is None:
            return NominalMatchResult(
                status=MATCH_NO_MATCH,
                confidence=0.0,
                reason="Dados financeiros insuficientes para matching nominal.",
                limitations=["empresa, data ou valor ausente no lançamento financeiro."],
            )

        exact = self._find_available(
            empresa_codigo=empresa_codigo,
            data=dt,
            valor=val,
            date_tolerance_days=0,
        )
        if len(exact) == 1:
            return self._finalize_single(exact[0], MATCH_EXACT, "Match exato por empresa+data+valor.")
        if len(exact) > 1:
            return self._finalize_ambiguous(exact, "Múltiplos turnos/caixas com mesmo valor na mesma data.")

        probable = self._find_available(
            empresa_codigo=empresa_codigo,
            data=dt,
            valor=val,
            date_tolerance_days=2,
        )
        if len(probable) == 1:
            cand = probable[0]
            return self._finalize_single(
                cand,
                MATCH_PROBABLE,
                f"Match provável: valor igual em turno próximo ({cand.data} vs {dt}).",
            )
        if len(probable) > 1:
            return self._finalize_ambiguous(
                probable,
                "Múltiplos turnos candidatos com mesmo valor em datas próximas — beneficiário não inferido.",
            )

        limitations = [
            "Nenhum turno CAIXA/CAIXA_APRESENTADO com valeFunApurado ou despesaApurado "
            f"correspondente a R$ {val} em {dt}.",
        ]
        if category and "vale" in category.casefold():
            limitations.append(
                "Vales consolidados em DESPESAS_FINANCEIRO_REDE não trazem funcionário; "
                "VALE_FUNCIONARIO_REDE (401) indisponível no token atual."
            )
        return NominalMatchResult(
            status=MATCH_NO_MATCH,
            confidence=0.0,
            reason="Sem candidato nominal operacional para este lançamento.",
            limitations=limitations,
        )

    def _find_available(
        self,
        *,
        empresa_codigo: Any,
        data: str,
        valor: Decimal,
        date_tolerance_days: int,
    ) -> list[NominalCandidate]:
        found: list[NominalCandidate] = []
        target_empresa = _norm_empresa(empresa_codigo)
        for idx, cand in enumerate(self._candidates):
            if idx in self._used:
                continue
            if _norm_empresa(cand.empresa_codigo) != target_empresa or cand.valor != valor:
                continue
            if date_tolerance_days == 0:
                if cand.data != data:
                    continue
            elif not _date_near(data, cand.data, date_tolerance_days):
                continue
            found.append(cand)
        return found

    def _finalize_single(
        self,
        candidate: NominalCandidate,
        status: str,
        reason: str,
    ) -> NominalMatchResult:
        idx = self._candidates.index(candidate)
        self._used.add(idx)
        limitations: list[str] = []
        if status == MATCH_PROBABLE:
            limitations.append("Data do turno operacional difere da data do lançamento financeiro consolidado.")
        if candidate.kind == "VALE_FUN_TURNO":
            limitations.append(
                "Beneficiário inferido via total valeFunApurado do turno — não é vale nominal linha a linha."
            )
        if candidate.funcionario_codigo is None:
            limitations.append("Turno identificado sem funcionarioCodigo na API CAIXA.")
        return NominalMatchResult(
            status=status,
            confidence=CONFIDENCE_BY_STATUS[status],
            candidate=candidate,
            reason=reason,
            limitations=limitations,
        )

    def _finalize_ambiguous(
        self,
        candidates: list[NominalCandidate],
        reason: str,
    ) -> NominalMatchResult:
        codes = {c.funcionario_codigo for c in candidates if c.funcionario_codigo is not None}
        limitations = [
            f"{len(candidates)} candidatos operacionais com mesmo valor — beneficiário não escolhido automaticamente.",
        ]
        if len(codes) > 1:
            limitations.append("Candidatos apontam funcionários distintos.")
        return NominalMatchResult(
            status=MATCH_AMBIGUOUS,
            confidence=CONFIDENCE_BY_STATUS[MATCH_AMBIGUOUS],
            candidates=candidates,
            reason=reason,
            limitations=limitations,
        )


@dataclass
class PrestacaoNominalCandidate:
    empresa_codigo: str
    valor: Decimal
    person_name: str | None
    funcionario_codigo: int | None = None
    source_file: str | None = None
    page_number: int | None = None
    line_reference: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    raw_text: str | None = None
    index: int = 0


def build_prestacao_candidates(items: list[Any]) -> list[PrestacaoNominalCandidate]:
    """Converte NominalEvidenceItem (Prestação) em candidatos de match."""
    candidates: list[PrestacaoNominalCandidate] = []
    for idx, item in enumerate(items):
        empresa = _norm_empresa(getattr(item, "empresa_codigo", None) or getattr(item, "tenant_id", None))
        if not empresa:
            continue
        val = _money(getattr(item, "amount", 0))
        if val <= 0:
            continue
        candidates.append(
            PrestacaoNominalCandidate(
                empresa_codigo=empresa,
                valor=val,
                person_name=getattr(item, "person_name", None),
                funcionario_codigo=_optional_code(getattr(item, "funcionario_codigo", None)),
                source_file=getattr(item, "source_file", None),
                page_number=getattr(item, "page_number", None),
                line_reference=getattr(item, "line_reference", None),
                period_start=getattr(item, "period_start", None),
                period_end=getattr(item, "period_end", None),
                raw_text=getattr(item, "raw_text", None),
                index=idx,
            )
        )
    return candidates


class PrestacaoNominalMatcher:
    """Match financeiro → linha nominal da Prestação (fonte complementar, agregado mensal)."""

    def __init__(
        self,
        candidates: list[PrestacaoNominalCandidate],
        *,
        no_match_amount_counts: dict[Decimal, int] | None = None,
    ) -> None:
        self._candidates = candidates
        self._no_match_amount_counts = no_match_amount_counts or {}
        self._used: set[int] = set()

    def match_financial_row(
        self,
        *,
        empresa_codigo: Any,
        data: str | None,
        valor: float | Decimal,
        category: str | None = None,
    ) -> NominalMatchResult:
        target_empresa = _norm_empresa(empresa_codigo)
        val = _money(valor)
        if not target_empresa or val <= 0:
            return NominalMatchResult(
                status=MATCH_NO_MATCH,
                confidence=0.0,
                reason="Dados insuficientes para match com Prestação.",
            )

        if category and "vale" not in category.casefold():
            return NominalMatchResult(
                status=MATCH_NO_MATCH,
                confidence=0.0,
                reason="Natureza financeira incompatível com vales da Prestação.",
            )

        pool = [
            c
            for c in self._candidates
            if c.index not in self._used
            and c.empresa_codigo == target_empresa
            and c.valor == val
        ]
        if not pool:
            return NominalMatchResult(
                status=MATCH_NO_MATCH,
                confidence=0.0,
                reason="Nenhuma linha nominal da Prestação com valor absoluto correspondente.",
                limitations=[
                    "Prestação disponível traz totais mensais por funcionário — "
                    f"sem linha nominal de R$ {val}."
                ],
            )

        same_financial = self._no_match_amount_counts.get(val, 0)
        if len(pool) > 1 or same_financial > 1:
            limitations = [
                "Mais de um beneficiário possível — requer conferência manual.",
                "Prestação de Contas agrega vales por funcionário no mês — "
                "não permite atribuição linha a linha sem ambiguidade.",
            ]
            if len(pool) > 1:
                limitations.append(f"{len(pool)} funcionários com vale mensal de R$ {val}.")
            if same_financial > 1:
                limitations.append(
                    f"{same_financial} lançamentos financeiros de R$ {val} aguardando identificação."
                )
            return NominalMatchResult(
                status=MATCH_AMBIGUOUS,
                confidence=CONFIDENCE_BY_STATUS[MATCH_AMBIGUOUS],
                reason="Múltiplos vínculos plausíveis entre lançamento financeiro e Prestação.",
                limitations=limitations,
            )

        cand = pool[0]
        self._used.add(cand.index)
        dt = _norm_date(data)
        date_note = ""
        if dt and cand.period_start and cand.period_end:
            if not (cand.period_start <= dt <= cand.period_end):
                date_note = " Data do lançamento fora do período da Prestação."

        limitations = [
            "Beneficiário inferido via total mensal de vale na Prestação — "
            "não confirma recebimento bancário nem encerra conferência.",
            "Prestação de Contas é fonte nominal complementar, não prova financeira externa.",
        ]
        if date_note:
            limitations.append(date_note.strip())

        pseudo = NominalCandidate(
            empresa_codigo=cand.empresa_codigo,
            data=dt or cand.period_end or "",
            valor=cand.valor,
            funcionario_codigo=cand.funcionario_codigo,
            source=NOMINAL_SOURCE_PRESTACAO,
            source_reference=cand.line_reference or cand.source_file,
            description=cand.person_name,
            kind="VALE_PRESTACAO_MENSAL",
            raw={"person_name": cand.person_name, "source_file": cand.source_file},
        )
        return NominalMatchResult(
            status=MATCH_PROBABLE,
            confidence=CONFIDENCE_BY_STATUS[MATCH_PROBABLE],
            candidate=pseudo,
            reason=(
                f"Match provável via Prestação: vale mensal R$ {val} "
                f"para {cand.person_name or 'funcionário não nomeado'}."
            ),
            limitations=limitations,
        )


def resolve_employee_name(
    funcionario_codigo: int | None,
    employee_index: dict[int, dict[str, Any]],
) -> str | None:
    if funcionario_codigo is None:
        return None
    row = employee_index.get(int(funcionario_codigo)) or {}
    name = row.get("employeeName") or row.get("nome")
    if name:
        return str(name)
    return None
