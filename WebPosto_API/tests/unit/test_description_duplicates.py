"""Duplicidade por descricao: EAN novo do mesmo produto nao pode gerar cadastro novo."""

from __future__ import annotations

from src.operational.product_registration.duplicate_checker import (
    distinctive_tokens,
    find_description_duplicates,
)

CATALOG = [
    {"produtoCodigo": 1802708, "nome": "PINGO DE OURO PICANHA"},
    {"produtoCodigo": 1801830, "nome": "BAUDUCCO COOKIES TRADICIONAL  60G"},
    {"produtoCodigo": 1802785, "nome": "BAUDUCCO COOKIES CHOCOLATE 100G"},
    {"produtoCodigo": 1801771, "nome": "BARRA GAROTO COOKIE 140G"},
    {"produtoCodigo": 1803067, "nome": "PINGO OURO BACON 30G"},
]


def test_packaging_and_marketing_tokens_are_ignored():
    assert distinctive_tokens("SALG PINGO OURO PICANHA 55G NOVO") == distinctive_tokens(
        "PINGO DE OURO PICANHA"
    )


def test_size_tokens_are_ignored():
    assert distinctive_tokens("BISCOITO RECHEADO 108G") == distinctive_tokens(
        "BISCOITO RECHEADO"
    )
    assert "108G" not in distinctive_tokens("BISCOITO RECHEADO 108G")


def test_accents_do_not_split_the_same_word():
    assert distinctive_tokens("LIMÃO") == distinctive_tokens("LIMAO")


def test_same_product_with_new_barcode_is_detected():
    """Caso real: fabricante troca o GTIN e a planilha marca a descricao como NOVO."""
    hits = find_description_duplicates("SALG PINGO OURO PICANHA 55G NOVO", CATALOG)

    assert [h["produtoCodigo"] for h in hits] == [1802708]


def test_different_flavour_is_not_a_duplicate():
    assert find_description_duplicates("BISC BAUDUCCO COOKIES AMORA 96G", CATALOG) == []


def test_different_product_sharing_words_is_not_a_duplicate():
    assert find_description_duplicates("BISCOITO COOKIE GAROTO CROCANTE 60GR", CATALOG) == []


def test_different_flavour_of_pingo_is_not_a_duplicate():
    assert find_description_duplicates("PINGO OURO CHURRASCO 55G", CATALOG) == []


def test_short_description_is_not_compared():
    """Uma palavra distintiva nao basta: bloquear por ela geraria falso positivo."""
    assert find_description_duplicates("PINGO", CATALOG) == []


def test_extra_words_in_catalog_entry_still_match():
    catalog = [{"produtoCodigo": 1, "nome": "REFRIGERANTE COCA COLA LATA 350ML"}]

    assert find_description_duplicates("COCA COLA 350ML", catalog)
