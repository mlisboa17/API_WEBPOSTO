"""Classificador de despesas LOGOS V2 — taxonomia expandida + confidence score (F01.3)."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "expense_classification_rules.json"

V2_CATEGORIES = (
    "OPERACIONAL",
    "PESSOAL",
    "ENERGIA",
    "MANUTENÇÃO",
    "FINANCEIRO",
    "TRIBUTÁRIO",
    "MARKETING",
    "COMPRAS",
    "TECNOLOGIA",
    "FRETES",
    "VEÍCULOS",
    "SERVIÇOS",
    "ALUGUÉIS",
    "SEGUROS",
    "OUTROS",
)

VALID_V2_CATEGORIES = frozenset(V2_CATEGORIES)


@dataclass(frozen=True)
class ClassificationResult:
    categoria_v2: str
    confidence_score: int
    matched_rule: str | None
    matched_field: str | None


def _norm(text: Any) -> str:
    if text is None:
        return ""
    s = str(text).strip().casefold()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    for ch in ".,;:/\\-|()[]":
        s = s.replace(ch, " ")
    return " ".join(s.split())


@lru_cache(maxsize=1)
def _load_rules() -> dict[str, Any]:
    if not RULES_PATH.exists():
        return {"rules": {}, "legacyMapping": {}}
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def _confidence_band(score: int) -> str:
    if score >= 95:
        return "automatico"
    if score >= 80:
        return "alta"
    if score >= 60:
        return "revisao"
    return "outros"


def classify_logos_expense_v2(
    descricao: str = "",
    plano_conta: str = "",
    fornecedor: str = "",
    centro_custo: str = "",
    historico: str = "",
) -> ClassificationResult:
    """Classifica despesa com taxonomia V2 e confidence score baseado em regras evidenciadas."""
    blob = _norm(" ".join([descricao, plano_conta, fornecedor, centro_custo, historico]))
    if not blob.strip():
        return ClassificationResult("OUTROS", 0, None, None)

    rules_doc = _load_rules()
    rules: dict[str, Any] = rules_doc.get("rules") or {}

    best_cat = "OUTROS"
    best_score = 0
    best_rule: str | None = None
    best_field: str | None = None

    for category, spec in rules.items():
        base_conf = int(spec.get("confidence") or 80)
        for supplier in spec.get("suppliers") or []:
            sup = _norm(supplier)
            if not sup:
                continue
            matched_sup = sup in blob if len(sup) > 3 else bool(
                re.search(rf"(?<![a-z0-9]){re.escape(sup)}(?![a-z0-9])", blob)
            )
            if matched_sup:
                score = min(100, base_conf + 2)
                if score > best_score:
                    best_score, best_cat, best_rule, best_field = score, category, supplier, "supplier"
        for keyword in spec.get("keywords") or []:
            kw = _norm(keyword)
            if not kw:
                continue
            matched = kw in blob
            if len(kw) <= 3:
                matched = bool(re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", blob))
            elif not matched:
                matched = bool(re.search(rf"\b{re.escape(kw)}\b", blob))
            if matched:
                score = base_conf
                if score > best_score:
                    best_score, best_cat, best_rule, best_field = score, category, keyword, "keyword"

    if best_score < 60:
        return ClassificationResult("OUTROS", best_score, best_rule, best_field)

    return ClassificationResult(best_cat, best_score, best_rule, best_field)


def map_v2_to_legacy(categoria_v2: str) -> str:
    rules_doc = _load_rules()
    mapping: dict[str, str] = rules_doc.get("legacyMapping") or {}
    return mapping.get(categoria_v2, mapping.get("OUTROS", "OUTROS"))


def classify_with_legacy(
    descricao: str = "",
    plano_conta: str = "",
    fornecedor: str = "",
    centro_custo: str = "",
    historico: str = "",
) -> dict[str, Any]:
    """Retorna V2 + legacy categoriaLogos + metadados de confiança."""
    result = classify_logos_expense_v2(descricao, plano_conta, fornecedor, centro_custo, historico)
    legacy = map_v2_to_legacy(result.categoria_v2)
    return {
        "categoriaLogos": legacy,
        "categoriaLogosV2": result.categoria_v2,
        "confidenceScore": result.confidence_score,
        "confidenceBand": _confidence_band(result.confidence_score),
        "matchedRule": result.matched_rule,
        "matchedField": result.matched_field,
    }
