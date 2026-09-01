"""Autorização mínima e explícita para rotas gerenciais mutáveis."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException

from src.interfaces.http.dependencies import get_current_user


def require_roles(*allowed_roles: str) -> Callable[..., Any]:
    allowed = {role.strip().lower() for role in allowed_roles}

    async def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if not isinstance(current_user, dict):
            raise HTTPException(status_code=401, detail="Token inválido ou malformado")
        role = str(current_user.get("role") or "").strip().lower()
        if role not in allowed:
            raise HTTPException(status_code=403, detail="Perfil sem permissão para esta ação")
        return current_user

    return dependency
