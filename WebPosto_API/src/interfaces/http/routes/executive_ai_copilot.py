from __future__ import annotations

from fastapi import APIRouter, Body, Query

from src.services.executive_ai_copilot_service import ExecutiveAiCopilotService
from src.services.executive_ai_copilot_snapshot_service import ExecutiveAiCopilotSnapshotService

router = APIRouter(prefix="/api/v1/executive-copilot", tags=["Executive AI Copilot F05.3"])

_service = ExecutiveAiCopilotService()
_snapshot = ExecutiveAiCopilotSnapshotService(_service)


@router.get("/cockpit")
async def executive_copilot_cockpit(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None}
    return {
        "success": True,
        "data": payload.get("cockpit"),
        "executiveAnswers": payload.get("executiveAnswers"),
        "parecerFinal": payload.get("parecerFinal"),
        "qa": payload.get("qa"),
        "governanceRules": payload.get("governanceRules"),
        "conversationLayer": payload.get("conversationLayer"),
        "recommendationEngine": payload.get("recommendationEngine"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def executive_copilot_summary(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None}
    return {
        "success": True,
        "data": {
            "executiveAnswers": payload.get("executiveAnswers"),
            "qa": payload.get("qa"),
            "parecerFinal": payload.get("parecerFinal"),
            "executiveReasoningEngine": payload.get("executiveReasoningEngine"),
            "governanceLayer": payload.get("governanceLayer"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/refresh")
async def executive_copilot_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}


@router.post("/ask")
async def executive_copilot_ask(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
    body: dict = Body(...),
) -> dict:
    pergunta = str(body.get("pergunta") or body.get("question") or "").strip()
    if not pergunta:
        return {"success": False, "error": "pergunta obrigatória"}
    resp = await _service.ask(pergunta, dataInicial, dataFinal, empresaCodigo)
    if not resp.success:
        return {"success": False, "error": resp.error}
    return {"success": True, "data": resp.data}
