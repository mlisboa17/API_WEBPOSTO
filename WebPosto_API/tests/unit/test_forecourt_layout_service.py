"""FORECOURT-CONFIG-01A — testes obrigatórios do ForecourtLayoutService."""

from __future__ import annotations

import pytest

from src.services.forecourt_layout_service import (
    ForecourtLayoutService,
    ForecourtValidationError,
    IslandDTO,
    LayoutCreateDTO,
    NozzleLinkDTO,
    PositionDTO,
    validate_forecourt_layout_payload,
)

STATION_A = 74014  # Real
STATION_B = 11495  # VIP


def _sample_payload(station_id: int = STATION_A, *, dup_nozzle: bool = False) -> LayoutCreateDTO:
    nozzles_p1 = [NozzleLinkDTO(nozzle_id=1), NozzleLinkDTO(nozzle_id=2)]
    nozzles_p2 = [NozzleLinkDTO(nozzle_id=1 if dup_nozzle else 3)]
    return LayoutCreateDTO(
        station_id=station_id,
        name="Layout Teste",
        islands=[
            IslandDTO(code="I1", name="Ilha 1", display_order=1, x=10, y=20),
            IslandDTO(code="I2", name="Ilha 2", display_order=2, x=200, y=20),
        ],
        positions=[
            PositionDTO(
                island_code="I1",
                pump_id=1,
                code="P1-AV",
                orientation="AVENIDA",
                x=15,
                y=25,
                nozzles=nozzles_p1,
            ),
            PositionDTO(
                island_code="I2",
                pump_id=3,
                code="P2-CV",
                orientation="CONVENIENCIA",
                x=210,
                y=30,
                nozzles=nozzles_p2,
            ),
        ],
    )


def test_layout_versioning_increments_per_station():
    svc = ForecourtLayoutService(isolated=True)
    a1 = svc.create_layout(_sample_payload(STATION_A))
    a2 = svc.create_layout(
        LayoutCreateDTO(station_id=STATION_A, name="v2", islands=[], positions=[])
    )
    b1 = svc.create_layout(
        LayoutCreateDTO(station_id=STATION_B, name="vip-v1", islands=[], positions=[])
    )
    assert a1["version"] == 1
    assert a2["version"] == 2
    assert b1["version"] == 1
    assert a1["status"] == "DRAFT"


def test_reject_duplicate_nozzle_in_same_layout():
    with pytest.raises(ForecourtValidationError) as ei:
        validate_forecourt_layout_payload(
            station_id=STATION_A,
            islands=_sample_payload(dup_nozzle=True).islands,
            positions=_sample_payload(dup_nozzle=True).positions,
        )
    assert ei.value.code == "DUPLICATE_NOZZLE"

    svc = ForecourtLayoutService(isolated=True)
    with pytest.raises(ForecourtValidationError) as ei2:
        svc.create_layout(_sample_payload(dup_nozzle=True))
    assert ei2.value.code == "DUPLICATE_NOZZLE"


def test_tenant_isolation_blocks_cross_station_access():
    svc = ForecourtLayoutService(isolated=True)
    created = svc.create_layout(_sample_payload(STATION_A))
    layout_id = created["id"]

    with pytest.raises(ForecourtValidationError) as ei:
        svc.get_layout(layout_id, requester_station_id=STATION_B)
    assert ei.value.code == "TENANT_FORBIDDEN"

    with pytest.raises(ForecourtValidationError) as ei2:
        svc.activate_layout(layout_id, requester_station_id=STATION_B)
    assert ei2.value.code == "TENANT_FORBIDDEN"


def test_only_one_active_layout_per_overlapping_period():
    svc = ForecourtLayoutService(isolated=True)
    first = svc.create_layout(_sample_payload(STATION_A))
    second = svc.create_layout(
        LayoutCreateDTO(
            station_id=STATION_A,
            name="segundo",
            islands=[IslandDTO(code="I1", name="Ilha")],
            positions=[
                PositionDTO(
                    island_code="I1",
                    pump_id=1,
                    code="P1",
                    orientation="AVENIDA",
                    nozzles=[NozzleLinkDTO(nozzle_id=9)],
                )
            ],
        )
    )
    svc.activate_layout(first["id"])
    with pytest.raises(ForecourtValidationError) as ei:
        svc.activate_layout(second["id"])
    assert ei.value.code == "ACTIVE_LAYOUT_CONFLICT"


def test_resolve_nozzle_chain():
    svc = ForecourtLayoutService(isolated=True)
    created = svc.create_layout(_sample_payload(STATION_A))
    svc.activate_layout(created["id"])
    resolved = svc.resolve_nozzle(STATION_A, 1)
    assert resolved.nozzle_id == 1
    assert resolved.position_code == "P1-AV"
    assert resolved.orientation == "AVENIDA"
    assert resolved.pump_id == 1
    assert resolved.island_code == "I1"
    assert resolved.coordinates["x"] == 15.0
    assert resolved.island_coordinates["x"] == 10.0


def test_move_nozzle_is_data_only_update():
    """Mover bico entre posições via update — sem hardcode de filial/regra."""
    from src.services.forecourt_layout_service import LayoutUpdateDTO

    svc = ForecourtLayoutService(isolated=True)
    created = svc.create_layout(_sample_payload(STATION_A))
    svc.activate_layout(created["id"])
    before = svc.resolve_nozzle(STATION_A, 2)
    assert before.position_code == "P1-AV"

    positions = []
    for p in created["positions"]:
        nozzles = [n for n in p["nozzles"] if int(n["nozzle_id"]) != 2]
        if p["code"] == "P2-CV":
            nozzles.append({"nozzle_id": 2, "active": True, "label": ""})
        positions.append(
            PositionDTO(
                id=p.get("id"),
                island_code=p["island_code"],
                pump_id=p["pump_id"],
                code=p["code"],
                name=p.get("name") or "",
                orientation=p["orientation"],
                x=p["x"],
                y=p["y"],
                nozzles=[NozzleLinkDTO(**n) for n in nozzles],
            )
        )
    svc.update_layout(created["id"], LayoutUpdateDTO(positions=positions))
    after = svc.resolve_nozzle(STATION_A, 2)
    assert after.position_code == "P2-CV"
    assert after.orientation == "CONVENIENCIA"
