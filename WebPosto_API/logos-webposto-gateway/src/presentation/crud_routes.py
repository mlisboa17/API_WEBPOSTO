from decimal import Decimal
from typing import Annotated, Any, Dict, Optional, Type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

from src.domain.crud_entities import (
    CartaoReceberRecord,
    ContaPagarRecord,
    GrupoRecord,
    MovimentacaoCaixaRecord,
    NfeCompraRecord,
    ProdutoRecord,
    SubgrupoRecord,
    TituloReceberRecord,
)
from src.infrastructure.database import get_db
from src.presentation.security import require_admin_token, require_consumer_token

router = APIRouter(prefix="/v1/crud", tags=["crud"])

RESOURCE_MODEL_MAP: Dict[str, Type[SQLModel]] = {
    "grupos": GrupoRecord,
    "subgrupos": SubgrupoRecord,
    "produtos": ProdutoRecord,
    "movimentacoes-caixa": MovimentacaoCaixaRecord,
    "nfe-compras": NfeCompraRecord,
    "contas-a-pagar": ContaPagarRecord,
    "titulos-a-receber": TituloReceberRecord,
    "cartoes-a-receber": CartaoReceberRecord,
}


def _resolve_model(resource: str) -> Type[SQLModel]:
    model = RESOURCE_MODEL_MAP.get(resource)
    if model is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "resource_not_found",
                "resource": resource,
                "available": list(RESOURCE_MODEL_MAP.keys()),
            },
        )
    return model


async def _validate_payload(
    resource: str,
    payload: Dict[str, Any],
    db: AsyncSession,
) -> None:
    if resource == "movimentacoes-caixa" and "tipo" in payload:
        if str(payload["tipo"]).upper() not in {"DEBITO", "CREDITO"}:
            raise HTTPException(status_code=422, detail="tipo must be DEBITO or CREDITO")

    if resource in {"produtos", "movimentacoes-caixa", "nfe-compras", "contas-a-pagar", "titulos-a-receber", "cartoes-a-receber"}:
        money_fields = {
            "produtos": ["preco"],
            "movimentacoes-caixa": ["valor"],
            "nfe-compras": ["valor_total"],
            "contas-a-pagar": ["valor"],
            "titulos-a-receber": ["valor"],
            "cartoes-a-receber": ["valor"],
        }
        for field_name in money_fields.get(resource, []):
            if field_name in payload:
                value = Decimal(str(payload[field_name]))
                if value < 0:
                    raise HTTPException(status_code=422, detail=f"{field_name} must be >= 0")

    if resource == "nfe-compras" and "status" in payload:
        allowed = {"aberta", "processada", "cancelada"}
        if payload["status"] not in allowed:
            raise HTTPException(status_code=422, detail="invalid status for nfe-compras")

    if resource == "contas-a-pagar" and "status" in payload:
        allowed = {"aberta", "paga", "vencida", "cancelada"}
        if payload["status"] not in allowed:
            raise HTTPException(status_code=422, detail="invalid status for contas-a-pagar")

    if resource == "titulos-a-receber" and "status" in payload:
        allowed = {"aberto", "recebido", "vencido", "cancelado"}
        if payload["status"] not in allowed:
            raise HTTPException(status_code=422, detail="invalid status for titulos-a-receber")

    if resource == "cartoes-a-receber" and "status" in payload:
        allowed = {"pendente", "recebido", "conciliado", "cancelado"}
        if payload["status"] not in allowed:
            raise HTTPException(status_code=422, detail="invalid status for cartoes-a-receber")

    if resource == "subgrupos" and "grupo_id" in payload:
        parent = await db.get(GrupoRecord, int(payload["grupo_id"]))
        if parent is None:
            raise HTTPException(status_code=422, detail="grupo_id not found")

    if resource == "produtos" and "subgrupo_id" in payload:
        parent = await db.get(SubgrupoRecord, int(payload["subgrupo_id"]))
        if parent is None:
            raise HTTPException(status_code=422, detail="subgrupo_id not found")


@router.get("/{resource}", status_code=200)
async def list_resource(
    resource: str,
    _: None = Depends(require_consumer_token),
    db: AsyncSession = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    status: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
):
    model = _resolve_model(resource)
    stmt = select(model)

    if status and hasattr(model, "status"):
        stmt = stmt.where(getattr(model, "status") == status)

    if q:
        search_columns = [col for col in ("nome", "descricao", "fornecedor", "cliente", "numero_nfe", "bandeira", "sku") if hasattr(model, col)]
        if search_columns:
            conditions = [getattr(model, col).ilike(f"%{q}%") for col in search_columns]
            stmt = stmt.where(or_(*conditions))

    count_stmt = select(func.count()).select_from(model)
    if status and hasattr(model, "status"):
        count_stmt = count_stmt.where(getattr(model, "status") == status)
    if q:
        search_columns = [col for col in ("nome", "descricao", "fornecedor", "cliente", "numero_nfe", "bandeira", "sku") if hasattr(model, col)]
        if search_columns:
            conditions = [getattr(model, col).ilike(f"%{q}%") for col in search_columns]
            count_stmt = count_stmt.where(or_(*conditions))

    stmt = stmt.offset(offset).limit(limit)
    total_result = await db.execute(count_stmt)
    total = int(total_result.scalar() or 0)

    result = await db.execute(stmt)
    items = result.scalars().all()
    return {
        "resource": resource,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [item.model_dump(mode="json") for item in items],
    }


@router.get("/{resource}/{record_id}", status_code=200)
async def get_resource(
    resource: str,
    record_id: int,
    _: None = Depends(require_consumer_token),
    db: AsyncSession = Depends(get_db),
):
    model = _resolve_model(resource)
    record = await db.get(model, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="record_not_found")
    return {"resource": resource, "item": record.model_dump(mode="json")}


@router.post("/{resource}", status_code=201)
async def create_resource(
    resource: str,
    payload: Dict[str, Any],
    _: None = Depends(require_consumer_token),
    db: AsyncSession = Depends(get_db),
    __: None = Depends(require_admin_token),
):
    model = _resolve_model(resource)
    await _validate_payload(resource=resource, payload=payload, db=db)
    try:
        entity = model(**payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"invalid_payload: {exc}")

    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return {"resource": resource, "item": entity.model_dump(mode="json")}


@router.put("/{resource}/{record_id}", status_code=200)
async def update_resource(
    resource: str,
    record_id: int,
    payload: Dict[str, Any],
    _: None = Depends(require_consumer_token),
    db: AsyncSession = Depends(get_db),
    __: None = Depends(require_admin_token),
):
    model = _resolve_model(resource)
    entity = await db.get(model, record_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="record_not_found")

    await _validate_payload(resource=resource, payload=payload, db=db)

    for key, value in payload.items():
        if key == "id":
            continue
        if hasattr(entity, key):
            setattr(entity, key, value)

    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return {"resource": resource, "item": entity.model_dump(mode="json")}


@router.delete("/{resource}/{record_id}", status_code=200)
async def delete_resource(
    resource: str,
    record_id: int,
    _: None = Depends(require_consumer_token),
    db: AsyncSession = Depends(get_db),
    __: None = Depends(require_admin_token),
):
    model = _resolve_model(resource)
    entity = await db.get(model, record_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="record_not_found")

    await db.delete(entity)
    await db.commit()
    return {"resource": resource, "deleted_id": record_id, "status": "deleted"}
