"""
Verifica WEBPOSTO_BEARER_TOKEN contra a API (sem imprimir o segredo completo).
Uso: na raiz do projeto, python scripts/verify_webposto_token.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Raiz do projeto (pai de scripts/)
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)


def _mask_secret(value: str, head: int = 4, tail: int = 4) -> str:
    if not value:
        return "(vazio)"
    if len(value) <= head + tail:
        return "***"
    return f"{value[:head]}...{value[-tail:]}"


async def main() -> int:
    import httpx

    from config import webposto

    base = (webposto.BASE_URL or "").strip().rstrip("/")
    token = (webposto.BEARER_TOKEN or "").strip()

    print("=== Verificação WebPosto (.env) ===")
    print(f"BASE_URL: {base or '(não definida)'}")
    print(f"TOKEN (mascarado): {_mask_secret(token)}")
    print(f"Health path: {webposto.ENDPOINT_V1_HEALTH}")

    if not base:
        print("\nRESULTADO: FALHA — defina WEBPOSTO_BASE_URL no .env")
        return 1

    if not token or token.lower() in (
        "seu_bearer_token_aqui",
        "changeme",
        "placeholder",
    ):
        print(
            "\nRESULTADO: FALHA — WEBPOSTO_BEARER_TOKEN ausente ou ainda é placeholder"
        )
        return 1

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    path = (
        webposto.ENDPOINT_V1_HEALTH
        if webposto.ENDPOINT_V1_HEALTH.startswith("/")
        else f"/{webposto.ENDPOINT_V1_HEALTH}"
    )

    try:
        async with httpx.AsyncClient(
            base_url=base, headers=headers, timeout=30.0
        ) as client:
            r = await client.get(path)
    except httpx.ConnectError as e:
        print(f"\nRESULTADO: FALHA — não conectou em {base}: {e}")
        return 3
    except httpx.TimeoutException:
        print("\nRESULTADO: FALHA — timeout ao contatar o WebPosto")
        return 4

    snippet = (r.text or "")[:300].replace("\n", " ")
    print(f"\nHTTP {r.status_code} em GET {path}")
    if snippet:
        print(f"Corpo (trecho): {snippet}")

    if r.status_code == 200:
        print("\nRESULTADO: OK — token aceito (200 no health)")
        return 0

    if r.status_code in (401, 403):
        print("\nRESULTADO: FALHA — token inválido ou sem permissão (401/403)")
        return 2

    if r.status_code == 404:
        print(
            "\nRESULTADO: INCERTO — path de health não encontrado (404). "
            "O token pode estar correto; ajuste WEBPOSTO_V1_HEALTH no .env se necessário."
        )
        return 5

    print(
        f"\nRESULTADO: ATENÇÃO — resposta inesperada ({r.status_code}); confira URL e rotas da API"
    )
    return 6


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
