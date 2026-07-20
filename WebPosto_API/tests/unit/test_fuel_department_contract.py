from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.domain.fuel.models import FuelVolumeFact
from src.services.fuel_analytics_service import FuelAnalyticsFilters, FuelAnalyticsService


def test_fuel_fact_accepts_licensed_company_and_normalizes_liters() -> None:
    fact = FuelVolumeFact(
        empresa_codigo=11495,
        produto_codigo=1257884,
        produto_lmc_codigo=8297,
        combustivel="Gasolina comum",
        data_referencia="2026-07-17",
        litros="100.5555",
    )

    assert fact.departamento == "combustiveis"
    assert fact.litros == Decimal("100.556")
    assert fact.fonte == "CONSULTAR_LMC_REDE"


def test_fuel_fact_rejects_unlicensed_company() -> None:
    with pytest.raises(ValidationError, match="empresa fora do escopo licenciado"):
        FuelVolumeFact(
            empresa_codigo=5333,
            produto_codigo=1257884,
            combustivel="Gasolina comum",
            litros=10,
        )


def test_fuel_fact_rejects_zero_or_negative_volume() -> None:
    with pytest.raises(ValidationError):
        FuelVolumeFact(
            empresa_codigo=5555,
            produto_codigo=1257884,
            combustivel="Gasolina comum",
            litros=0,
        )


@pytest.mark.asyncio
async def test_fuel_service_blocks_unlicensed_filter_before_calling_api() -> None:
    class ClientThatMustNotBeCalled:
        async def call_endpoint(self, *_args, **_kwargs):
            raise AssertionError("API não deveria ser chamada")

    service = FuelAnalyticsService(ClientThatMustNotBeCalled())
    response = await service.get_fuel_summary(
        FuelAnalyticsFilters("2026-07-01", "2026-07-17", empresa_codigo=5333)
    )

    assert response.success is False
    assert response.error is not None
    assert response.error.status == 403
    assert response.error.type == "UNLICENSED_COMPANY"
