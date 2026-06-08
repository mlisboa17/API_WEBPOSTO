"""Classificador de despesas LOGOS SPACE — retrocompatível via V2 (F01.3)."""
from __future__ import annotations

from typing import Any

from src.services.logos_expense_classifier_v2 import (
    VALID_V2_CATEGORIES,
    classify_logos_expense_v2,
    classify_with_legacy,
    map_v2_to_legacy,
)

LOGOS_CATEGORIES = {
    "OPERACIONAL": (),
    "PESSOAL": (),
    "ADMINISTRATIVA": (),
    "COMERCIAL": (),
    "COMPRAS": (),
    "FINANCEIRO": (),
}

VALID_CATEGORIES = frozenset(LOGOS_CATEGORIES.keys()) | {"OUTROS"}

V1_BASELINE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "OPERACIONAL": (
        "energia", "luz", "coelba", "neoenergia", "agua", "água", "telefone", "internet",
        "limpeza", "material de limpeza", "almoço", "almoco", "uber", "diaria", "diária",
    ),
    "PESSOAL": (
        "salario", "salário", "folha", "pro labore", "pro-labore", "funcionario", "funcionário",
        "complemento salario", "adiantamento", "vale", "beneficio", "benefício",
    ),
    "ADMINISTRATIVA": (
        "contabil", "contábil", "juridic", "jurídic", "sistema", "consultoria", "software",
        "contador", "honorario", "honorário",
    ),
    "COMERCIAL": ("marketing", "publicidade", "comissao", "comissão", "propaganda", "brinde"),
    "COMPRAS": (
        "compra", "mercadoria", "produto", "parafuso", "cloro", "cadeado", "material",
        "combustivel", "combustível", "trr", "nota entrada",
    ),
    "FINANCEIRO": (
        "juros", "tarifa", "multa", "iof", "ted", "doc", "pix", "transferencia", "transferência",
        "taxa banc", "banco",
    ),
}


def classify_logos_expense_v1_baseline(descricao: str, plano_conta: str = "") -> str:
    """Baseline pré-F01.3 para métricas de reclassificação."""
    from src.services.logos_expense_classifier_v2 import _norm

    blob = _norm(f"{descricao} {plano_conta}")
    for category, keywords in V1_BASELINE_KEYWORDS.items():
        if any(kw in blob for kw in keywords):
            return category
    return "OUTROS"


def classify_logos_expense(descricao: str, plano_conta: str = "") -> str:
    """Mantém contrato V1 — delega para V2 e mapeia categoria legacy."""
    return map_v2_to_legacy(classify_logos_expense_v2(descricao, plano_conta).categoria_v2)


def classify_logos_expense_full(
    descricao: str = "",
    plano_conta: str = "",
    fornecedor: str = "",
    centro_custo: str = "",
    historico: str = "",
) -> dict[str, Any]:
    return classify_with_legacy(descricao, plano_conta, fornecedor, centro_custo, historico)
