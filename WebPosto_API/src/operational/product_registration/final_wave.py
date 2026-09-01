"""Classificacao e desempate da ONDA FINAL — risco assumido pelo proprietario."""

from __future__ import annotations

from typing import Any

from collections import Counter

from .duplicate_checker import (
    FALSE_POSITIVE,
    POSSIBLE_VARIANT,
    SAME_PRODUCT_NEW_GTIN,
    classify_duplicate,
    distinctive_tokens,
)
from .fiscal_resolver import ST_PROVEN

SAME_PRODUCT = "SAME_PRODUCT"
LEGITIMATE_VARIANT = "LEGITIMATE_VARIANT"
UNRESOLVED_DUPLICATE = "UNRESOLVED_DUPLICATE"


def classify_final_duplicate(
    candidate_description: str,
    existing_description: str,
    *,
    candidate_family: str | None = None,
    existing_family: str | None = None,
) -> tuple[str, str]:
    """Decide se o par e o mesmo produto, variante legitima ou irresoluvel.

    Diferenca comercial identificavel vira variante. Falta de medida ou de
    caracteristica essencial no cadastro existente impede confirmar.
    """
    label, reason = classify_duplicate(
        candidate_description,
        existing_description,
        candidate_family=candidate_family,
        existing_family=existing_family,
    )
    if label == SAME_PRODUCT_NEW_GTIN:
        extra_on_candidate = distinctive_tokens(candidate_description) - distinctive_tokens(
            existing_description
        )
        if extra_on_candidate:
            return LEGITIMATE_VARIANT, (
                "Candidato traz caracteristica comercial ausente no cadastro: "
                f"{', '.join(sorted(extra_on_candidate))}"
            )
        return SAME_PRODUCT, reason
    if label == FALSE_POSITIVE:
        return LEGITIMATE_VARIANT, reason
    if label == POSSIBLE_VARIANT and "não declarada" in reason:
        return UNRESOLVED_DUPLICATE, reason
    return LEGITIMATE_VARIANT, reason


def score_icms_row(
    row: Any,
    *,
    verified_references: set[str],
    expected_cst_entrada: str | None,
    expected_rate: float | None,
) -> tuple[int, str]:
    """Pontua uma linha da tabela ICMS. Campo vazio nao conta como zero."""
    score = 0
    if expected_cst_entrada and row.cst_entrada == expected_cst_entrada:
        score += 8
    if expected_rate is not None and row.icms_entrada == expected_rate:
        score += 4
    if row.csosn_entrada is not None and row.csosn_saida is not None:
        score += 2
    if row.fcp is not None:
        score += 1
    if row.referencia in verified_references:
        score += 16
    return score, str(row.referencia)


def pick_icms_row(
    rows: list[Any],
    *,
    verified_references: set[str],
    expected_cst_entrada: str | None = None,
    expected_rate: float | None = None,
) -> tuple[Any, str]:
    """Escolhe a linha de maior pontuacao; empate absoluto usa a menor referencia."""
    complete = [
        row
        for row in rows
        if row.csosn_entrada is not None and row.csosn_saida is not None and row.fcp is not None
    ]
    pool = complete or rows
    ranked = sorted(
        (
            (
                score_icms_row(
                    row,
                    verified_references=verified_references,
                    expected_cst_entrada=expected_cst_entrada,
                    expected_rate=expected_rate,
                ),
                row,
            )
            for row in pool
        ),
        key=lambda item: (-item[0][0], item[0][1]),
    )
    winner = ranked[0]
    tied = [item for item in ranked if item[0][0] == winner[0][0]]
    reason = "HIGHEST_SCORE"
    if len(tied) > 1:
        if any(item[1].referencia in verified_references for item in tied):
            winner = next(item for item in tied if item[1].referencia in verified_references)
            reason = "VERIFIED_PIPELINE_TIEBREAK"
        else:
            reason = "OWNER_ACCEPTED_DETERMINISTIC_TIEBREAK"
    return winner[1], reason


def majority_treatment(
    entries: list[dict[str, Any]],
) -> tuple[str | None, float | None, list[dict[str, Any]]]:
    """Maioria entre NF-e distintas. Empate de votos nao elege tratamento."""
    by_invoice: dict[str, dict[str, Any]] = {}
    for entry in entries:
        invoice = str(entry.get("nfe") or "")
        if invoice and invoice not in by_invoice:
            by_invoice[invoice] = entry
    votes: Counter[str] = Counter()
    rates: Counter[float] = Counter()
    for entry in by_invoice.values():
        classification = str(entry.get("classification") or "")
        if classification:
            votes[classification] += 1
        if entry.get("aliquotaEntrada") is not None:
            rates[round(float(entry["aliquotaEntrada"]), 4)] += 1
    if not votes:
        return None, None, []
    ranked = votes.most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None, None, [
            {"classification": name, "notas": count} for name, count in ranked
        ]
    winner = ranked[0][0]
    rate = rates.most_common(1)[0][0] if winner != ST_PROVEN and rates else None
    discarded = [
        {"classification": name, "notas": count}
        for name, count in ranked
        if name != winner
    ]
    return winner, rate, discarded
