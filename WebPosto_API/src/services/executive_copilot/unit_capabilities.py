"""Matriz canônica UnitCapabilities do Copiloto. Sem I/O e sem rede."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from src.core.config import OFFICIAL_COMPANY_CODES
from src.utils.filial_normalizer import EMPRESA_VIP_LEGACY_ALIAS

VIP_ALIAS = EMPRESA_VIP_LEGACY_ALIAS
UNIT_SOURCE_NOT_APPLICABLE = "UNIT_SOURCE_NOT_APPLICABLE"
UNIT_SOURCE_NOT_APPLICABLE_MESSAGE = (
    "Esta fonte de combustível não se aplica à Conveniência 24 Horas."
)
UNIT_NAME_AMBIGUOUS = "UNIT_NAME_AMBIGUOUS"
UNIT_REQUIRED_FOR_ACTION = "UNIT_REQUIRED_FOR_ACTION"
ACTION_NETWORK_SCOPE_FORBIDDEN = "ACTION_NETWORK_SCOPE_FORBIDDEN"
MANAGER_NETWORK_SCOPE_FORBIDDEN = "MANAGER_NETWORK_SCOPE_FORBIDDEN"

PISTA_CAPABILITIES = frozenset(
    {
        "FATURAMENTO_PISTA",
        "LITROS",
        "ABASTECIMENTOS",
        "TICKET",
        "BICOS",
        "BOMBAS",
        "TANQUES",
        "LMC",
        "DRAFT_PRODUCT",
        "DRAFT_EXPENSE",
        "AUDIT_TASK",
    }
)
LOJA_CAPABILITIES = frozenset(
    {
        "PRODUTOS_LOJA",
        "VENDAS_LOJA",
        "ESTOQUE_LOJA",
        "COMPRAS",
        "DESPESAS",
        "DRAFT_PRODUCT",
        "DRAFT_EXPENSE",
        "RECLASSIFY",
        "AUDIT_TASK",
    }
)
FUEL_CAPABILITIES = frozenset(
    {
        "FATURAMENTO_PISTA",
        "LITROS",
        "ABASTECIMENTOS",
        "TICKET",
        "BICOS",
        "BOMBAS",
        "TANQUES",
        "LMC",
    }
)
FUEL_SOURCES = frozenset({"SDS_ABASTECIMENTO", "CHECKPOINT", "LMC"})

_TODAS = (
    "todas as unidades",
    "todas as filiais",
    "todas as lojas",
    "todas unidades",
    "todas filiais",
)


@dataclass(frozen=True)
class UnitCapability:
    code: int
    public_name: str
    aliases: tuple[str, ...]
    unit_type: str
    capabilities: frozenset[str]
    allowed_sources: frozenset[str]
    data_on_demand: bool
    draft_actions: bool


def _codes() -> tuple[int, int, int, int]:
    casa, vip, real, loja = OFFICIAL_COMPANY_CODES
    return int(casa), int(vip), int(real), int(loja)


CASA_CAIADA, POSTO_VIP, POSTO_REAL, CONVENIENCIA_24H = _codes()

UNIT_CAPABILITIES: tuple[UnitCapability, ...] = (
    UnitCapability(
        code=CASA_CAIADA,
        public_name="AP Casa Caiada",
        aliases=("AP Casa Caiada", "Casa Caiada", "AP Casa Caiada Olinda", "5555"),
        unit_type="PISTA",
        capabilities=PISTA_CAPABILITIES,
        allowed_sources=FUEL_SOURCES,
        data_on_demand=True,
        draft_actions=True,
    ),
    UnitCapability(
        code=POSTO_VIP,
        public_name="Posto VIP",
        aliases=("Posto VIP", "VIP", "Posto VIP Olinda", "11495", "6666"),
        unit_type="PISTA",
        capabilities=PISTA_CAPABILITIES,
        allowed_sources=FUEL_SOURCES,
        data_on_demand=True,
        draft_actions=True,
    ),
    UnitCapability(
        code=POSTO_REAL,
        public_name="Posto Real/Doze",
        aliases=("Posto Real/Doze", "Posto Real", "Posto Doze", "Real Doze", "Doze", "74014"),
        unit_type="PISTA",
        capabilities=PISTA_CAPABILITIES,
        allowed_sources=FUEL_SOURCES,
        data_on_demand=True,
        draft_actions=True,
    ),
    UnitCapability(
        code=CONVENIENCIA_24H,
        public_name="Conveniência 24 Horas",
        aliases=(
            "Conveniência 24 Horas",
            "Conveniencia 24 Horas",
            "Conveniência 24H",
            "Conveniencia 24H",
            "Loja 24 Horas",
            "Loja 24H",
            "118508",
        ),
        unit_type="LOJA",
        capabilities=LOJA_CAPABILITIES,
        allowed_sources=frozenset({"LOJA_LOCAL", "DESPESAS", "PRODUTOS_LOJA"}),
        data_on_demand=False,
        draft_actions=True,
    ),
)

COPILOT_UNIT_CODES: tuple[int, ...] = tuple(item.code for item in UNIT_CAPABILITIES)
PISTA_UNIT_CODES: tuple[int, ...] = tuple(item.code for item in UNIT_CAPABILITIES if item.unit_type == "PISTA")
_BY_CODE = {item.code: item for item in UNIT_CAPABILITIES}


def _fold(value: str) -> str:
    norm = unicodedata.normalize("NFD", str(value or ""))
    ascii_only = "".join(ch for ch in norm if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", ascii_only.casefold()).strip()


_ALIAS_INDEX: list[tuple[str, int]] = sorted(
    ((_fold(alias), item.code) for item in UNIT_CAPABILITIES for alias in (item.public_name, *item.aliases)),
    key=lambda pair: len(pair[0]),
    reverse=True,
)
_AMBIGUOUS_LOJA = frozenset({"loja", "a loja", "na loja"})


@dataclass(frozen=True)
class UnitSelection:
    codes: list[int]
    all_units: bool
    ambiguous: bool
    from_text: bool
    names: list[str]


def capability_for(code: int) -> UnitCapability | None:
    return _BY_CODE.get(int(code))


def public_name(code: int) -> str:
    item = capability_for(code)
    return item.public_name if item else f"Unidade {code}"


def public_names(codes: list[int] | tuple[int, ...]) -> list[str]:
    return [public_name(code) for code in codes]


def is_copilot_unit(code: int) -> bool:
    return int(code) in _BY_CODE


def is_pista(code: int) -> bool:
    item = capability_for(code)
    return bool(item and item.unit_type == "PISTA")


def supports_data_on_demand(code: int) -> bool:
    item = capability_for(code)
    return bool(item and item.data_on_demand)


def supports_capability(code: int, capability: str) -> bool:
    item = capability_for(code)
    return bool(item and capability in item.capabilities)


def source_for_intent(intent: str) -> str:
    mapping = {
        "SALES": "FATURAMENTO_PISTA",
        "LITERS": "LITROS",
        "ABASTECIMENTOS": "ABASTECIMENTOS",
        "VOLUME_COUNT": "ABASTECIMENTOS",
        "TICKET": "TICKET",
        "COMPARE": "FATURAMENTO_PISTA",
        "PROFIT": "FATURAMENTO_PISTA",
        "CASH": "FATURAMENTO_PISTA",
        "ECONOMY": "FATURAMENTO_PISTA",
        "EXPENSE": "DESPESAS",
        "CREATE_PRODUCT_DRAFT": "DRAFT_PRODUCT",
        "CREATE_EXPENSE_DRAFT": "DRAFT_EXPENSE",
        "RECLASSIFY_EXPENSE_DRAFT": "RECLASSIFY",
        "CREATE_AUDIT_TASK": "AUDIT_TASK",
        "CONFIRM_ACTION": "DRAFT_EXPENSE",
    }
    return mapping.get(str(intent), "FATURAMENTO_PISTA")


def is_fuel_capability(capability: str) -> bool:
    return capability in FUEL_CAPABILITIES


def compatible_units(codes: list[int], capability: str) -> list[int]:
    return [code for code in codes if supports_capability(code, capability)]


def dod_units(codes: list[int]) -> list[int]:
    return [code for code in codes if supports_data_on_demand(code)]


def mentions_all_units(question: str) -> bool:
    blob = _fold(question)
    return any(token in blob for token in _TODAS)


def _ambiguous_loja(question: str) -> bool:
    blob = f" {_fold(question)} "
    if "24h" in blob.replace(" ", "") or "24 horas" in blob:
        return False
    return bool(re.search(r"(?<![a-z0-9])loja(?![a-z0-9])", blob)) and "conveniencia" not in blob


def codes_from_text(question: str) -> UnitSelection:
    """Resolve nomes/aliases no texto. 6666 vira VIP e nunca é devolvido."""
    raw = str(question or "")
    blob = _fold(raw)
    if _ambiguous_loja(raw):
        remaining = blob
        for alias, _code in _ALIAS_INDEX:
            if alias and alias in remaining:
                remaining = remaining.replace(alias, " ")
        if _fold(remaining) and re.search(r"(?<![a-z0-9])loja(?![a-z0-9])", f" {remaining} "):
            return UnitSelection(codes=[], all_units=False, ambiguous=True, from_text=True, names=[])
    found: list[int] = []
    remaining = blob
    for alias, code in _ALIAS_INDEX:
        if not alias or alias not in remaining:
            continue
        if code not in found:
            found.append(code)
        remaining = remaining.replace(alias, " ")
    if VIP_ALIAS in found:
        found = [POSTO_VIP if code == VIP_ALIAS else code for code in found]
        found = [code for code in found if code != VIP_ALIAS]
    return UnitSelection(
        codes=found,
        all_units=mentions_all_units(raw),
        ambiguous=False,
        from_text=bool(found),
        names=public_names(found),
    )


def select_requested_units(question: str, requested: list[int] | None) -> UnitSelection:
    """Nomes do texto têm prioridade sobre o filtro numérico."""
    from_text = codes_from_text(question)
    if from_text.ambiguous:
        return from_text
    if from_text.all_units and not from_text.codes:
        return UnitSelection(codes=[], all_units=True, ambiguous=False, from_text=True, names=[])
    if from_text.codes:
        return from_text
    codes: list[int] = []
    for raw in requested or []:
        try:
            code = int(raw)
        except (TypeError, ValueError):
            continue
        if code == VIP_ALIAS:
            code = POSTO_VIP
        if is_copilot_unit(code) and code not in codes:
            codes.append(code)
    return UnitSelection(
        codes=codes,
        all_units=False,
        ambiguous=False,
        from_text=False,
        names=public_names(codes),
    )


def user_role(user: dict[str, Any] | None) -> str:
    if not isinstance(user, dict):
        return ""
    return str(user.get("role") or "").strip().lower()
