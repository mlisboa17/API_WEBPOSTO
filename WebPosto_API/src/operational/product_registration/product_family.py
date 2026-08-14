"""Classificacao de familia fiscal por descricao de produto.

Fonte unica usada pelo gerador de bases candidatas e pela matriz tributaria, para que
os dois nao divirjam. A familia e apenas um agrupamento para buscar evidencia; ela
nao define tributacao por si.
"""

from __future__ import annotations

import re
import unicodedata

BISCOITOS = "BISCOITOS"
AMENDOINS = "AMENDOINS"
SALGADINHOS_INDUSTRIALIZADOS = "SALGADINHOS_INDUSTRIALIZADOS"
CHIPS_BANANA = "CHIPS_BANANA"
CHIPS_BATATA_DOCE = "CHIPS_BATATA_DOCE"
CHIPS_MACAXEIRA = "CHIPS_MACAXEIRA"
CHIPS_OUTROS = "CHIPS_OUTROS"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


def family(description: str) -> str:
    """Agrupa a descricao numa familia fiscal candidata.

    A ordem importa: batata-doce e macaxeira precisam ser testadas antes de batata
    frita industrializada, senao caem em salgadinhos.
    """
    text = normalize(description)

    if "BANANA" in text:
        return CHIPS_BANANA
    if "BATATA DOCE" in text:
        return CHIPS_BATATA_DOCE
    if "MACAXEIRA" in text or "AIPIM" in text or "MANDIOCA" in text:
        return CHIPS_MACAXEIRA
    if "AMENDOIM" in text or "MENDORATO" in text:
        return AMENDOINS
    if "BISCOITO" in text or "TRAKINAS" in text or "COOKIE" in text or "WAFER" in text:
        return BISCOITOS
    if any(
        word in text
        for word in (
            "RUFFLES",
            "CEBOLITOS",
            "SALGADINHO",
            "PIPPOS",
            "CROCANTISSIMO",
            "DORITOS",
            "FANDANGOS",
            "CHEETOS",
            "BATATA",
        )
    ):
        return SALGADINHOS_INDUSTRIALIZADOS
    return CHIPS_OUTROS
