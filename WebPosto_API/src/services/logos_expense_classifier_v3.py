"""Classificador LOGOS V3 — hierarquia Plano de Contas + Centro de Custo (F01.4-A)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.services.logos_expense_classifier_v2 import (
    VALID_V2_CATEGORIES,
    classify_logos_expense_v2,
    map_v2_to_legacy,
)

MAPPING_PATH = Path(__file__).resolve().parents[2] / "config" / "account_category_mapping.json"

VALID_V3_CATEGORIES = VALID_V2_CATEGORIES
CLASSIFICATION_SOURCES = frozenset(
    {"PLANO_CONTA", "CENTRO_CUSTO", "FORNECEDOR", "DESCRICAO", "HIBRIDO", "MANUAL", "OUTROS"}
)

WEIGHT_PLANO = 0.60
WEIGHT_CENTRO = 0.25
WEIGHT_DESC = 0.15


@dataclass(frozen=True)
class ClassificationResultV3:
    categoria_v3: str
    confidence_score: float
    classification_source: str
    matched_rule: str | None
    categoria_v2: str
    categoria_legacy: str


@lru_cache(maxsize=1)
def _load_plano_map() -> dict[int, dict[str, Any]]:
    if not MAPPING_PATH.exists():
        return {}
    doc = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    out: dict[int, dict[str, Any]] = {}
    for item in doc.get("mappings") or []:
        code = item.get("codigoGerencial") or item.get("planoContaId")
        if code is not None:
            out[int(code)] = item
    return out


def _clamp_conf(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def classify_logos_expense_v3(
    descricao: str = "",
    plano_conta: str = "",
    fornecedor: str = "",
    centro_custo: str = "",
    historico: str = "",
    plano_conta_gerencial_codigo: int | str | None = None,
    centro_custo_codigo: int | str | None = None,
) -> ClassificationResultV3:
    """Hierarquia: Plano Conta → Centro Custo → Fornecedor → Descrição → OUTROS."""
    plano_map = _load_plano_map()
    candidates: list[tuple[str, str, float, str | None]] = []

    if plano_conta_gerencial_codigo is not None:
        try:
            code = int(plano_conta_gerencial_codigo)
            entry = plano_map.get(code)
            if entry and entry.get("categoriaLogosV3") and entry["categoriaLogosV3"] != "OUTROS":
                conf = float(entry.get("confidenceScore") or 0.85)
                src = str(entry.get("classificationSource") or "PLANO_CONTA")
                if src not in CLASSIFICATION_SOURCES:
                    src = "PLANO_CONTA"
                candidates.append(
                    (entry["categoriaLogosV3"], src, _clamp_conf(conf * WEIGHT_PLANO / 0.6), entry.get("descricaoGerencial"))
                )
        except (TypeError, ValueError):
            pass

    if centro_custo or centro_custo_codigo:
        cc_blob = f"{centro_custo}".strip()
        cc_v2 = classify_logos_expense_v2(cc_blob)
        if cc_v2.categoria_v2 != "OUTROS":
            candidates.append(
                (cc_v2.categoria_v2, "CENTRO_CUSTO", _clamp_conf(cc_v2.confidence_score / 100 * WEIGHT_CENTRO), cc_blob[:60])
            )

    if fornecedor:
        f_v2 = classify_logos_expense_v2(fornecedor)
        if f_v2.categoria_v2 != "OUTROS":
            candidates.append(
                (f_v2.categoria_v2, "FORNECEDOR", _clamp_conf(f_v2.confidence_score / 100 * 0.12), fornecedor[:60])
            )

    desc_v2 = classify_logos_expense_v2(descricao, plano_conta, fornecedor, centro_custo, historico)
    if desc_v2.categoria_v2 != "OUTROS":
        candidates.append(
            (desc_v2.categoria_v2, "DESCRICAO", _clamp_conf(desc_v2.confidence_score / 100 * WEIGHT_DESC), desc_v2.matched_rule)
        )

    if not candidates:
        return ClassificationResultV3(
            "OUTROS", 0.0, "OUTROS", None, "OUTROS", "OUTROS"
        )

    if len(candidates) > 1:
        best = max(candidates, key=lambda x: x[2])
        cat, src, conf, rule = best
        if any(c[0] != cat for c in candidates):
            src = "HIBRIDO"
            conf = _clamp_conf(conf * 0.95)
    else:
        cat, src, conf, rule = candidates[0]

    return ClassificationResultV3(
        categoria_v3=cat,
        confidence_score=conf,
        classification_source=src,
        matched_rule=rule,
        categoria_v2=cat,
        categoria_legacy=map_v2_to_legacy(cat),
    )


def classify_with_all_versions(
    descricao: str = "",
    plano_conta: str = "",
    fornecedor: str = "",
    centro_custo: str = "",
    historico: str = "",
    plano_conta_gerencial_codigo: int | str | None = None,
    centro_custo_codigo: int | str | None = None,
) -> dict[str, Any]:
    v2 = classify_logos_expense_v2(descricao, plano_conta, fornecedor, centro_custo, historico)
    v3 = classify_logos_expense_v3(
        descricao, plano_conta, fornecedor, centro_custo, historico,
        plano_conta_gerencial_codigo, centro_custo_codigo,
    )
    return {
        "categoriaLogos": v3.categoria_legacy,
        "categoriaLogosV2": v3.categoria_v2,
        "categoriaLogosV3": v3.categoria_v3,
        "confidenceScore": v2.confidence_score,
        "confidenceScoreV3": v3.confidence_score,
        "confidenceBand": "automatico" if v3.confidence_score >= 0.95 else "alta" if v3.confidence_score >= 0.80 else "revisao" if v3.confidence_score >= 0.60 else "outros",
        "classificationSource": v3.classification_source,
        "matchedRule": v3.matched_rule,
    }
