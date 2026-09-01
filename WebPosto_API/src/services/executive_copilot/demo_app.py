"""Entrypoint isolado da demonstração do Copiloto. Sem scheduler, migração ou API 8040.

Importar este módulo não abre porta, não chama rede e não inicia jobs.
O bind só ocorre em __main__ após --bind explícito.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from src.interfaces.http.routes.auth import router as auth_router
from src.interfaces.http.routes.executive_copilot_ask import router
from src.interfaces.http.routes.executive_copilot_data_requests import (
    configure_data_on_demand,
    router as data_requests_router,
)
from src.interfaces.http.routes.executive_copilot_action_drafts import (
    configure_expense_drafts,
    router as action_drafts_router,
)
from src.services.executive_copilot.contracts import WEBPOSTO_WRITES
from src.services.executive_copilot.data_on_demand.http_contract import EXECUTOR_MODE

DEMO_BIND = "127.0.0.1"
DEMO_PORT = 8095
DEMO_SAFETY = {
    "bind": DEMO_BIND,
    "defaultPort": DEMO_PORT,
    "mainApi8040": False,
    "scheduler": False,
    "migrations": False,
    "webposto": False,
    "authBypass": False,
    "officialAuth": True,
    "jobs": False,
    "dataOnDemandFake": True,
    "executorMode": EXECUTOR_MODE,
    "webpostoWrites": WEBPOSTO_WRITES,
}


async def _demo_current_user(request: Request) -> dict:
    """Auth real no processo isolado. Não reutiliza bypass de desenvolvimento."""
    from src.interfaces.http.read_mode_guard import user_from_request

    try:
        user = user_from_request(request, allow_dev_bypass=False)
    except HTTPException:
        raise
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _demo_data_on_demand_service():
    """Planner local com executor falso. Lê checkpoints; não escreve SDS nem WebPosto."""
    from src.services.executive_copilot.data_on_demand.executor import FakeDataRefreshExecutor
    from src.services.executive_copilot.data_on_demand.service import DataOnDemandService
    from src.services.executive_copilot.data_on_demand.store import DataRequestStore, default_store_path
    from src.services.executive_copilot.local_store import SqliteCheckpointStore
    from src.services.sds_process_lock import NullSdsProcessLock

    return DataOnDemandService(
        DataRequestStore(default_store_path()),
        SqliteCheckpointStore(),
        executor=FakeDataRefreshExecutor(auto_by_units=True),
        process_lock=NullSdsProcessLock(),
        auto_run_on_confirm=True,
    )


def _demo_expense_draft_service():
    from src.services.executive_copilot.expense_drafts import ExpenseDraftService

    return ExpenseDraftService()


def create_demo_app(data_on_demand_service=None, expense_draft_service=None):
    from fastapi import FastAPI

    from src.interfaces.http.dependencies import get_current_user

    if data_on_demand_service is not None:
        configure_data_on_demand(data_on_demand_service)
    else:
        configure_data_on_demand(factory=_demo_data_on_demand_service)
    if expense_draft_service is not None:
        configure_expense_drafts(expense_draft_service)
    else:
        configure_expense_drafts(factory=_demo_expense_draft_service)
    app = FastAPI(
        title="LOGOS Executive Copilot Demo",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.include_router(auth_router)
    app.include_router(router)
    app.include_router(data_requests_router)
    app.include_router(action_drafts_router)
    app.dependency_overrides[get_current_user] = _demo_current_user

    @app.get("/health")
    async def demo_health() -> dict:
        return {
            "service": "executive-copilot-local",
            "webpostoWrites": WEBPOSTO_WRITES,
        }

    @app.get("/auth/me")
    async def current_user_identity(request: Request) -> dict:
        """Identidade do JWT oficial. Sem bypass e sem enriquecer o token."""
        user = await _demo_current_user(request)
        return {
            "sub": user.get("sub"),
            "email": user.get("email") or user.get("sub"),
            "role": user.get("role"),
            "company_id": user.get("company_id"),
        }

    return app


def demo_safety_report() -> dict[str, object]:
    return dict(DEMO_SAFETY)


def demo_cli_error(*, bind: bool, host: str, port: int) -> str | None:
    """Valida o CLI sem abrir porta. None = permitido."""
    if not bind:
        return "Recusado: informe --bind para abrir a porta."
    if host not in {"127.0.0.1", "localhost"}:
        return "Recusado: somente loopback 127.0.0.1/localhost"
    if port == 8040:
        return "Recusado: porta 8040 é a API principal"
    return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Copiloto Executivo — demo isolada loopback")
    parser.add_argument("--bind", action="store_true", help="Obrigatório para abrir a porta")
    parser.add_argument("--host", default=DEMO_BIND)
    parser.add_argument("--port", type=int, default=DEMO_PORT)
    args = parser.parse_args()
    refused = demo_cli_error(bind=args.bind, host=args.host, port=args.port)
    if refused:
        raise SystemExit(refused)
    import uvicorn

    uvicorn.run(create_demo_app(), host=args.host, port=args.port, log_level="warning")
