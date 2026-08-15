"""Gateway e verificacao independente do endpoint legado."""

from __future__ import annotations

import time
from typing import Any, Protocol

import httpx

LEGACY_ENDPOINT = "/INTEGRACAO/INCLUIR_PRODUTO"
DEFAULT_TIMEOUT = 120.0


class CatalogReader(Protocol):
    def get_catalog(self, key: str, cursor: int, page_size: int) -> list[dict[str, Any]]: ...

    def get_company_links(self, key: str, cursor: int, page_size: int) -> list[dict[str, Any]]: ...


class WebPostoRegistrationGateway:
    """POST /INTEGRACAO/INCLUIR_PRODUTO com CHAVE_ONLY. Sem retry cego."""

    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def post_once(self, client: httpx.Client, key: str, body: dict[str, Any]) -> httpx.Response:
        if "empresaCodigo" in body:
            raise ValueError("empresaCodigo e proibido no body do endpoint legado")
        return client.post(
            f"{self.base_url}{LEGACY_ENDPOINT}",
            params={"CHAVE": key},
            content=__import__("json").dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    def wait_retry_after(self, response: httpx.Response, default: float = 5.0) -> float:
        header = response.headers.get("Retry-After", "").strip()
        try:
            return min(max(float(header), 1.0), 60.0)
        except ValueError:
            return default


class ProductPostVerifier:
    """GET independente. Nao reutiliza a resposta do POST."""

    def __init__(self, reader: CatalogReader, empresa: int) -> None:
        self.reader = reader
        self.empresa = empresa

    def verify(
        self,
        key: str,
        *,
        produto_codigo: int,
        ean: str,
        expected_ncm: str,
        expected_cest: str | None,
        expected_sale: float,
        expected_cost: float,
    ) -> dict[str, Any]:
        links = self.reader.get_company_links(key, cursor=produto_codigo - 1, page_size=50)
        matching = [row for row in links if int(row.get("produtoCodigo") or 0) == produto_codigo]
        company_link = next(
            (row for row in matching if int(row.get("empresaCodigo") or 0) == self.empresa),
            None,
        )
        rows = self.reader.get_catalog(key, cursor=produto_codigo - 1, page_size=50)
        created = next((row for row in rows if int(row.get("produtoCodigo") or 0) == produto_codigo), None)
        divergences: list[str] = []
        if not company_link:
            return {
                "ok": False,
                "classification": "CREATED_IN_WRONG_COMPANY" if matching else "ORPHANED_SHARED_CATALOG_RECORD",
                "divergences": ["empresa"],
            }
        if abs(float(company_link.get("precoVenda") or 0) - expected_sale) > 0.005:
            divergences.append("precoVenda")
        if abs(float(company_link.get("precoCusto") or 0) - expected_cost) > 0.005:
            divergences.append("precoCusto")
        if not company_link.get("ativo"):
            divergences.append("ativo")
        if created and str(created.get("ncm") or "") != str(expected_ncm):
            divergences.append("ncm")
        if created and str(created.get("cest") or "") != str(expected_cest or ""):
            divergences.append("cest")
        barcodes = {
            str((item.get("codigoBarra") if isinstance(item, dict) else item) or "").strip()
            for item in (created or {}).get("produtoCodigoBarra") or []
        }
        if created and created.get("produtoCodigoExterno"):
            barcodes.add(str(created["produtoCodigoExterno"]).strip())
        if created and ean not in barcodes:
            divergences.append("codigoBarras")
        return {
            "ok": not divergences,
            "classification": "CREATED_AND_VERIFIED" if not divergences else "DIVERGENCIA_POS_POST",
            "divergences": divergences,
            "empresa": int(company_link.get("empresaCodigo") or 0),
            "produtoCodigo": produto_codigo,
            "referencia": (created or {}).get("referenciaCodigo"),
            "ativo": company_link.get("ativo"),
        }


def sleep_retry_after(seconds: float) -> None:
    time.sleep(seconds)
