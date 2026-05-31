import asyncio
import logging
import os
from time import perf_counter
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlmodel import select

from src.application.sync_products import SyncProductsUseCase
from src.domain.entities import TenantPostoRecord
from src.infrastructure.cache import cache_manager
from src.infrastructure.database import async_session
from src.infrastructure.webposto_client import WebPostoClient


logger = logging.getLogger(__name__)


def load_environment() -> None:
    """Load .env from gateway root and workspace root when present."""
    current_file = Path(__file__).resolve()
    gateway_root = current_file.parents[2]
    workspace_root = gateway_root.parent

    gateway_env = gateway_root / ".env"
    workspace_env = workspace_root / ".env"

    if workspace_env.exists():
        load_dotenv(dotenv_path=workspace_env, override=False)
    if gateway_env.exists():
        load_dotenv(dotenv_path=gateway_env, override=False)


async def ensure_vip_tenant_from_env() -> None:
    api_key = (os.getenv("WEBPOSTO_API_KEY") or "").strip()
    base_url = (os.getenv("WEBPOSTO_BASE_URL") or "").strip()

    # If not configured, skip silently.
    if not api_key or not base_url:
        return

    posto_id = (os.getenv("WEBPOSTO_VIP_POSTO_ID") or api_key).strip()
    nome = (os.getenv("WEBPOSTO_VIP_POSTO_NOME") or "Posto VIP").strip()

    async with async_session() as session:
        result = await session.execute(select(TenantPostoRecord).where(TenantPostoRecord.id == posto_id))
        tenant = result.scalar_one_or_none()

        if tenant is None:
            tenant = TenantPostoRecord(
                id=posto_id,
                nome_posto=nome,
                webposto_base_url=base_url,
                api_key=api_key,
                ativo=True,
            )
            session.add(tenant)
        else:
            tenant.nome_posto = nome
            tenant.webposto_base_url = base_url
            tenant.api_key = api_key
            tenant.ativo = True

        await session.commit()


async def run_initial_vip_sync_pipeline() -> None:
    """Run initial VIP catalog sync in background without blocking startup."""
    started = perf_counter()
    status = "success"
    reason = "completed"

    try:
        api_key = (os.getenv("WEBPOSTO_API_KEY") or "").strip()
        base_url = (os.getenv("WEBPOSTO_BASE_URL") or "").strip()
        posto_id = (os.getenv("WEBPOSTO_VIP_POSTO_ID") or api_key).strip()
        endpoint_path = os.getenv("WEBPOSTO_PRODUCTS_ENDPOINT", "/INTEGRACAO/PRODUTOS")
        timeout = min(int(os.getenv("WEBPOSTO_API_TIMEOUT", "10")), 10)

        if not api_key or not base_url:
            status = "skipped"
            reason = "missing_env"
            return

        async with WebPostoClient(timeout=timeout) as client:
            catalog = await client.fetch_products_catalog(
                base_url=base_url,
                api_key=api_key,
                posto_id=posto_id,
                include_inactive=True,
                endpoint_path=endpoint_path,
            )

        async with async_session() as session:
            use_case = SyncProductsUseCase(db_session=session, cache=cache_manager)
            await use_case.execute(posto_id=posto_id, catalog=catalog, force_refresh=True)
    except Exception:
        status = "failed"
        reason = "exception"
        logger.exception("vip_initial_sync_error")
    finally:
        elapsed_ms = round((perf_counter() - started) * 1000, 3)
        logger.info(
            "vip_initial_sync_finished status=%s reason=%s duration_ms=%s",
            status,
            reason,
            elapsed_ms,
        )


def schedule_initial_vip_sync_task() -> Optional[asyncio.Task]:
    """Schedule background sync task and return task handle."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning("vip_initial_sync_not_scheduled_no_loop")
        return None
    return loop.create_task(run_initial_vip_sync_pipeline())
