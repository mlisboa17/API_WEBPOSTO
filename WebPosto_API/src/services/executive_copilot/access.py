"""Autorização de unidades do Copiloto. Sem rede."""

from __future__ import annotations

from typing import Any

from src.services.executive_copilot.source_registry import UnitResolution, resolve_executive_units
from src.services.executive_copilot.unit_capabilities import COPILOT_UNIT_CODES

NETWORK_ROLES = frozenset({"director", "admin", "owner"})
_SCOPE_KEYS = ("units", "empresas", "company_codes")


def _parse_code_list(raw: Any) -> tuple[list[int] | None, dict[str, str] | None]:
    if raw in (None, ""):
        return None, {"code": "UNIT_SCOPE_EMPTY", "message": "Escopo de unidades vazio no token."}
    if isinstance(raw, (str, int)):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return None, {"code": "UNIT_SCOPE_INVALID", "message": "Escopo de unidades inválido no token."}
    if len(raw) == 0:
        return None, {"code": "UNIT_SCOPE_EMPTY", "message": "Escopo de unidades vazio no token."}
    codes: list[int] = []
    for item in raw:
        try:
            codes.append(int(item))
        except (TypeError, ValueError):
            return None, {
                "code": "UNIT_SCOPE_INVALID",
                "message": "Escopo de unidades inválido no token.",
            }
    return codes, None


def _codes_from_user(user: dict[str, Any]) -> tuple[list[int] | None, dict[str, str] | None]:
    """None, None = campo ausente (rede só para papéis de rede). Erro nunca amplia acesso."""
    for key in _SCOPE_KEYS:
        if key in user:
            return _parse_code_list(user.get(key))
    company = user.get("company_id") if "company_id" in user else user.get("empresaCodigo")
    if "company_id" in user or "empresaCodigo" in user:
        if company in (None, ""):
            return None, {"code": "UNIT_SCOPE_EMPTY", "message": "Escopo de unidades vazio no token."}
        return _parse_code_list([company])
    return None, None


def user_accessible_units(user: dict[str, Any] | None) -> UnitResolution:
    """Unidades do token. Escopo inválido/vazio não vira rede."""
    if not isinstance(user, dict):
        return UnitResolution(
            units=[],
            persisted_units=[],
            blocked={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
        )
    role = str(user.get("role") or "").strip().lower()
    scoped, error = _codes_from_user(user)
    if error:
        return UnitResolution(units=[], persisted_units=[], blocked=error)
    if scoped is None:
        if role in NETWORK_ROLES:
            licensed = list(COPILOT_UNIT_CODES)
            return UnitResolution(units=licensed, persisted_units=list(licensed), blocked=None)
        return UnitResolution(
            units=[],
            persisted_units=[],
            blocked={"code": "UNIT_SCOPE_MISSING", "message": "Token sem unidades autorizadas."},
        )
    return resolve_executive_units(scoped)


def restrict_requested_units(
    requested: list[int] | None,
    user: dict[str, Any] | None,
) -> UnitResolution:
    """Interseção pedido ∩ autorização. Unidade não autorizada bloqueia."""
    allowed = user_accessible_units(user)
    if allowed.blocked:
        return allowed
    if not requested:
        return allowed
    resolved = resolve_executive_units(requested)
    if resolved.blocked:
        return resolved
    if any(code not in set(allowed.units) for code in resolved.units):
        return UnitResolution(
            units=[],
            persisted_units=[],
            blocked={
                "code": "UNIT_FORBIDDEN_FOR_USER",
                "message": "Unidade solicitada fora do escopo autorizado do usuário.",
            },
        )
    return resolved


def default_units_for_user(user: dict[str, Any] | None) -> list[int]:
    allowed = user_accessible_units(user)
    if allowed.blocked:
        return []
    return list(allowed.units)
