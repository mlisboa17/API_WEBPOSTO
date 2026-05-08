from fastapi import APIRouter, Depends

from src.application.services.sync_service import SyncService
from src.interfaces.http.dependencies import get_sync_service

router = APIRouter(prefix="/sync", tags=["Sync"])


@router.post("/clientes")
async def sync_clientes(service: SyncService = Depends(get_sync_service)):
    """Sincroniza clientes da API webPosto."""
    return await service.sync_clientes()


@router.post("/abastecimentos")
async def sync_abastecimentos(service: SyncService = Depends(get_sync_service)):
    """Sincroniza abastecimentos da API webPosto."""
    return await service.sync_abastecimentos()


@router.post("/financeiro")
async def sync_financeiro(service: SyncService = Depends(get_sync_service)):
    """Sincroniza dados financeiros da API webPosto."""
    return await service.sync_financeiro()


@router.post("/caixa")
async def sync_caixa(service: SyncService = Depends(get_sync_service)):
    """Sincroniza movimentos de caixa da API webPosto."""
    return await service.sync_caixa()


@router.post("/full")
async def full_sync(service: SyncService = Depends(get_sync_service)):
    """Sincroniza tudo: clientes, abastecimentos, financeiro, caixa."""
    return await service.full_sync()
