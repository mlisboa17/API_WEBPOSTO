from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from src.gateway.webposto_client import WebPostoClient
from src.models.response_model import WebPostoResponse


TTL_HOURS = 24


@dataclass
class _CacheItem:
    expires_at: datetime
    payload: dict[str, Any]


class ProdutoCatalogService:
    _cache: dict[str, _CacheItem] = {}
    _cache_version = "v2"

    def __init__(self, client: WebPostoClient) -> None:
        self.client = client

    @staticmethod
    def _rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            for key in ("resultados", "data", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]
        return []

    @staticmethod
    def _cache_key(company_codes: list[int] | None) -> str:
        prefix = ProdutoCatalogService._cache_version
        if not company_codes:
            return f"{prefix}:base"
        return f"{prefix}:" + ",".join(str(code) for code in sorted(set(company_codes)))

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _is_fresh(item: _CacheItem | None) -> bool:
        return bool(item and item.expires_at > ProdutoCatalogService._now())

    @staticmethod
    def _normalize_entry(row: dict[str, Any], source: str, company_row: dict[str, Any] | None = None) -> dict[str, Any] | None:
        code = row.get("produtoCodigo") or row.get("codigo")
        if code is None:
            return None
        try:
            code_int = int(code)
        except Exception:
            return None

        company = company_row or {}
        name = str(
            row.get("nome")
            or row.get("descricao")
            or row.get("descricaoProduto")
            or company.get("nome")
            or company.get("descricao")
            or ""
        ).strip()
        if not name or name.lower() in {"none", "null", "undefined"}:
            name = f"Produto {code_int}"
        grupo = str(row.get("nomeGrupo") or row.get("grupoProduto") or row.get("descricaoGrupo") or "").strip()
        tipo = str(row.get("tipoProduto") or row.get("produtoTipo") or "").strip()
        combustivel = bool(row.get("combustivel")) or bool(row.get("tipoCombustivel")) or tipo.upper() == "C"
        tipo_combustivel = str(row.get("tipoCombustivel") or company.get("tipoCombustivel") or "").strip()
        active = company.get("ativo") if company.get("ativo") is not None else row.get("ativo")
        raw_lmc_code = row.get("produtoLmcCodigo") or company.get("produtoLmcCodigo")
        try:
            lmc_code = int(raw_lmc_code) if raw_lmc_code is not None else None
        except Exception:
            lmc_code = None
        return {
            "produtoCodigo": code_int,
            "produtoLmcCodigo": lmc_code,
            "nomeProduto": name,
            "grupoProduto": grupo,
            "tipoProduto": tipo,
            "combustivel": combustivel,
            "tipoCombustivel": tipo_combustivel,
            "ativo": active,
            "source": source,
        }

    async def _fetch_produto_base(self) -> list[dict[str, Any]]:
        response = await self.client.call_endpoint("produto", params={})
        if not response.success:
            return []
        return self._rows(response.data)

    async def _fetch_produto_empresa(self, company_code: int) -> list[dict[str, Any]]:
        response = await self.client.call_endpoint("produto_empresa", params={"empresaCodigo": company_code})
        if not response.success:
            return []
        return self._rows(response.data)

    async def get_catalog(self, company_codes: list[int] | None = None) -> WebPostoResponse:
        key = self._cache_key(company_codes)
        cached = self._cache.get(key)
        if self._is_fresh(cached):
            return WebPostoResponse.ok(cached.payload)

        base_rows = await self._fetch_produto_base()
        by_code: dict[int, dict[str, Any]] = {}
        for row in base_rows:
            entry = self._normalize_entry(row, source="/INTEGRACAO/PRODUTO")
            if entry is None:
                continue
            by_code[entry["produtoCodigo"]] = entry

        for company_code in sorted(set(company_codes or [])):
            for row in await self._fetch_produto_empresa(company_code):
                code = row.get("produtoCodigo") or row.get("codigo")
                if code is None:
                    continue
                try:
                    code_int = int(code)
                except Exception:
                    continue
                current = by_code.get(code_int, {"produtoCodigo": code_int, "nomeProduto": ""})
                current_name = str(current.get("nomeProduto") or "").strip()
                if not current_name or current_name.lower() in {"none", "null", "undefined"}:
                    current_name = f"Produto {code_int}"
                current_lmc = current.get("produtoLmcCodigo")
                try:
                    current_lmc = int(current_lmc) if current_lmc is not None else None
                except Exception:
                    current_lmc = None
                merged = {
                    **current,
                    "produtoCodigo": code_int,
                    "produtoLmcCodigo": current_lmc,
                    "nomeProduto": current_name,
                    "ativo": row.get("ativo", current.get("ativo")),
                    "source": f"{current.get('source', '/INTEGRACAO/PRODUTO')}+/INTEGRACAO/PRODUTO_EMPRESA",
                }
                by_code[code_int] = merged

        payload = {
            "generatedAt": self._now().isoformat(),
            "ttlHours": TTL_HOURS,
            "total": len(by_code),
            "products": sorted(by_code.values(), key=lambda item: (str(item.get("nomeProduto") or ""), item["produtoCodigo"])),
        }
        self._cache[key] = _CacheItem(
            expires_at=self._now() + timedelta(hours=TTL_HOURS),
            payload=payload,
        )
        return WebPostoResponse.ok(payload)
