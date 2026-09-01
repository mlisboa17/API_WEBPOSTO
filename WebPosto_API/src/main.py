import logging

import uvicorn

from src.infrastructure.config.settings import settings
from src.interfaces.http.app import create_app

app = create_app()
LOGGER = logging.getLogger(__name__)


def _resolve_workers() -> int:
    """Cache RAM de pista exige um único processo uvicorn."""
    if settings.pista_sync_worker_enabled:
        if settings.api_workers != 1:
            LOGGER.warning(
                "pista_sync_worker_enabled=True → forçando API_WORKERS=1 "
                "(configurado=%s) para unificar cache In-Memory",
                settings.api_workers,
            )
        return 1
    return max(1, int(settings.api_workers or 1))


if __name__ == "__main__":
    workers = _resolve_workers()
    # reload=False com worker de pista: evita restart no meio do discover_permissions
    # (que envenena o permission_cache com 401 e zera o cache RAM).
    use_reload = bool(settings.debug and workers == 1 and not settings.pista_sync_worker_enabled)
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=workers,
        reload=use_reload,
        log_level=settings.log_level.lower(),
    )
