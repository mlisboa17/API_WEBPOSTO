"""
FastAPI Routes - Auditoria
Endpoints para análise de despesas e fechamentos de caixa
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from src.application.services.auditoria_service import AuditoriaService
from src.domain.models.auditoria_models import (
    DespesaCaixa,
    ResumoAuditoriaUnidade,
    ListaFechamentos,
)
from src.interfaces.http.dependencies import get_auditoria_service
from src.shared.logger import logger

__all__ = ["router"]

router = APIRouter(
    prefix="/auditoria",
    tags=["auditoria"],
    responses={
        404: {"description": "Recurso não encontrado"},
        500: {"description": "Erro interno do servidor"},
    },
)

log = logger.getChild(__name__)


@router.get(
    "/health",
    summary="Health Check",
    description="Verifica saúde do serviço de auditoria",
    response_model=dict,
)
async def health_check(
    service: AuditoriaService = Depends(get_auditoria_service),
) -> dict:
    """
    Health check do serviço de auditoria

    Returns:
        Status do serviço
    """
    try:
        return {
            "status": "ok",
            "service": "Logos Auditoria",
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        log.error(f"Erro em health check: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao verificar saúde")


@router.get(
    "/despesas/{unidade_id}",
    summary="Listar Despesas",
    description="Retorna despesas de uma unidade",
    response_model=List[DespesaCaixa],
    responses={
        200: {
            "description": "Lista de despesas",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "exp_001",
                            "unidade_id": "real_01",
                            "caixa_tipo": "pista",
                            "horario": "2026-04-12T14:30:00",
                            "categoria": "gelo",
                            "valor": 85.50,
                            "operador": "João Silva",
                            "status_justificativa": "justificada",
                            "tem_documento": True,
                        }
                    ]
                }
            },
        },
        404: {"description": "Nenhuma despesa encontrada para a unidade"},
    },
)
async def get_despesas_unidade(
    unidade_id: str = Query(
        ..., description="ID da unidade (ex: 'real_01', 'casa_caiada_01')"
    ),
    data: Optional[str] = Query(
        None, description="Data para filtro (ISO 8601 format, opcional)"
    ),
    service: AuditoriaService = Depends(get_auditoria_service),
) -> List[DespesaCaixa]:
    """
    Retorna despesas estruturadas de uma unidade

    Parâmetros:
    - **unidade_id**: ID único da unidade (obrigatório)
    - **data**: Data para filtro, formato ISO 8601 (opcional)

    Raises:
        HTTPException 404: Se nenhuma despesa for encontrada
        HTTPException 500: Se houver erro na extração
    """
    try:
        data_obj = None
        if data:
            try:
                data_obj = datetime.fromisoformat(data)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Data inválida. Use formato ISO 8601 (ex: 2026-04-12T14:30:00)",
                )

        despesas = await service.extrair_despesas_por_unidade(unidade_id, data_obj)

        if not despesas:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhuma despesa encontrada para a unidade '{unidade_id}'",
            )

        log.info(f"Despesas retornadas para {unidade_id}: {len(despesas)} registros")
        return despesas

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Erro ao buscar despesas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao extrair despesas")


@router.get(
    "/fechamentos/{unidade_id}",
    summary="Listar Fechamentos",
    description="Retorna fechamentos com resumo consolidado de uma unidade",
    response_model=ListaFechamentos,
)
async def get_fechamentos_unidade(
    unidade_id: str = Query(..., description="ID da unidade"),
    data: Optional[str] = Query(None, description="Data para filtro (opcional)"),
    service: AuditoriaService = Depends(get_auditoria_service),
) -> ListaFechamentos:
    """
    Retorna fechamentos estruturados com resumo consolidado

    Parâmetros:
    - **unidade_id**: ID único da unidade (obrigatório)
    - **data**: Data para filtro (opcional)

    Raises:
        HTTPException 404: Se nenhum fechamento for encontrado
        HTTPException 500: Se houver erro na extração
    """
    try:
        data_obj = None
        if data:
            try:
                data_obj = datetime.fromisoformat(data)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Data inválida. Use formato ISO 8601",
                )

        lista = await service.get_fechamentos_com_resumo(unidade_id, data_obj)

        if not lista.fechamentos:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhum fechamento encontrado para a unidade '{unidade_id}'",
            )

        log.info(
            f"Fechamentos retornados para {unidade_id}: {len(lista.fechamentos)} registros"
        )
        return lista

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Erro ao buscar fechamentos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao extrair fechamentos")


@router.get(
    "/resumo/{unidade_id}",
    summary="Resumo Executivo",
    description="Retorna resumo executivo com KPIs e insights de auditoria",
    response_model=ResumoAuditoriaUnidade,
)
async def get_resumo_auditoria(
    unidade_id: str = Query(..., description="ID da unidade"),
    data: Optional[str] = Query(None, description="Data para filtro (opcional)"),
    service: AuditoriaService = Depends(get_auditoria_service),
) -> ResumoAuditoriaUnidade:
    """
    Retorna resumo executivo de auditoria com KPIs e insights

    Consolida:
    - Faturamento total
    - Despesas operacionais
    - Quebra de caixa
    - Status de caixas
    - Flags de auditoria

    Análise Estoica:
    - Desvio de despesas em relação a padrão de 5%
    - Identificação de outliers

    Parâmetros:
    - **unidade_id**: ID único da unidade
    - **data**: Data para filtro (opcional)

    Raises:
        HTTPException 500: Se houver erro no cálculo
    """
    try:
        data_obj = None
        if data:
            try:
                data_obj = datetime.fromisoformat(data)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Data inválida",
                )

        fechamentos = await service.extrair_fechamentos(unidade_id, data_obj)
        despesas = await service.extrair_despesas_por_unidade(unidade_id, data_obj)

        resumo = service.calcular_resumo_unidade(fechamentos, despesas)

        log.info(f"Resumo calculado para {unidade_id}")
        return resumo

    except Exception as e:
        log.error(f"Erro ao calcular resumo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao calcular resumo")


@router.post(
    "/registrar-despesa",
    summary="Registrar Nova Despesa",
    description="Registra nova despesa no sistema",
    response_model=DespesaCaixa,
    status_code=201,
)
async def registrar_despesa(
    despesa: DespesaCaixa,
    service: AuditoriaService = Depends(get_auditoria_service),
) -> DespesaCaixa:
    """
    Registra nova despesa no sistema

    Request Body:
    ```json
    {
      "id": "exp_001",
      "unidade_id": "real_01",
      "caixa_tipo": "pista",
      "horario": "2026-04-12T14:30:00",
      "categoria": "gelo",
      "valor": 85.50,
      "operador": "João Silva",
      "status_justificativa": "justificada",
      "documento_anexo": "/docs/gelo_001.pdf",
      "tem_documento": true
    }
    ```

    Validações de Negócio:
    - Valor deve ser positivo
    - Despesa sem documento gera alerta
    - Despesa sem categoria marcada para auditoria

    Raises:
        HTTPException 422: Se validação de campo falhar
        HTTPException 500: Se houver erro na persistência

    Returns:
        Despesa registrada com sucesso
    """
    try:
        despesa_registrada = await service.registrar_despesa(despesa)
        log.info(f"Despesa registrada: {despesa.id}")
        return despesa_registrada

    except ValidationError as e:
        log.warning(f"Erro de validação ao registrar despesa: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.error(f"Erro ao registrar despesa: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao registrar despesa")
