from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
from time import perf_counter
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.infrastructure.bootstrap import (
    ensure_vip_tenant_from_env,
    load_environment,
    schedule_initial_vip_sync_task,
)
from src.infrastructure.database import init_db
from src.presentation.crud_routes import router as crud_router
from src.presentation.routes import router


API_PORT = 8050
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle hook."""
    load_environment()
    await init_db()
    await ensure_vip_tenant_from_env()
    app.state.vip_initial_sync_task = schedule_initial_vip_sync_task()
    yield


app = FastAPI(
    title="Logos WebPosto Gateway",
    version="1.0.0",
    description="API Gateway unificada para integração com WebPosto (Porta 8050)",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    started = perf_counter()
    response = await call_next(request)
    duration_ms = round((perf_counter() - started) * 1000, 3)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
            },
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "internal_server_error",
            },
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

app.include_router(router)
app.include_router(crud_router)


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", str(API_PORT))),
        reload=True,
    )
