"""GTIN com checksum valido pode ainda assim nao existir."""

from __future__ import annotations

import pytest

from src.operational.product_registration.duplicate_checker import looks_fabricated_gtin


@pytest.mark.parametrize(
    "ean",
    [
        "7891000377130",  # Negresco
        "7891008124583",  # Garoto crocante
        "7893000632073",  # Pizza Sadia
    ],
)
def test_real_barcodes_are_accepted(ean):
    assert looks_fabricated_gtin(ean) is None


def test_ascending_sequence_is_flagged():
    assert looks_fabricated_gtin("1234567890128") is not None


def test_embedded_sequence_is_flagged():
    assert looks_fabricated_gtin("4512345678999") is not None


def test_repeated_digit_is_flagged():
    assert looks_fabricated_gtin("9999999999999") is not None


def test_short_codes_are_left_to_the_checksum_rule():
    assert looks_fabricated_gtin("1234567") is None
