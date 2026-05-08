"""
Diagnostico completo do erro 403 - ver body, headers e tentar HTTPS
"""

import httpx
import asyncio

API_KEY = "<WEBPOSTO_API_TOKEN>"


async def testar(url, params=None, headers_extra=None):
    h = {"Accept": "application/json", "Content-Type": "application/json"}
    if headers_extra:
        h.update(headers_extra)
    try:
        async with httpx.AsyncClient(verify=False) as c:
            r = await c.get(
                url, params=params, headers=h, timeout=15, follow_redirects=True
            )
            print(f"\n{'='*50}")
            print(f"URL:     {r.url}")
            print(f"STATUS:  {r.status_code}")
            print(f"HEADERS: {dict(r.headers)}")
            print(f"BODY:    {r.text[:1000]}")
    except Exception as e:
        print(f"\n{'='*50}")
        print(f"URL:   {url}")
        print(f"ERRO:  {e}")


async def main():
    print("\n🔍 DIAGNOSTICO COMPLETO DO 403\n")

    # 1. HTTP com CHAVE
    await testar("http://web.qualityautomacao.com.br/", {"CHAVE": API_KEY})

    # 2. HTTPS com CHAVE
    await testar("https://web.qualityautomacao.com.br/", {"CHAVE": API_KEY})

    # 3. SEM chave - ver se muda o erro
    await testar("http://web.qualityautomacao.com.br/")

    # 4. Com chave no Header X-API-Key
    await testar(
        "http://web.qualityautomacao.com.br/", headers_extra={"X-API-Key": API_KEY}
    )

    # 5. Com chave no Header Authorization Basic
    import base64

    basic = base64.b64encode(f"{API_KEY}:".encode()).decode()
    await testar(
        "http://web.qualityautomacao.com.br/",
        headers_extra={"Authorization": f"Basic {basic}"},
    )


asyncio.run(main())
