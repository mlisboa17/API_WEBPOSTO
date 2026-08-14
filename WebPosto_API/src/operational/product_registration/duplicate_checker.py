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
        "DE", "DA", "DO", "DOS", "DAS", "COM", "C", "SEM", "S", "E", "EM", "P", "PARA",
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


SAME_PRODUCT_NEW_GTIN = "SAME_PRODUCT_NEW_GTIN"
POSSIBLE_VARIANT = "POSSIBLE_VARIANT"
FALSE_POSITIVE = "FALSE_POSITIVE"

# Fator de conversão para a unidade base de cada grandeza.
MASS_UNITS = {"G": 1.0, "GR": 1.0, "GRS": 1.0, "KG": 1000.0}
VOLUME_UNITS = {"ML": 1.0, "L": 1000.0, "LT": 1000.0, "LTS": 1000.0, "LITRO": 1000.0}

MEASURE_PATTERN = re.compile(
    r"(?<![A-Z0-9])(\d+(?:[.,]\d+)?)\s*(KG|GRS|GR|G|ML|LTS|LT|LITRO|L)(?![A-Z0-9])"
)
# Embalagem múltipla ("70X130G", "12 X 500ML") descreve o fardo, não a unidade de venda.
PACK_PATTERN = re.compile(r"(?<![A-Z0-9])(\d+)\s*X\s*(\d+(?:[.,]\d+)?)\s*(KG|GR|G|ML|LT|L)(?![A-Z0-9])")


def extract_measure(description: str) -> tuple[float, str] | None:
    """Conteúdo declarado na descrição, convertido para grama ou mililitro.

    Devolve None quando a descrição não declara medida: ausência não é zero e não pode
    ser tratada como medida coincidente.
    """
    text = _strip_accents(str(description or "")).upper().replace(",", ".")
    pack = PACK_PATTERN.search(text)
    if pack:
        amount, unit = float(pack.group(2)), pack.group(3)
    else:
        found = MEASURE_PATTERN.search(text)
        if not found:
            return None
        amount, unit = float(found.group(1)), found.group(2)
    if unit in MASS_UNITS:
        return amount * MASS_UNITS[unit], "G"
    if unit in VOLUME_UNITS:
        return amount * VOLUME_UNITS[unit], "ML"
    return None


def classify_duplicate(
    candidate_description: str,
    existing_description: str,
    *,
    candidate_family: str | None = None,
    existing_family: str | None = None,
) -> tuple[str, str]:
    """Classifica um par retido pela busca por descrição.

    A medida serve para confirmar, nunca para presumir: par sem medida nos dois lados
    fica como variante possível, para decisão humana, e não como produto confirmado.
    """
    if candidate_family and existing_family and candidate_family != existing_family:
        return FALSE_POSITIVE, (
            f"Famílias comerciais diferentes: {candidate_family} e {existing_family}"
        )

    candidate_tokens = distinctive_tokens(candidate_description)
    existing_tokens = distinctive_tokens(existing_description)
    extra = existing_tokens - candidate_tokens
    candidate_measure = extract_measure(candidate_description)
    existing_measure = extract_measure(existing_description)

    # Conteúdo diferente é o motivo mais objetivo, por isso vem antes do qualificador.
    if candidate_measure and existing_measure:
        if candidate_measure[1] != existing_measure[1]:
            return POSSIBLE_VARIANT, (
                f"Grandezas diferentes: {candidate_measure[1]} e {existing_measure[1]}"
            )
        if abs(candidate_measure[0] - existing_measure[0]) > 0.01:
            return POSSIBLE_VARIANT, (
                f"Conteúdo diferente: {candidate_measure[0]:g}{candidate_measure[1]} "
                f"e {existing_measure[0]:g}{existing_measure[1]}"
            )
    if extra:
        return POSSIBLE_VARIANT, (
            "Cadastro existente traz qualificador ausente no candidato: "
            f"{', '.join(sorted(extra))}"
        )
    if candidate_measure is None or existing_measure is None:
        missing = "candidato" if candidate_measure is None else "cadastro existente"
        return POSSIBLE_VARIANT, f"Medida não declarada no {missing}; duplicidade não confirmável"
    return SAME_PRODUCT_NEW_GTIN, (
        f"Mesmos termos e mesmo conteúdo ({candidate_measure[0]:g}{candidate_measure[1]}); "
        "difere apenas o código de barras"
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
