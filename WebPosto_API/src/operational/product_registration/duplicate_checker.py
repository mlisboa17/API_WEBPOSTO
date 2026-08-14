"""Verificação de duplicidade (ativos + inativos) — FASE 5."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .schemas import ProductAnalysis

# Palavras que não distinguem uma mercadoria de outra: ligação, embalagem e marcação
# comercial. "NOVO" costuma indicar troca de código de barras do mesmo produto.
GENERIC_TOKENS = frozenset(
    {
        "DE", "DA", "DO", "DOS", "DAS", "COM", "SEM", "E", "EM", "P", "PARA",
        "SABOR", "SABORES", "NOVO", "NOVA", "UN", "UNI", "UND", "PC", "PCT", "PACOTE",
        "CX", "CAIXA", "DP", "FD", "FARDO", "KG", "G", "GR", "ML", "L", "LT", "LATA",
        "SALG", "REF", "TIPO",
    }
)

# Token que expressa apenas peso, volume ou multiplicação de embalagem.
SIZE_TOKEN = re.compile(r"^\d+([.,]\d+)?(G|GR|KG|ML|L|LT|UN|UNI|X\d+)?$|^\d+X\d+")


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def distinctive_tokens(description: str) -> frozenset[str]:
    """Extrai os termos que realmente identificam a mercadoria.

    Remove ligação, embalagem e medidas, de modo que "SALG PINGO OURO PICANHA 55G NOVO"
    e "PINGO DE OURO PICANHA" produzam o mesmo conjunto.
    """
    text = _strip_accents(str(description or "")).upper()
    tokens = re.split(r"[^A-Z0-9]+", text)
    return frozenset(
        token
        for token in tokens
        if token and token not in GENERIC_TOKENS and not SIZE_TOKEN.match(token)
    )


def find_description_duplicates(
    description: str,
    products: list[dict[str, Any]],
    *,
    name_key: str = "nome",
    min_tokens: int = 2,
) -> list[dict[str, Any]]:
    """Produtos do catálogo que já representam a mesma mercadoria.

    O critério é conter todos os termos distintivos da descrição procurada. Sabor ou
    variante diferente sobra um termo e não casa, então "COOKIES AMORA" não colide com
    "COOKIES TRADICIONAL". Descrição curta demais não é comparada, para não gerar
    bloqueio por coincidência.
    """
    wanted = distinctive_tokens(description)
    if len(wanted) < min_tokens:
        return []
    return [
        product
        for product in products
        if wanted <= distinctive_tokens(product.get(name_key) or "")
    ]


class DuplicateChecker:
    """Verifica se EAN já existe em produtos ativos/inativos."""

    def __init__(
        self,
        active_products: dict[str, dict[str, Any]] | None = None,
        inactive_products: dict[str, dict[str, Any]] | None = None,
    ):
        self.active_products = active_products or {}
        self.inactive_products = inactive_products or {}

    def find_duplicate(self, ean: str) -> dict[str, Any] | None:
        """Retorna produto ativo ou inativo com o EAN, ou None."""
        ean_normalized = str(ean).strip()
        
        # Buscar em ativos
        if ean_normalized in self.active_products:
            return {
                "status": "ACTIVE",
                **self.active_products[ean_normalized],
            }
        
        # Buscar em inativos
        if ean_normalized in self.inactive_products:
            return {
                "status": "INACTIVE",
                **self.inactive_products[ean_normalized],
            }
        
        return None

    def check_and_update_analysis(
        self,
        analysis: ProductAnalysis,
    ) -> ProductAnalysis:
        """Atualiza análise com resultado de duplicidade."""
        duplicate = self.find_duplicate(analysis.ean)
        
        if duplicate:
            status = duplicate.get("status")
            if status == "ACTIVE":
                analysis.status = "BLOCKED"
                analysis.gate = "BLOCKED_ALREADY_REGISTERED_ACTIVE"
                analysis.validation_issues.append(
                    f"EAN {analysis.ean} já registrado como ativo: "
                    f"produtoCodigo={duplicate.get('produtoCodigo')}"
                )
                analysis.risk_level = "ALTO_RISCO"
            else:  # INACTIVE
                analysis.status = "REVIEW_REQUIRED"
                analysis.validation_issues.append(
                    f"EAN {analysis.ean} encontrado como inativo: "
                    f"produtoCodigo={duplicate.get('produtoCodigo')} — "
                    "verificar se deve reativar ou criar novo"
                )
                analysis.risk_level = "MÉDIO_RISCO"
        
        return analysis
