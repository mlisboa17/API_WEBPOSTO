from __future__ import annotations

from datetime import date
from typing import Any, Dict


async def get_executive_metrics(db: Any, cache: Any, current_user: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback simples para rota /metrics/executive enquanto o módulo completo não existe."""
    role = str(current_user.get("role") or current_user.get("perfil") or "guest")
    return {
        "ok": True,
        "engine": "fallback",
        "periodo": date.today().isoformat(),
        "role": role,
        "message": "Executive metrics fallback payload",
    }
