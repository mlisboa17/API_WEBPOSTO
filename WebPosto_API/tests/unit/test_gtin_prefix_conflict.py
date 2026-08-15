"""Prefixo GS1 e comprimento precisam concordar."""

from __future__ import annotations

from src.operational.product_registration.ean_service import gtin_prefix_length_conflict


def test_brazilian_gtin13_is_accepted():
    assert gtin_prefix_length_conflict("7896074051413") is None


def test_brazilian_prefix_with_twelve_digits_is_flagged():
    conflict = gtin_prefix_length_conflict("789607405141")

    assert conflict is not None
    assert "789" in conflict


def test_foreign_gtin12_remains_valid():
    assert gtin_prefix_length_conflict("012345678905") is None


def test_short_and_long_codes_are_untouched():
    assert gtin_prefix_length_conflict("78960740") is None
    assert gtin_prefix_length_conflict("78960740514139") is None
