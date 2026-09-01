"""Testes do bridge WebPosto (venda + venda_forma_pagamento) -> CardSaleEvent (D02+)."""
from __future__ import annotations

from datetime import datetime

from src.services.bank_reconciliation.card_sale_event_builder import (
    build_administradora_lookup,
    build_card_sale_events,
)


def _venda(venda_codigo: int, **overrides) -> dict:
    defaults = dict(vendaCodigo=venda_codigo, data="2026-07-05")
    defaults.update(overrides)
    return defaults


def _vfp(venda_codigo: int, **overrides) -> dict:
    defaults = dict(
        vendaCodigo=venda_codigo,
        vendaFormaPagamentoCodigo=1,
        nomeFormaPagamento="CARTAO CREDITO VISA",
        valorPagamento=150.0,
    )
    defaults.update(overrides)
    return defaults


def test_build_card_sale_events_joins_venda_date_and_translates_method():
    venda_rows = [_venda(1)]
    vfp_rows = [_vfp(1)]

    events = build_card_sale_events(venda_rows, vfp_rows)

    assert len(events) == 1
    event = events[0]
    assert event.occurredAt == datetime(2026, 7, 5)
    assert event.amount == 150.0
    assert event.brand == "VISA"
    assert event.method == "CREDITO"
    assert event.reference == "1-1"


def test_build_card_sale_events_translates_debit_method():
    venda_rows = [_venda(2)]
    vfp_rows = [_vfp(2, nomeFormaPagamento="CARTAO DEBITO MASTERCARD", valorPagamento=80.0)]

    events = build_card_sale_events(venda_rows, vfp_rows)

    assert len(events) == 1
    assert events[0].method == "DEBITO"
    assert events[0].brand == "MASTERCARD"


def test_build_card_sale_events_skips_row_without_matching_venda():
    vfp_rows = [_vfp(99)]

    events = build_card_sale_events([], vfp_rows)

    assert events == []


def test_build_card_sale_events_uses_net_amount_when_fee_present():
    # O banco liquida o valor LIQUIDO (bruto - taxa da adquirente), nao o bruto da venda.
    venda_rows = [_venda(3)]
    vfp_rows = [_vfp(3, valorPagamento=100.0, taxaPercentual=3.39)]

    events = build_card_sale_events(venda_rows, vfp_rows)

    assert len(events) == 1
    assert events[0].amount == 96.61


def test_build_card_sale_events_uses_gross_amount_when_no_fee_present():
    venda_rows = [_venda(4)]
    vfp_rows = [_vfp(4, valorPagamento=100.0)]

    events = build_card_sale_events(venda_rows, vfp_rows)

    assert len(events) == 1
    assert events[0].amount == 100.0


def test_build_card_sale_events_skips_non_card_rows():
    venda_rows = [_venda(3)]
    vfp_rows = [
        dict(vendaCodigo=3, nomeFormaPagamento="DINHEIRO", valorPagamento=50.0),
        _vfp(3, vendaFormaPagamentoCodigo=2, valorPagamento=200.0),
    ]

    events = build_card_sale_events(venda_rows, vfp_rows)

    assert len(events) == 1
    assert events[0].amount == 200.0


def test_build_card_sale_events_skips_zero_amount():
    venda_rows = [_venda(4)]
    vfp_rows = [_vfp(4, valorPagamento=0)]

    events = build_card_sale_events(venda_rows, vfp_rows)

    assert events == []


def test_build_card_sale_events_uses_administradora_lookup_for_generic_label():
    """Achado real: nomeFormaPagamento costuma ser genérico ('CARTAO POS') sem bandeira/método —
    a resolução correta vem do administradoraCodigo via CONSULTAR_ADMINISTRADORA_REDE."""
    venda_rows = [_venda(5)]
    vfp_rows = [
        dict(
            vendaCodigo=5,
            vendaFormaPagamentoCodigo=1,
            nomeFormaPagamento="CARTAO POS",
            valorPagamento=120.0,
            administradoraCodigo=106906,
        )
    ]
    administradora_rows = [
        dict(administradoraCodigo=106906, descricao="VISA CREDITO PAGSEGURO CrÚdito", tipo="CrÚdito"),
    ]
    lookup = build_administradora_lookup(administradora_rows)

    events = build_card_sale_events(venda_rows, vfp_rows, lookup)

    assert len(events) == 1
    assert events[0].brand == "VISA"
    assert events[0].method == "CREDITO"


def test_build_administradora_lookup_handles_debito_mojibake():
    administradora_rows = [dict(administradoraCodigo=1, descricao="ELO DEBITO PAGSEGURO DÚbito", tipo="DÚbito")]

    lookup = build_administradora_lookup(administradora_rows)

    assert lookup[1]["brand"] == "ELO"
    assert lookup[1]["method"] == "DEBITO"


def test_build_card_sale_events_excludes_premmia_administradora():
    venda_rows = [_venda(6)]
    vfp_rows = [
        dict(
            vendaCodigo=6,
            vendaFormaPagamentoCodigo=1,
            nomeFormaPagamento="CARTAO",
            valorPagamento=90.0,
            administradoraCodigo=98787,
        )
    ]
    administradora_rows = [dict(administradoraCodigo=98787, descricao="PREMMIA CREDITO Carteira Digital", tipo="CrÚdito")]
    lookup = build_administradora_lookup(administradora_rows)

    events = build_card_sale_events(venda_rows, vfp_rows, lookup)

    assert events == []
