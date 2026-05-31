"""
Sandbox de testes contra a API WebPosto real (CHAVE via env).
Uso: python -m src.infrastructure.clients.test_api_sandbox
"""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

ENDPOINTS = [
    ("/INTEGRACAO/EMPRESAS", {}),
    ("/INTEGRACAO/PRODUTO", {"pagina": 0, "tamanhoPagina": 3}),
    ("/INTEGRACAO/VENDA", {"pagina": 0, "tamanhoPagina": 3}),
    ("/INTEGRACAO/ABASTECIMENTO", {"pagina": 0, "tamanhoPagina": 3}),
]


async def main() -> int:
    from src.infrastructure.clients.posto_client_v1 import PostoAPIClient
    key = os.getenv("WEBPOSTO_API_KEY", "").strip()
    base = os.getenv("WEBPOSTO_BASE_URL", "").strip().rstrip("/")
    if "qualityautomacao.com.br" in base.lower() and base.lower().startswith("http://"):
        base = "https://web.qualityautomacao.com.br"
    if not key:
        print("WEBPOSTO_API_KEY ausente no .env")
        return 1

    client = PostoAPIClient(base, key)
    ok = 0
    for path, extra in ENDPOINTS:
        try:
            data = await client._get_json(path, extra)
            n = len(data) if isinstance(data, list) else "obj"
            print(f"OK  {path} -> {n}")
            ok += 1
        except PermissionError as e:
            print(f"401 {path} -> {e}")
        except Exception as e:
            print(f"ERR {path} -> {e}")

    print(f"\n{ok}/{len(ENDPOINTS)} endpoints OK")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
