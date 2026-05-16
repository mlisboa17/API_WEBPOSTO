"""
Entrypoint FastAPI unificado — proxy WebPosto, cache Valkey, rotas legadas e UI Lionda.

Uso:
  python src/presentation/app.py
  # ou: uvicorn src.presentation.app:app --host 0.0.0.0 --port 8765
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.application.usecases.fetch_executive_kpis import (
    FetchExecutiveKpisRequest,
    fetch_executive_kpis,
    periodo_preset,
)
from src.infrastructure.cache.valkey_manager import get_cache
from src.infrastructure.config.settings import settings
from src.shared.logger import setup_logging

ROOT = _ROOT
THEME_DIR = ROOT / "theme"
ENV_PATH = ROOT / ".env"


def _load_dotenv() -> None:
    if not ENV_PATH.is_file():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line.strip())
        if m and m.group(1) not in os.environ:
            os.environ[m.group(1)] = m.group(2).strip().strip('"').strip("'")


_load_dotenv()


def _env(key: str, default: str = "") -> str:
    return (os.environ.get(key) or getattr(settings, key.lower(), None) or default).strip()


def normalize_base(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if "qualityautomacao.com.br" in u.lower() and u.lower().startswith("http://"):
        return "https://web.qualityautomacao.com.br"
    return u or "https://web.qualityautomacao.com.br"


_INVALID_CHAVES = frozenset(
    {"", "sua_chave_api_rest_aqui", "SEU_TOKEN_AQUI", "__from_env__"}
)


def _resolve_chave(override: Optional[str] = None) -> str:
    """Chave do body/query ou fallback .env — ignora placeholders inválidos."""
    c = (override or "").strip()
    if c in _INVALID_CHAVES or (c.startswith("__") and c.endswith("__")):
        c = ""
    if c:
        return c
    return (
        _env("WEBPOSTO_API_KEY")
        or _env("WEBPOSTO_CHAVE")
        or (settings.webposto_api_key or "")
    ).strip()


def merge_query(chave: str, query: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    params: Dict[str, Any] = {"CHAVE": chave}
    if not query:
        return params
    for k, v in query.items():
        if v is None or v == "":
            continue
        if isinstance(v, str) and k in ("filial", "produto") and "," in v:
            params[k] = [x.strip() for x in v.split(",") if x.strip()]
        else:
            params[k] = v
    return params


class ProxyBody(BaseModel):
    chave: Optional[str] = None
    path: str
    query: Dict[str, Any] = Field(default_factory=dict)
    method: str = "GET"
    json_body: Optional[Any] = None
    use_cache: bool = True


class ExecutiveSummary(BaseModel):
    """Cockpit executivo Logos Space — Adelaide Tax Engine."""

    faturamento_bruto: Decimal = Decimal("0")
    galonagem_total: Decimal = Decimal("0")
    credito_recuperavel: Decimal = Decimal("0")
    despesas_caixa: Decimal = Decimal("0")
    margem_liquida_real: Decimal = Decimal("0")
    periodo: str = "30D"
    fallback: bool = False
    mensagem: Optional[str] = None
    combustiveis: List[Dict[str, Any]] = Field(default_factory=list)


def create_unified_app() -> FastAPI:
    setup_logging(settings.log_level, settings.log_format)
    app = FastAPI(
        title="Logos WebPosto Gateway",
        version="2026.1",
        description="Proxy Quality · Adelaide · dashboards executivos",
    )
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for mod_name in ("auth", "metrics", "clientes", "sync"):
        try:
            mod = __import__(
                f"src.interfaces.http.routes.{mod_name}",
                fromlist=["router"],
            )
            app.include_router(mod.router)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                "Rota %s não carregada: %s", mod_name, exc
            )

    try:
        from src.routes_crud import router as crud_router

        app.include_router(crud_router)
    except Exception:
        pass

    # Auditoria (Mongo) — opcional
    try:
        from src.interfaces.http.routes import auditoria

        app.include_router(auditoria.router)
    except Exception:
        pass

    cache = get_cache()

    @app.get("/health", tags=["gateway"])
    def gateway_health():
        chave = _resolve_chave()
        if not chave:
            return {
                "status": "attention",
                "database": "connected",
                "api_key": "missing_in_env",
            }
        return {
            "status": "healthy",
            "database": "connected",
            "api_key": "active",
        }

    @app.get("/dashboard", response_class=HTMLResponse, tags=["gateway"])
    async def dashboard_executivo():
        p = ROOT / "static" / "dashboard_logos.html"
        if not p.is_file():
            raise HTTPException(404, "static/dashboard_logos.html não encontrado")
        return FileResponse(p, media_type="text/html; charset=utf-8")

    @app.get("/api/v1/proxy/{endpoint:path}", tags=["gateway"])
    async def webposto_proxy_v1(
        endpoint: str,
        request: Request,
        api_key: Optional[str] = Query(None, alias="api_key"),
    ):
        """Proxy reverso GET — CHAVE na query WebPosto (não Bearer)."""
        chave = _resolve_chave(api_key)
        if not chave:
            raise HTTPException(
                status_code=401,
                detail="Chave de integração WebPosto não informada.",
            )

        path = endpoint.strip()
        if not path.startswith("/"):
            path = f"/{path}"
        if not path.upper().startswith("/INTEGRACAO"):
            path = f"/INTEGRACAO/{path.lstrip('/')}"

        fwd: Dict[str, Any] = dict(request.query_params)
        fwd.pop("api_key", None)

        base = normalize_base(_env("WEBPOSTO_BASE_URL", settings.webposto_base_url))
        url = f"{base}{path}"
        params = merge_query(chave, fwd)
        t0 = time.perf_counter()

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=20.0), verify=True
            ) as client:
                response = await client.get(url, params=params)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Rede: {exc!s}") from exc

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        if response.status_code != 200:
            detail = response.text[:500] if response.text else "Erro na API Quality"
            raise HTTPException(status_code=response.status_code, detail=detail)

        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}

        return {
            "status_code": response.status_code,
            "elapsed_ms": elapsed_ms,
            "data": body,
        }

    @app.get("/api/v1/adelaide/overview", response_model=ExecutiveSummary, tags=["adelaide"])
    async def get_adelaide_executive_overview(
        periodo: str = Query("30d"),
        api_key: Optional[str] = Query(None, alias="api_key"),
    ):
        from src.domain.adelaide.fiscal_catalog import list_fiscal_audit_rows

        combustiveis = list_fiscal_audit_rows()
        chave = _resolve_chave(api_key)
        if not chave:
            return ExecutiveSummary(
                fallback=True,
                mensagem="WEBPOSTO_API_KEY ausente no .env",
                combustiveis=combustiveis,
            )

        di, df, label = periodo_preset(periodo)
        try:
            from src.webposto import WebPostoClient, WebPostoConfig

            client = WebPostoClient(
                WebPostoConfig(
                    chave=chave,
                    base_url=normalize_base(
                        _env("WEBPOSTO_BASE_URL", settings.webposto_base_url)
                    ),
                    max_retries=0,
                )
            )
            resp = await fetch_executive_kpis(
                FetchExecutiveKpisRequest(
                    data_inicial=di,
                    data_final=df,
                    periodo_label=label,
                    role="director",
                ),
                client,
            )
            k = resp.kpis
            return ExecutiveSummary(
                faturamento_bruto=k.faturamento_total,
                galonagem_total=k.litros_total,
                credito_recuperavel=k.pis_cofins_total,
                despesas_caixa=k.custo_total,
                margem_liquida_real=k.margem_liquida_total,
                periodo=label,
                fallback=resp.fallback,
                mensagem=resp.mensagem,
                combustiveis=combustiveis,
            )
        except Exception as exc:
            return ExecutiveSummary(
                fallback=True,
                mensagem=str(exc),
                combustiveis=combustiveis,
            )

    @app.get("/api/config")
    async def api_config():
        k = (
            _env("WEBPOSTO_API_KEY")
            or _env("WEBPOSTO_CHAVE")
            or settings.webposto_api_key
            or ""
        ).strip()
        ph = "sua_chave_api_rest_aqui"
        valid = bool(k and k not in (ph, "SEU_TOKEN_AQUI"))
        hint = f"{k[:4]}…{k[-4:]}" if valid and len(k) >= 12 else None
        return {
            "has_key": valid,
            "key_hint": hint,
            "base_url": normalize_base(
                _env("WEBPOSTO_BASE_URL", settings.webposto_base_url)
            ),
            "cache": cache.stats(),
        }

    @app.get("/api/health/webposto")
    async def health_webposto_key():
        """Monitoramento da chave .env com try/except dedicado."""
        chave = (
            _env("WEBPOSTO_API_KEY")
            or _env("WEBPOSTO_CHAVE")
            or settings.webposto_api_key
        ).strip()
        if not chave:
            return {"ok": False, "detail": "WEBPOSTO_API_KEY ausente no .env"}
        base = normalize_base(_env("WEBPOSTO_BASE_URL", settings.webposto_base_url))
        url = f"{base}/INTEGRACAO/EMPRESAS"
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
                r = await client.get(url, params={"CHAVE": chave})
            elapsed = int((time.perf_counter() - t0) * 1000)
            return {
                "ok": r.status_code == 200,
                "status_code": r.status_code,
                "elapsed_ms": elapsed,
                "endpoint_testado": "/INTEGRACAO/EMPRESAS",
            }
        except Exception as exc:
            return {"ok": False, "detail": str(exc)}

    @app.post("/api/webposto/proxy")
    async def webposto_proxy(req: ProxyBody):
        chave = _resolve_chave(req.chave)
        if not chave:
            raise HTTPException(
                status_code=400,
                detail="Informe a CHAVE no dashboard ou configure WEBPOSTO_API_KEY no .env",
            )

        path = req.path if req.path.startswith("/") else f"/{req.path}"
        method = req.method.upper().strip()
        if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            raise HTTPException(status_code=400, detail="Método não suportado")

        ck = cache.cache_key("proxy", path, {**req.query, "m": method})
        if req.use_cache and method == "GET":
            cached = cache.get_json(ck)
            if cached is not None:
                cached["cache_hit"] = True
                return cached

        base = normalize_base(_env("WEBPOSTO_BASE_URL", settings.webposto_base_url))
        url = f"{base}{path}"
        params = merge_query(chave, req.query)
        t0 = time.perf_counter()

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=30.0), verify=True
            ) as client:
                if method == "GET":
                    r = await client.get(url, params=params)
                elif method == "POST":
                    r = await client.post(url, params=params, json=req.json_body)
                elif method == "PUT":
                    r = await client.put(url, params=params, json=req.json_body)
                else:
                    r = await client.request(
                        method, url, params=params, json=req.json_body
                    )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Rede: {exc!s}") from exc

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        ct = r.headers.get("content-type", "")
        if "json" in ct:
            try:
                body = r.json()
            except Exception:
                body = r.text
        else:
            body = r.text[:50000] if r.text else None

        payload = {
            "status_code": r.status_code,
            "elapsed_ms": elapsed_ms,
            "content_type": ct,
            "url_requested": str(r.request.url),
            "body": body,
            "cache_hit": False,
        }
        if req.use_cache and method == "GET" and r.status_code == 200:
            cache.set_json(ck, payload, ttl=60)
        return payload

    @app.get("/api/executive/kpis")
    async def executive_kpis(
        periodo: str = Query("hoje", description="hoje | 7d | 30d"),
        request: Request = None,
    ):
        role = "director"
        if request:
            token = request.cookies.get("access_token")
            if token:
                try:
                    from src.infrastructure.security.jwt_utils import decode_token

                    role = decode_token(token).get("role", "director")
                except Exception:
                    pass

        di, df, label = periodo_preset(periodo)
        try:
            from src.webposto import WebPostoClient, WebPostoConfig

            chave = (
                _env("WEBPOSTO_API_KEY")
                or _env("WEBPOSTO_CHAVE")
                or settings.webposto_api_key
            )
            client = WebPostoClient(
                WebPostoConfig(
                    chave=chave,
                    base_url=normalize_base(
                        _env("WEBPOSTO_BASE_URL", settings.webposto_base_url)
                    ),
                    max_retries=0,
                )
            )
            resp = await fetch_executive_kpis(
                FetchExecutiveKpisRequest(
                    data_inicial=di,
                    data_final=df,
                    periodo_label=label,
                    role=role,
                ),
                client,
            )
            return resp.model_dump(mode="json")
        except Exception as exc:
            from src.domain.adelaide.tax_profile import ExecutiveKpiSummary

            empty = ExecutiveKpiSummary(
                periodo=label,
                fallback=True,
                mensagem=str(exc),
            )
            return {
                "periodo": label,
                "kpis": empty.model_dump(mode="json"),
                "anomalias_caixa": [],
                "ok": False,
                "fallback": True,
                "mensagem": str(exc),
            }

    @app.get("/api/cache/stats")
    async def cache_stats():
        return cache.stats()

    # ── Frontend estático ─────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    async def dashboard_root():
        p = ROOT / "dashboard_vendas.html"
        if not p.is_file():
            raise HTTPException(404, "dashboard_vendas.html não encontrado")
        return FileResponse(p, media_type="text/html; charset=utf-8")

    @app.get("/app/vendas", response_class=HTMLResponse)
    async def dashboard_vendas():
        return await dashboard_root()

    if THEME_DIR.is_dir():
        app.mount("/theme", StaticFiles(directory=str(THEME_DIR)), name="theme")

    static = ROOT / "static"
    if static.is_dir():
        app.mount("/static", StaticFiles(directory=str(static)), name="static")

    js_catalog = ROOT / "api_hub_catalog.js"
    if js_catalog.is_file():

        @app.get("/api_hub_catalog.js")
        async def catalog_js():
            return FileResponse(js_catalog, media_type="application/javascript")

    return app


app = create_unified_app()


def main() -> None:
    import uvicorn

    port = int(
        _env("API_PORT") or _env("EXPLORADOR_PORT") or "8000"
    )
    print("\n  Logos WebPosto Gateway")
    print(f"  Health:    http://127.0.0.1:{port}/health")
    print(f"  Cockpit:   http://127.0.0.1:{port}/dashboard")
    print(f"  Operacional: http://127.0.0.1:{port}/\n")
    uvicorn.run(
        "src.presentation.app:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
