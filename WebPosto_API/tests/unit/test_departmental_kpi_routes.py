import asyncio

import pytest

from src.interfaces.http.app import create_app
from src.interfaces.http.routes import departmental_kpis as mod


class FakeService:
    def build_dre(self, company, day):
        if company == 5256:
            raise ValueError("UNLICENSED_COMPANY")
        if company == 74014:
            return None
        return {"companyCode": company, "period": {"start": day, "end": day}, "lines": []}


class FakeComparison:
    def build(self, day):
        return {"period": {"start": day, "end": day}, "departments": []}


class FakeHistory:
    def build(self, company, start, end):
        return {"companyCode": company, "period": {"start": start, "end": end}}


class FakeExecutive:
    def cockpit(self, day):
        return {"period": {"start": day, "end": day}, "blocks": []}

    def director_panels(self, company, start, end):
        return {"companyCode": company, "period": {"start": start, "end": end}}


@pytest.fixture(autouse=True)
def fake_service(monkeypatch):
    monkeypatch.setattr(mod, "_service", FakeService())
    monkeypatch.setattr(mod, "_comparison", FakeComparison())
    monkeypatch.setattr(mod, "_history", FakeHistory())
    monkeypatch.setattr(mod, "_executive", FakeExecutive())


def test_dre_route_returns_service_result():
    response = asyncio.run(mod.departmental_dre(11495, "2026-07-23"))
    assert response["success"] is True
    assert response["data"]["companyCode"] == 11495


def test_dre_route_rejects_unlicensed_company():
    with pytest.raises(Exception) as exc_info:
        asyncio.run(mod.departmental_dre(5256, "2026-07-23"))
    assert getattr(exc_info.value, "status_code", None) == 422


def test_dre_route_returns_404_without_materialized_batch():
    with pytest.raises(Exception) as exc_info:
        asyncio.run(mod.departmental_dre(74014, "2026-07-23"))
    assert getattr(exc_info.value, "status_code", None) == 404


def test_dre_route_is_registered():
    paths = {route.path for route in create_app().routes}
    assert "/api/v1/departmental-kpis/dre" in paths
    assert "/api/v1/departmental-kpis/comparisons" in paths
    assert "/api/v1/departmental-kpis/trends" in paths
    assert "/api/v1/departmental-kpis/presidency-cockpit" in paths
    assert "/api/v1/departmental-kpis/director-panels" in paths


def test_comparison_route_returns_same_period_result():
    response = asyncio.run(mod.departmental_comparisons("2026-07-23"))
    assert response["data"]["period"]["start"] == "2026-07-23"


def test_sprint_4_to_6_routes_return_scoped_results():
    trend = asyncio.run(mod.departmental_trends(11495, "2026-07-23", "2026-07-23"))
    cockpit = asyncio.run(mod.presidency_cockpit("2026-07-23"))
    panels = asyncio.run(mod.director_panels(11495, "2026-07-23", "2026-07-23"))
    assert trend["data"]["companyCode"] == 11495
    assert cockpit["data"]["blocks"] == []
    assert panels["data"]["companyCode"] == 11495
