"""Testes — normalização de filtros empresa LOGOS."""
from __future__ import annotations

import pytest

from src.services.multiselect_utils import (
    empresa_snapshot_suffix,
    is_network_wide_empresa,
    parse_empresa_codigos,
)


@pytest.mark.parametrize(
    ("value", "expected_wide"),
    [
        (None, True),
        ("", True),
        ("Todos", True),
        ("todos", True),
        ("ALL", True),
        ("11495", False),
        ("11495,5555", False),
    ],
)
def test_is_network_wide(value, expected_wide) -> None:
    assert is_network_wide_empresa(value) is expected_wide


def test_parse_empresa_ignores_todos() -> None:
    assert parse_empresa_codigos("Todos") == []
    assert parse_empresa_codigos("11495,5555") == [11495, 5555]


def test_snapshot_suffix_never_todos_literal() -> None:
    assert empresa_snapshot_suffix("Todos") == "all"
    assert empresa_snapshot_suffix("") == "all"
    assert empresa_snapshot_suffix("11495") == "11495"
    assert empresa_snapshot_suffix("11495,5555") == "5555,11495"
