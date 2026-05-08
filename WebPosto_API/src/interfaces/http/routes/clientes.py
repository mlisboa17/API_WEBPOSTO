from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.dto.cliente_dto import (
    ClienteCreateDTO,
    ClienteResponseDTO,
    ClienteUpdateDTO,
)
from src.application.services.cliente_service import ClienteService
from src.interfaces.http.dependencies import get_cliente_service

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post(
    "/", response_model=ClienteResponseDTO, status_code=status.HTTP_201_CREATED
)
async def criar_cliente(
    dto: ClienteCreateDTO, service: ClienteService = Depends(get_cliente_service)
):
    """Cria um novo cliente."""
    return await service.criar_cliente(dto)


@router.get("/{cliente_id}", response_model=ClienteResponseDTO)
async def obter_cliente(
    cliente_id: str, service: ClienteService = Depends(get_cliente_service)
):
    """Obtém um cliente por ID."""
    cliente = await service.obter_cliente(cliente_id)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )
    return cliente


@router.get("/", response_model=List[ClienteResponseDTO])
async def listar_clientes(
    skip: int = 0,
    limit: int = 100,
    apenas_ativos: bool = False,
    service: ClienteService = Depends(get_cliente_service),
):
    """Lista clientes com paginação."""
    if apenas_ativos:
        return await service.listar_ativos(skip, limit)
    return await service.listar_clientes(skip, limit)


@router.put("/{cliente_id}", response_model=ClienteResponseDTO)
async def atualizar_cliente(
    cliente_id: str,
    dto: ClienteUpdateDTO,
    service: ClienteService = Depends(get_cliente_service),
):
    """Atualiza um cliente existente."""
    cliente = await service.atualizar_cliente(cliente_id, dto)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )
    return cliente


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_cliente(
    cliente_id: str, service: ClienteService = Depends(get_cliente_service)
):
    """Deleta um cliente."""
    success = await service.deletar_cliente(cliente_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )
    return None
