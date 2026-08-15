"""Classificacao dos pares retidos: medida confirma duplicidade, nunca presume."""

from __future__ import annotations

import pytest

from src.operational.product_registration.duplicate_checker import (
    FALSE_POSITIVE,
    POSSIBLE_VARIANT,
    SAME_PRODUCT_NEW_GTIN,
    classify_duplicate,
    distinctive_tokens,
    extract_measure,
    find_description_duplicates,
)
from src.operational.product_registration.product_family import commercial_family


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("BISC BAUDUCCO COOKIES AMORA 96G", (96.0, "G")),
        ("BISCOITO COOKIE GAROTO CROCANTE 60GR", (60.0, "G")),
        ("ACUCAR REFINADO 1KG", (1000.0, "G")),
        ("CERVEJA IMPERIO GOLD 330ML", (330.0, "ML")),
        ("WHISKY JACK DANIELS 1 LT", (1000.0, "ML")),
        ("VODKA NATASHA LIMAO 1L", (1000.0, "ML")),
        ("PASSATEMPO Bisc Recheado Choc 70x130g BR", (130.0, "G")),
    ],
)
def test_measure_is_normalized(description, expected):
    assert extract_measure(description) == expected


def test_description_without_measure_returns_none():
    assert extract_measure("PINGO DE OURO PICANHA") is None


def test_digits_that_are_not_measure_are_ignored():
    assert extract_measure("WHISKY JACK DANIELS N 7") is None


def test_same_measure_and_same_terms_is_confirmed_duplicate():
    label, reason = classify_duplicate(
        "CERVEJA IMPERIO PURO MALTE LATA 350 ML", "CERVEJA IMPERIO PURO MALTE 350 ML"
    )

    assert label == SAME_PRODUCT_NEW_GTIN
    assert "350" in reason


def test_different_measure_is_variant():
    label, reason = classify_duplicate(
        "CERVEJA IMPERIO GOLD 330ML", "CERVEJA IMPERIO GOLD 269ML"
    )

    assert label == POSSIBLE_VARIANT
    assert "Conteúdo diferente" in reason


def test_missing_measure_never_confirms_duplicate():
    """Caso do Pingo de Ouro: nomes iguais, mas o cadastro nao declara conteudo."""
    label, reason = classify_duplicate(
        "SALG PINGO OURO PICANHA 55G NOVO", "PINGO DE OURO PICANHA"
    )

    assert label == POSSIBLE_VARIANT
    assert "não declarada" in reason


def test_extra_qualifier_in_existing_record_is_variant():
    label, reason = classify_duplicate(
        "ESPUMANTE SALTON BRUT 750ML", "ESPUMANTE SALTON BRUT ROSE 750ML"
    )

    assert label == POSSIBLE_VARIANT
    assert "ROSE" in reason


def test_abbreviated_com_is_not_a_qualifier():
    """'C/' e abreviacao de 'com' e nao distingue produto."""
    label, reason = classify_duplicate(
        "BARRA CEREAL NUTRY AVELA CHOCOLATE 22G", "BARRA CEREAL NUTRY AVELA C/ CHOCOLATE"
    )

    assert label == POSSIBLE_VARIANT
    assert "não declarada" in reason


def test_content_difference_is_reported_before_qualifier():
    label, reason = classify_duplicate(
        "CERVEJA IMPERIO LAGER 330ML", "CERVEJA IMPERIO LAGER LONG 275ML"
    )

    assert label == POSSIBLE_VARIANT
    assert "Conteúdo diferente" in reason


def test_different_grandeza_is_variant():
    label, _ = classify_duplicate("SUCO UVA 500ML", "SUCO UVA 500G")

    assert label == POSSIBLE_VARIANT


def test_different_commercial_family_is_false_positive():
    label, reason = classify_duplicate(
        "BISCOITO COOKIE GAROTO 60G",
        "BARRA GAROTO COOKIE 60G",
        candidate_family="BISCOITO",
        existing_family="CHOCOLATE",
    )

    assert label == FALSE_POSITIVE
    assert "Famílias" in reason


def test_family_keyword_matches_whole_word_only():
    assert commercial_family("SALGADINHO PINGO OURO") == "SALGADINHO"
    assert commercial_family("SAL REFINADO 1KG") == "MERCEARIA"


def test_unknown_product_has_no_family():
    assert commercial_family("PRODUTO GENERICO XYZ") is None


# Qualificadores de modelo/tamanho/versao devem ser preservados na normalizacao e
# distintivos na confirmacao de duplicidade.

def test_model_numbers_are_distinctive_tokens():
    assert "102" in distinctive_tokens("FILTRO PARA CAFE 102 CAIXA 30 UNIDADES - MELITTA")
    assert "103" in distinctive_tokens("FILTRO PARA CAFE 103 CAIXA 30 UNIDADES - MELITTA")


def test_filter_102_and_103_are_not_duplicates():
    f102 = "FILTRO PARA CAFE 102 CAIXA 30 UNIDADES - MELITTA"
    f103 = "FILTRO PARA CAFE 103 CAIXA 30 UNIDADES - MELITTA"

    assert find_description_duplicates(f102, [{"nome": f103}]) == []
    assert find_description_duplicates(f103, [{"nome": f102}]) == []


def test_same_model_103_with_abbreviated_description_is_still_duplicate():
    f103_full = "FILTRO PARA CAFE 103 CAIXA 30 UNIDADES - MELITTA"
    f103_short = "FILTRO MELITTA 103"

    assert find_description_duplicates(f103_short, [{"nome": f103_full}]) != []


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("PILHA DURACELL AA", "PILHA DURACELL AAA"),
        ("CAMISETA BRANCA P", "CAMISETA BRANCA M"),
        ("VENTILADOR ARNO 110V", "VENTILADOR ARNO 220V"),
        ("SMARTPHONE X MODELO 1", "SMARTPHONE X MODELO 2"),
    ],
)
def test_model_size_and_version_numbers_are_not_duplicates(first, second):
    assert find_description_duplicates(first, [{"nome": second}]) == []
    assert find_description_duplicates(second, [{"nome": first}]) == []
