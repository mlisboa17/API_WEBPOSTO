from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.gateway.webposto_client import WebPostoClient
from src.services.director_financial_reconciliation_pipeline import DirectorFinancialReconciliationPipeline
from src.services.director_financial_reconciliation_snapshot_service import (
    DirectorFinancialReconciliationSnapshotService,
)
from src.services.complete_departmental_dre_service import CompleteDepartmentalDreService
from src.services.complete_departmental_dre_snapshot_service import (
    CompleteDepartmentalDreSnapshotService,
    summarize_dre_payload,
)
from src.services.fuel_sales_reconciliation_service import FuelSalesReconciliationService
from src.services.non_fuel_product_sales_service import NonFuelProductSalesService
from src.services.dre_homologation_service import DreHomologationService
from src.services.webposto.offline_mode import (
    WebPostoOfflineBlocked,
    annotate_offline_success,
    offline_unavailable_response,
    webposto_offline_mode,
)


router = APIRouter(prefix="/api/v1/finance/director-reconciliation", tags=["Director Financial Reconciliation"])
_pipeline = DirectorFinancialReconciliationPipeline(WebPostoClient())
_snapshot = DirectorFinancialReconciliationSnapshotService(_pipeline)
_complete_dre = CompleteDepartmentalDreService(
    _pipeline,
    FuelSalesReconciliationService(_pipeline._client),
    NonFuelProductSalesService(_pipeline._client),
)
_dre_homologation = DreHomologationService()
_complete_dre_snapshot = CompleteDepartmentalDreSnapshotService(_complete_dre)


class DepartmentReviewBody(BaseModel):
    factId: str
    department: str
    reviewer: str = Field(min_length=2)
    rationale: str = Field(min_length=3)
    applyToAccount: bool = False
    managementAccountCode: str | None = None
    category: str | None = None
    subcategory: str | None = None


class ExpenseClassificationBody(BaseModel):
    factId: str
    managementAccountCode: str
    department: str
    category: str = Field(min_length=2)
    subcategory: str = Field(min_length=2)
    reviewer: str = Field(min_length=2)
    rationale: str = Field(min_length=3)
    applyToSimilar: bool = False
    recipientName: str | None = None


class ExpenseClassificationBatchBody(BaseModel):
    items: list[ExpenseClassificationBody] = Field(min_length=1, max_length=500)


class SharedAllocationBody(BaseModel):
    managementAccountCode: str
    percentages: dict[str, int]
    reviewer: str = Field(min_length=2)
    rationale: str = Field(min_length=3)


class DreApprovalBody(BaseModel):
    reviewer: str = Field(min_length=2)
    rationale: str = Field(min_length=3)


@router.get("")
async def get_director_financial_reconciliation(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: int | None = Query(None),
) -> dict:
    try:
        data, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    except WebPostoOfflineBlocked:
        return offline_unavailable_response(route="/api/v1/finance/director-reconciliation")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    body = {"success": True, "data": data, "snapshot": {"hit": hit, "stale": stale}}
    if webposto_offline_mode():
        return annotate_offline_success(body, source="snapshot")
    return body


@router.post("/refresh")
async def refresh_director_financial_reconciliation(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: int | None = Query(None),
) -> dict:
    try:
        data = await _snapshot.refresh(dataInicial, dataFinal, empresaCodigo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data, "snapshot": {"hit": False, "stale": False}}


@router.get("/dre")
async def get_confirmed_departmental_dre(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: int | None = Query(None),
) -> dict:
    try:
        data, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    except WebPostoOfflineBlocked:
        return offline_unavailable_response(route="/api/v1/finance/director-reconciliation/dre")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    body = {"success": True, "data": {
        "period": data.get("period"),
        "scope": data.get("scope"),
        "lines": data.get("departmentalDre") or [],
        "publication": data.get("publication"),
        "coverage": data.get("coverage"),
    }, "snapshot": {"hit": hit, "stale": stale}}
    if webposto_offline_mode():
        return annotate_offline_success(body, source="snapshot")
    return body


@router.get("/dre-complete")
async def get_complete_departmental_dre(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: int | None = Query(None),
    regime: str = Query(
        "competencia",
        description="competencia (data da nota) | caixa (data do pagamento/boleto)",
    ),
    summary: bool = Query(
        True,
        description="Retorna árvore resumida (totais) — padrão para budget HTTP < 1.2s",
    ),
    refresh: bool = Query(
        False,
        description="Força recálculo (ignora cache RAM/TTL 60s)",
    ),
) -> dict:
    try:
        data, stale, hit = await _complete_dre_snapshot.get_or_collect(
            dataInicial,
            dataFinal,
            empresaCodigo,
            force_refresh=refresh,
            regime=regime,
        )
    except WebPostoOfflineBlocked:
        return offline_unavailable_response(
            route="/api/v1/finance/director-reconciliation/dre-complete"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = summarize_dre_payload(data) if summary else data
    if isinstance(payload, dict):
        payload.setdefault("regime", data.get("regime") or regime)
        payload.setdefault("periodLock", data.get("periodLock") or {})
    body = {
        "success": True,
        "data": payload,
        "snapshot": {"hit": hit, "stale": stale, "summary": summary, "ttlSeconds": 60},
    }
    if webposto_offline_mode():
        return annotate_offline_success(body, source="snapshot")
    return body


@router.get("/dre-validation")
async def validate_complete_departmental_dre(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: int | None = Query(None),
) -> dict:
    data = await _complete_dre.build(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": {
        "dre": data,
        "validation": _dre_homologation.validate(data),
    }}


@router.post("/dre-approve")
async def approve_complete_departmental_dre(
    body: DreApprovalBody,
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
) -> dict:
    data = await _complete_dre.build(dataInicial, dataFinal, None)
    try:
        approval = _dre_homologation.approve(data, body.reviewer, body.rationale)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"success": True, "data": approval.model_dump(mode="json")}


@router.get("/department-reviews")
async def list_department_reviews() -> dict:
    return {"success": True, "data": [
        item.model_dump(mode="json") for item in _pipeline._reviews.list_all()
    ]}


@router.post("/department-reviews")
async def assign_department_review(
    body: DepartmentReviewBody,
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: int | None = Query(None),
) -> dict:
    try:
        review = _pipeline._reviews.assign(
            body.factId, body.department, body.reviewer, body.rationale,
            body.category, body.subcategory, body.recipientName,
        )
        rule = None
        if body.applyToAccount:
            if not body.managementAccountCode:
                raise ValueError("plano de contas obrigatorio para regra permanente")
            rule = _pipeline._reviews.assign_rule(
                body.managementAccountCode, body.department, body.reviewer, body.rationale
                , body.category, body.subcategory
            )
        data = await _snapshot.refresh(dataInicial, dataFinal, empresaCodigo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": {
        "review": review.model_dump(mode="json"),
        "rule": rule.model_dump(mode="json") if rule else None,
        "reconciliation": data,
    }}


@router.get("/expense-classifications")
async def list_expense_classifications() -> dict:
    return {"success": True, "data": {
        "reviews": [item.model_dump(mode="json") for item in _pipeline._reviews.list_all()],
        "rules": [item.model_dump(mode="json") for item in _pipeline._reviews.list_rules()],
    }}


@router.post("/expense-classifications")
async def classify_expense(body: ExpenseClassificationBody) -> dict:
    try:
        review = _pipeline._reviews.assign(
            body.factId, body.department, body.reviewer, body.rationale,
            body.category, body.subcategory,
        )
        rule = _pipeline._reviews.assign_rule(
            body.managementAccountCode, body.department, body.reviewer, body.rationale,
            body.category, body.subcategory,
        ) if body.applyToSimilar and body.managementAccountCode.strip() else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": {
        "review": review.model_dump(mode="json"),
        "rule": rule.model_dump(mode="json") if rule else None,
    }}


@router.post("/expense-classifications/batch")
async def classify_expenses_batch(body: ExpenseClassificationBatchBody) -> dict:
    saved = []
    rules_by_account = {}
    try:
        for item in body.items:
            review = _pipeline._reviews.assign(
                item.factId, item.department, item.reviewer, item.rationale,
                item.category, item.subcategory, item.recipientName,
            )
            saved.append(review.model_dump(mode="json"))
            if item.applyToSimilar and item.managementAccountCode.strip() and item.managementAccountCode not in rules_by_account:
                rule = _pipeline._reviews.assign_rule(
                    item.managementAccountCode, item.department, item.reviewer, item.rationale,
                    item.category, item.subcategory,
                )
                rules_by_account[item.managementAccountCode] = rule.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": {
        "savedCount": len(saved), "reviews": saved, "rules": list(rules_by_account.values()),
    }}


@router.delete("/expense-classifications/{fact_id}")
async def undo_expense_classification(fact_id: str, managementAccountCode: str | None = Query(None)) -> dict:
    review_removed = _pipeline._reviews.delete(fact_id)
    rule_removed = _pipeline._reviews.delete_rule(managementAccountCode) if managementAccountCode else False
    return {"success": True, "data": {"reviewRemoved": review_removed, "ruleRemoved": rule_removed}}


@router.get("/department-rules")
async def list_department_rules() -> dict:
    return {"success": True, "data": [
        item.model_dump(mode="json") for item in _pipeline._reviews.list_rules()
    ]}


@router.get("/allocation-rules")
async def list_allocation_rules() -> dict:
    return {"success": True, "data": [
        item.model_dump(mode="json") for item in _pipeline._reviews.list_allocations()
    ]}


@router.post("/allocation-rules")
async def assign_allocation_rule(
    body: SharedAllocationBody,
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: int | None = Query(None),
) -> dict:
    try:
        rule = _pipeline._reviews.assign_allocation(
            body.managementAccountCode, body.percentages, body.reviewer, body.rationale
        )
        data = await _snapshot.refresh(dataInicial, dataFinal, empresaCodigo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": {
        "rule": rule.model_dump(mode="json"),
        "reconciliation": data,
    }}
