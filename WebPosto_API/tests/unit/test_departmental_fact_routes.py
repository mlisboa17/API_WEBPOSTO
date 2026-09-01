import asyncio

import pytest

from src.interfaces.http.routes import departmental_facts as mod
from src.interfaces.http.app import create_app
from src.services.departmental_fact_store import DepartmentalFactStore


class FakePipeline:
    async def build_day(self, company, day):
        if company == 5256:
            return {
                "companyCode": company,
                "day": day,
                "materialized": False,
                "blockingReasons": ["UNLICENSED_COMPANY"],
            }
        return {
            "companyCode": company,
            "day": day,
            "materialized": True,
            "publishable": False,
            "blockingReasons": ["QUARANTINE_ABOVE_TOLERANCE:expenses"],
            "pagination": {},
            "catalogCoverage": {},
            "classificationCoverage": {},
            "batches": {},
        }


@pytest.fixture()
def isolated_services(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_pipeline", FakePipeline())
    monkeypatch.setattr(mod, "_store", DepartmentalFactStore(tmp_path))


def test_materialize_persists_and_quality_reads_same_summary(isolated_services):
    created = asyncio.run(mod.materialize_departmental_facts(11495, "2026-07-23", {"sub": "ops", "role": "operations"}))
    loaded = asyncio.run(mod.departmental_fact_quality(11495, "2026-07-23"))

    assert created["data"]["materialized"] is True
    assert created["data"]["publishable"] is False
    assert loaded["data"]["companyCode"] == 11495


def test_materialize_rejects_unlicensed_company(isolated_services):
    with pytest.raises(Exception) as exc_info:
        asyncio.run(mod.materialize_departmental_facts(5256, "2026-07-23", {"sub": "ops", "role": "operations"}))

    assert getattr(exc_info.value, "status_code", None) == 422


def test_quality_returns_404_when_snapshot_does_not_exist(isolated_services):
    with pytest.raises(Exception) as exc_info:
        asyncio.run(mod.departmental_fact_quality(74014, "2026-07-23"))

    assert getattr(exc_info.value, "status_code", None) == 404


def test_departmental_fact_routes_are_registered_in_application():
    paths = {route.path for route in create_app().routes}

    assert "/api/v1/departmental-facts/materialize" in paths
    assert "/api/v1/departmental-facts/quality" in paths
