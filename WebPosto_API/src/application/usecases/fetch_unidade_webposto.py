"""Contexto da unidade (posto) vinculada à chave WebPosto."""

from __future__ import annotations

from typing import Any, Optional

from src.domain.catalog.grupo_schema import UnidadeWebPosto


def _mascarar_chave(chave: str) -> str:
    c = (chave or "").strip()
    if len(c) >= 12:
        return f"{c[:4]}…{c[-4:]}"
    return "—"


async def fetch_unidade_webposto(
    webposto_client: Any,
    *,
    base_url: str = "",
    chave: str = "",
) -> UnidadeWebPosto:
    """GET /INTEGRACAO/EMPRESAS — identifica qual posto a chave está consultando."""
    fantasia = ""
    razao = ""
    cnpj = ""
    empresa_codigo: Optional[int] = None

    try:
        import asyncio
        raw = await asyncio.to_thread(webposto_client._http.get, "/INTEGRACAO/EMPRESAS", {})
        rows = raw if isinstance(raw, list) else (raw.get("resultados") or []) if isinstance(raw, dict) else []
        if rows and isinstance(rows[0], dict):
            row = rows[0]
            empresa_codigo = row.get("empresaCodigo") or row.get("codigo")
            if empresa_codigo is not None:
                empresa_codigo = int(empresa_codigo)
            fantasia = str(row.get("fantasia") or row.get("nomeFantasia") or "").strip()
            razao = str(row.get("razao") or row.get("razaoSocial") or "").strip()
            cnpj = str(row.get("cnpj") or "").strip()
    except Exception:
        pass

    if not fantasia and not razao:
        fantasia = "Unidade não identificada"
        razao = "Verifique WEBPOSTO_API_KEY no .env"

    return UnidadeWebPosto(
        empresa_codigo=empresa_codigo,
        fantasia=fantasia,
        razao_social=razao,
        cnpj=cnpj,
        base_url=base_url.rstrip("/"),
        chave_mascarada=_mascarar_chave(chave),
    )
