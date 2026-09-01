"""Testes do ExternalMarketService — fallback e parsing CEPEA."""
from __future__ import annotations

import pytest

from src.services.external_market_service import (
    ExternalMarketService,
    BRANCH_GEOCOORDINATES,
)


@pytest.mark.asyncio
async def test_live_indicators_never_raise_and_have_values():
    svc = ExternalMarketService(timeout_seconds=8.0)
    live = await svc.get_live_indicators(force_refresh=True)

    assert live.usd_brl.value > 0
    assert live.brent_usd.value > 0
    assert live.esalq_etanol_pe.value > 0
    assert live.esalq_etanol_al.value > 0
    payload = live.to_dict()
    assert "sources" in payload
    assert "is_fallback" in payload
    assert len(payload["branches_geo"]) >= 3


def test_branch_coordinates_olinda_recife():
    svc = ExternalMarketService()
    casa = svc.get_branch_coordinates(5555)[0]
    vip = svc.get_branch_coordinates(6666)[0]
    real = svc.get_branch_coordinates(74014)[0]

    assert casa["cidade"] == "Olinda"
    assert vip["cidade"] == "Olinda"
    assert real["cidade"] == "Recife"
    assert casa["latitude"] < 0 and casa["longitude"] < 0
    assert 5555 in BRANCH_GEOCOORDINATES


def test_parse_cepea_etanol_prices_from_html_snippet():
    html = """
    <html><body>
    Indicador Etanol Hidratado Pernambuco 3,45 e Alagoas 3,38
    </body></html>
    """
    parsed = ExternalMarketService._parse_cepea_etanol_prices(html)
    assert "pe" in parsed
    assert 1.5 <= parsed["pe"] <= 8.0
