from __future__ import annotations

from fastapi import APIRouter, Body, Query

from src.services.commercial_copilot_service import CommercialCopilotService
from src.services.commercial_copilot_snapshot_service import CommercialCopilotSnapshotService

router = APIRouter(prefix="/api/v1/commercial-copilot", tags=["Commercial Copilot F07.9"])

_service = CommercialCopilotService()
_snapshot = CommercialCopilotSnapshotService(_service)


@router.get("/cockpit")
async def commercial_copilot_cockpit(
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
        "commercialKnowledgeEngine": payload.get("commercialKnowledgeEngine"),
        "commercialReasoningEngine": payload.get("commercialReasoningEngine"),
        "commercialRecommendationEngine": payload.get("commercialRecommendationEngine"),
        "commercialActionCenterIntegration": payload.get("commercialActionCenterIntegration"),
        "commercialConversationLayer": payload.get("commercialConversationLayer"),
        "commercialGovernanceLayer": payload.get("commercialGovernanceLayer"),
        "fonte": payload.get("fonte"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def commercial_copilot_summary(
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
            "commercialGovernanceLayer": payload.get("commercialGovernanceLayer"),
            "dwLayer": payload.get("dwLayer"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/refresh")
async def commercial_copilot_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}


@router.post("/ask")
async def commercial_copilot_ask(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
    body: dict = Body(...),
) -> dict:
    pergunta = str(body.get("question") or body.get("pergunta") or "").strip()
    if not pergunta:
        return {"success": False, "error": "question obrigatória"}
    resp = await _service.ask(pergunta, dataInicial, dataFinal, empresaCodigo)
    if not resp.success:
        return {"success": False, "error": resp.error}
    return {"success": True, "data": resp.data}
