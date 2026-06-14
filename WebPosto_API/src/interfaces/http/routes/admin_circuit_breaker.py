"""F08.0 — Admin circuit breaker reset e observabilidade."""
from __future__ import annotations

from fastapi import APIRouter, Body

from src.gateway.shared_client import get_webposto_client

router = APIRouter(prefix="/api/v1/admin/circuit-breaker", tags=["Admin Circuit Breaker F08.0"])

_client = get_webposto_client()


@router.get("/status")
async def circuit_breaker_status() -> dict:
    status = _client.get_circuit_status()
    return {"success": True, "data": status, "error": None}


@router.post("/reset")
async def circuit_breaker_reset(payload: dict = Body(default={"scope": "global"})) -> dict:
    scope = str(payload.get("scope") or "global")
    result = _client.reset_circuit(scope)
    ok = bool(result.get("reset"))
    return {
        "success": ok,
        "data": result,
        "error": None if ok else {"type": "INVALID_SCOPE", "message": result.get("error")},
    }
