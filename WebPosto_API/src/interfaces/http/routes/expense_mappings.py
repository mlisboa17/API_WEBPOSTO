"""Rotas de gerenciamento de mapeamento de despesas — Sprint 47."""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.http.authz import require_roles
from src.services.expense_categorization_service import (
    ExpenseCategorizationService,
    ExpenseMappingRule,
    MatchConfidence,
    CategorizationSummary,
)
from src.domain.enums.expense_classification import ExpenseClassification

router = APIRouter(
    prefix="/api/v1/financial/expense-mappings",
    tags=["Expense Mappings S47"],
)


class CreateMappingRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    webposto_pattern: str = Field(min_length=1)
    target_classification: str
    confidence_level: str = "PATTERN"
    department: str | None = None
    priority: int = 50


class UpdateMappingRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_active: bool | None = None
    priority: int | None = None
    target_classification: str | None = None


class ReclassifyRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    original_description: str
    new_classification: str
    created_by: str = "user"


class CategorizeRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    expenses: list[dict]


def _get_service() -> ExpenseCategorizationService:
    return ExpenseCategorizationService()


@router.get("/")
async def list_mapping_rules(
    active_only: bool = Query(True),
    current_user: dict = Depends(require_roles("director", "admin", "manager")),
) -> dict:
    service = _get_service()
    rules = service.list_rules(active_only=active_only)
    return {
        "success": True,
        "data": {
            "total": len(rules),
            "rules": [r.model_dump() for r in rules],
        },
    }


@router.get("/{rule_id}")
async def get_mapping_rule(
    rule_id: str,
    current_user: dict = Depends(require_roles("director", "admin", "manager")),
) -> dict:
    service = _get_service()
    rule = service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    return {"success": True, "data": rule.model_dump()}


@router.post("/")
async def create_mapping_rule(
    body: CreateMappingRequest,
    current_user: dict = Depends(require_roles("director", "admin")),
) -> dict:
    service = _get_service()

    try:
        classification = ExpenseClassification(body.target_classification)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Classificação inválida: {body.target_classification}")

    try:
        confidence = MatchConfidence(body.confidence_level)
    except ValueError:
        confidence = MatchConfidence.PATTERN

    rule = service.add_rule(
        webposto_pattern=body.webposto_pattern,
        target_classification=classification,
        confidence_level=confidence,
        department=body.department,
        created_by=current_user.get("email", "user"),
        priority=body.priority,
    )

    return {"success": True, "data": rule.model_dump()}


@router.put("/{rule_id}")
async def update_mapping_rule(
    rule_id: str,
    body: UpdateMappingRequest,
    current_user: dict = Depends(require_roles("director", "admin")),
) -> dict:
    service = _get_service()

    classification = None
    if body.target_classification:
        try:
            classification = ExpenseClassification(body.target_classification)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Classificação inválida")

    rule = service.update_rule(
        rule_id=rule_id,
        is_active=body.is_active,
        priority=body.priority,
        target_classification=classification,
    )

    if not rule:
        raise HTTPException(status_code=404, detail="Regra não encontrada")

    return {"success": True, "data": rule.model_dump()}


@router.delete("/{rule_id}")
async def delete_mapping_rule(
    rule_id: str,
    current_user: dict = Depends(require_roles("admin")),
) -> dict:
    service = _get_service()
    deleted = service.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    return {"success": True, "message": "Regra excluída"}


@router.post("/categorize")
async def categorize_expenses(
    body: CategorizeRequest,
    current_user: dict = Depends(require_roles("director", "admin", "manager")),
) -> dict:
    service = _get_service()
    summary = service.categorize_batch(body.expenses)
    return {
        "success": True,
        "data": summary.model_dump(),
    }


@router.post("/reclassify-pending")
async def reclassify_pending_expenses(
    body: CategorizeRequest,
    current_user: dict = Depends(require_roles("director", "admin")),
) -> dict:
    service = _get_service()
    summary = service.reclassify_pending(body.expenses)
    return {
        "success": True,
        "data": {
            "total": summary.total_expenses,
            "categorized": summary.categorized,
            "still_pending": summary.pending,
            "by_classification": summary.by_classification,
        },
    }


@router.post("/learn")
async def learn_from_reclassification(
    body: ReclassifyRequest,
    current_user: dict = Depends(require_roles("director", "admin")),
) -> dict:
    service = _get_service()

    try:
        classification = ExpenseClassification(body.new_classification)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Classificação inválida: {body.new_classification}")

    rule = service.learn_from_reclassification(
        original_description=body.original_description,
        new_classification=classification,
        created_by=body.created_by,
    )

    return {
        "success": True,
        "data": rule.model_dump(),
        "message": "Nova regra criada a partir da reclassificação",
    }


@router.get("/stats/coverage")
async def mapping_coverage_stats(
    current_user: dict = Depends(require_roles("director", "admin", "manager")),
) -> dict:
    service = _get_service()
    rules = service.list_rules(active_only=True)

    by_classification: dict[str, int] = {}
    by_confidence: dict[str, int] = {}

    for rule in rules:
        cls = rule.target_classification.value
        by_classification[cls] = by_classification.get(cls, 0) + 1
        conf = rule.confidence_level.value
        by_confidence[conf] = by_confidence.get(conf, 0) + 1

    return {
        "success": True,
        "data": {
            "total_rules": len(rules),
            "by_classification": by_classification,
            "by_confidence": by_confidence,
        },
    }
