"""
Servidor leve: interface HTML + proxy para API WebPosto (sem Postgres/Redis).

Uso (na raiz do projeto):
  pip install fastapi uvicorn httpx pydantic
  python explorador_standalone.py

Abra http://127.0.0.1:8765/  (painel amigável)

Rotas de página:
  /       → painel_webposto.html (consultas rápidas; usa WEBPOSTO_API_KEY do .env)
  /tecnico → explorador_tecnico.html (JSON, catálogo completo, POST/PUT)

Configure WEBPOSTO_API_KEY e WEBPOSTO_BASE_URL no .env (HTTPS para qualityautomacao.com.br).
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from explorador_catalog import ENDPOINTS

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
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
    return (os.environ.get(key) or default).strip()


def normalize_base(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    low = u.lower()
    if "qualityautomacao.com.br" in low and low.startswith("http://"):
        return "https://web.qualityautomacao.com.br"
    return u or "https://web.qualityautomacao.com.br"


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
    chave: Optional[str] = Field(
        None, description="Sobrescreve WEBPOSTO_API_KEY do .env"
    )
    base_url: Optional[str] = None
    method: str = "GET"
    path: str
    query: Dict[str, Any] = Field(default_factory=dict)
    json_body: Optional[Any] = None


app = FastAPI(title="WebPosto Explorador", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/explorer/catalog")
async def catalog():
    return {"endpoints": ENDPOINTS, "total": len(ENDPOINTS)}


@app.get("/api/explorer/config")
async def explorer_config():
    """Indica se há chave no .env (sem expor a chave completa)."""
    k = (_env("WEBPOSTO_API_KEY") or _env("WEBPOSTO_CHAVE") or "").strip()
    ph = "sua_chave_api_rest_aqui"
    valid = bool(k and k != ph)
    hint: Optional[str] = None
    if valid and len(k) >= 12:
        hint = f"{k[:4]}…{k[-4:]}"
    return {
        "has_key": valid,
        "key_hint": hint,
        "base_url": normalize_base(
            _env("WEBPOSTO_BASE_URL", "https://web.qualityautomacao.com.br")
        ),
    }


@app.get("/api/explorer/stats")
async def stats():
    g = sum(1 for e in ENDPOINTS if e.get("method") == "GET")
    p = sum(1 for e in ENDPOINTS if e.get("method") == "POST")
    u = sum(1 for e in ENDPOINTS if e.get("method") == "PUT")
    pa = sum(1 for e in ENDPOINTS if e.get("method") == "PATCH")
    d = sum(1 for e in ENDPOINTS if e.get("method") == "DELETE")
    return {
        "total": len(ENDPOINTS),
        "get": g,
        "post": p,
        "put": u,
        "patch": pa,
        "delete": d,
        "categorias": sorted({e["categoria"] for e in ENDPOINTS}),
    }


@app.post("/api/explorer/proxy")
async def proxy(req: ProxyBody):
    chave = (
        req.chave or _env("WEBPOSTO_API_KEY") or _env("WEBPOSTO_CHAVE") or ""
    ).strip()
    if not chave or chave == "sua_chave_api_rest_aqui":
        raise HTTPException(
            status_code=400,
            detail="Informe a CHAVE na tela ou configure WEBPOSTO_API_KEY no arquivo .env",
        )

    base = normalize_base(
        req.base_url or _env("WEBPOSTO_BASE_URL", "https://web.qualityautomacao.com.br")
    )
    path = req.path if req.path.startswith("/") else f"/{req.path}"
    url = f"{base}{path}"
    method = req.method.upper().strip()
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        raise HTTPException(status_code=400, detail="Método HTTP não suportado")

    params = merge_query(chave, req.query)
    verify = False if base.lower().startswith("https") else True
    timeout = httpx.Timeout(120.0, connect=30.0)
    t0 = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=timeout, verify=verify) as client:
            if method == "GET":
                r = await client.get(url, params=params)
            elif method == "POST":
                r = await client.post(url, params=params, json=req.json_body)
            elif method == "PUT":
                r = await client.put(url, params=params, json=req.json_body)
            elif method == "PATCH":
                r = await client.patch(url, params=params, json=req.json_body)
            else:
                r = await client.delete(url, params=params)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Erro de rede: {e!s}") from e

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    ct = r.headers.get("content-type", "")
    body: Any
    if "json" in ct:
        try:
            body = r.json()
        except Exception:
            body = r.text
    else:
        body = r.text[:50000] if r.text else None

    return {
        "status_code": r.status_code,
        "elapsed_ms": elapsed_ms,
        "content_type": ct,
        "url_requested": str(r.request.url),
        "body": body,
    }


@app.get("/", response_class=HTMLResponse)
async def root():
    index = STATIC / "painel_webposto.html"
    if not index.is_file():
        return HTMLResponse(
            "<h1>Arquivo static/painel_webposto.html não encontrado.</h1>",
            status_code=500,
        )
    return FileResponse(index, media_type="text/html; charset=utf-8")


@app.get("/tecnico", response_class=HTMLResponse)
async def tecnico():
    """Explorador técnico (JSON, POST/PUT) — mantido para testes."""
    path = STATIC / "explorador_tecnico.html"
    if not path.is_file():
        return HTMLResponse(
            "<h1>static/explorador_tecnico.html não encontrado.</h1>", status_code=500
        )
    return FileResponse(path, media_type="text/html; charset=utf-8")


def _root_html(filename: str) -> FileResponse:
    p = ROOT / filename
    if not p.is_file():
        raise HTTPException(
            status_code=404, detail=f"Arquivo nao encontrado: {filename}"
        )
    return FileResponse(p, media_type="text/html; charset=utf-8")


@app.get("/app/vendas", response_class=HTMLResponse)
async def app_dashboard_vendas():
    return _root_html("dashboard_vendas.html")


@app.get("/app/abastecimento", response_class=HTMLResponse)
async def app_dashboard_abastecimento():
    return _root_html("dashboard_abastecimento.html")


@app.get("/app/despesas", response_class=HTMLResponse)
async def app_dashboard_despesas():
    return _root_html("dashboard_demo.html")


@app.get("/app/filtros", response_class=HTMLResponse)
async def app_dashboard_filtros():
    return _root_html("dashboard_filtros.html")


@app.get("/app/landing", response_class=HTMLResponse)
async def app_landing():
    return _root_html("index.html")


if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


def _pick_port(preferred: int) -> tuple[int, str]:
    """
    Escolhe uma porta livre em 127.0.0.1.
    Evita WinError 10048 (WSAEADDRINUSE) quando 8765 já está em uso.
    """
    import socket

    for delta in range(0, 30):
        port = preferred + delta
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                msg = (
                    f"Abra http://127.0.0.1:{port}/"
                    if port == preferred
                    else f"Porta {preferred} ocupada - abra http://127.0.0.1:{port}/"
                )
                return port, msg
            except OSError:
                continue
    raise RuntimeError(
        f"Nenhuma porta livre entre {preferred} e {preferred + 29}. "
        "Feche o processo que usa a porta ou defina EXPLORADOR_PORT no .env."
    )


def main():
    import uvicorn

    preferred = int(_env("EXPLORADOR_PORT", "8765") or "8765")
    port, hint = _pick_port(preferred)
    print("\n  WebPosto Explorador")
    print(f"  -> {hint}\n")
    uvicorn.run(
        "explorador_standalone:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
