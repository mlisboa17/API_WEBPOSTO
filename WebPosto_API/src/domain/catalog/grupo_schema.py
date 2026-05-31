"""Schemas de grupos de produto e contexto da unidade WebPosto."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class UnidadeWebPosto(BaseModel):
    """Posto/empresa vinculado à chave de integração (GET /INTEGRACAO/EMPRESAS)."""

    model_config = ConfigDict(frozen=True)

    empresa_codigo: Optional[int] = None
    fantasia: str = ""
    razao_social: str = ""
    cnpj: str = ""
    base_url: str = ""
    chave_mascarada: str = ""


class ProdutoGrupoItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    codigo: int
    nome: str
    qtd_produtos: int = 0
    codigos_produto: List[str] = Field(default_factory=list)


class GruposProdutoResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    unidade: Optional[UnidadeWebPosto] = None
    total_grupos: int = 0
    total_grupos_sistema: int = 0
    grupos_com_produtos_catalogo: int = 0
    total_produtos_indexados: int = 0
    grupos: List[ProdutoGrupoItem] = Field(default_factory=list)
    fonte: str = "webposto_integracao"
    cache_hit: bool = False
