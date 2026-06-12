from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.core.config import load_core_config
from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse

router = APIRouter(prefix="/api/v1/finance/statements", tags=["Statements"])


class OfxTransactionIn(BaseModel):
    valor: float
    data: str
    descricao: str
    tipo: str | None = None


class OfxImportIn(BaseModel):
    cdConta: int = Field(..., ge=1)
    cdFilial: int = Field(..., ge=1)
    dataInicial: str
    opcaoImportacao: str = "IMPORTAR_APENAS_DIAS_INEXISTENTES_SISTEMA"
    transacoes: list[OfxTransactionIn]


@router.post("/import-ofx")
async def import_ofx(body: OfxImportIn) -> dict[str, Any]:
    cfg = load_core_config()
    payload = body.model_dump()
    payload["transacoes"] = [t.model_dump(exclude_none=True) for t in body.transacoes]
    params = {"CHAVE": cfg.webposto_api_key}
    url = f"{cfg.webposto_base_url.rstrip('/')}/INTEGRACAO/INCLUIR_OFX"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, params=params, json=payload)

    if response.status_code not in (200, 204):
        return WebPostoResponse.fail(
            WebPostoError(
                endpoint="/INTEGRACAO/INCLUIR_OFX",
                status=response.status_code,
                type="WEBPOSTO_ERROR",
                message=response.text[:220],
            )
        ).to_dict()

    return WebPostoResponse.ok({"imported": len(body.transacoes)}).to_dict()
