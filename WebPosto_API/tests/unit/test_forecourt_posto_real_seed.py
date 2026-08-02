"""FORECOURT-CONFIG-01C-A — seed Posto Real (22 bicos) + regressão Casa Caiada."""

from __future__ import annotations

from src.services.forecourt_layout_service import ForecourtLayoutService

EXPECTED_REAL_NOZZLES = set(range(1, 23))  # 001–022

# Cadeia esperada (dados do seed — sem hardcode de regra analítica)
CHAIN_SAMPLES = {
    1: {
        "position_code": "REAL_B01_SENSOR_01",
        "orientation": "UNCONFIRMED",
        "pump_id": 1,
        "island_code": "REAL_LIQ_ILHA_01",
        "zone_code": "ZONE_LIQUIDOS",
    },
    10: {
        "position_code": "REAL_B02_SENSOR_04",
        "orientation": "UNCONFIRMED",
        "pump_id": 2,
        "island_code": "REAL_LIQ_ILHA_02",
        "zone_code": "ZONE_LIQUIDOS",
    },
    17: {
        "position_code": "REAL_B03_SENSOR_05",
        "orientation": "UNCONFIRMED",
        "pump_id": 3,
        "island_code": "REAL_LIQ_ILHA_03",
        "zone_code": "ZONE_LIQUIDOS",
    },
    19: {
        "position_code": "REAL_GNV_001",
        "orientation": "GNV",
        "pump_id": 101,
        "island_code": "REAL_GNV_01",
        "zone_code": "ZONE_GNV",
    },
    22: {
        "position_code": "REAL_GNV_002",
        "orientation": "GNV",
        "pump_id": 102,
        "island_code": "REAL_GNV_02",
        "zone_code": "ZONE_GNV",
    },
}


def _nozzle_ids(layout: dict) -> set[int]:
    ids: set[int] = set()
    for p in layout.get("positions") or []:
        for n in p.get("nozzles") or []:
            ids.add(int(n["nozzle_id"]))
    return ids


def test_posto_real_maps_all_22_nozzles():
    svc = ForecourtLayoutService(isolated=True)
    seeded = svc.seed_posto_real_pilot()
    assert seeded["name"] == "Posto Real V1"
    assert seeded["status"] == "ACTIVE"
    assert seeded["mapping_status"] == "PROVISIONAL"
    assert seeded["summary"]["qtd_bicos"] == 22
    assert seeded["summary"]["qtd_ilhas"] == 5
    assert seeded["summary"]["qtd_ilhas_liquidos"] == 3
    assert seeded["summary"]["qtd_equip_gnv"] == 2
    assert seeded["summary"]["qtd_bombas_liquidos"] == 3
    assert seeded["summary"]["qtd_posicoes"] == 8
    assert seeded["summary"]["qtd_posicoes_liquidos"] == 6
    assert seeded["summary"]["qtd_zonas"] == 2
    assert seeded.get("markers") and seeded["markers"][0]["code"] == "BR-101"
    assert "orientação física" in (seeded.get("mapping_note") or "").lower()
    assert _nozzle_ids(seeded) == EXPECTED_REAL_NOZZLES
    # Sensores líquidos sem orientação inventada
    for p in seeded["positions"]:
        if "SENSOR" in p["code"]:
            assert p["orientation"] == "UNCONFIRMED"
    # Geometria T: Ilha 3 à esquerda, Ilha 1 à direita
    by_code = {i["code"]: i for i in seeded["islands"]}
    assert by_code["REAL_LIQ_ILHA_03"]["x"] < by_code["REAL_LIQ_ILHA_02"]["x"]
    assert by_code["REAL_LIQ_ILHA_02"]["x"] < by_code["REAL_LIQ_ILHA_01"]["x"]


def test_posto_real_resolve_chain_bico_to_zone():
    svc = ForecourtLayoutService(isolated=True)
    seeded = svc.seed_posto_real_pilot()
    station = int(seeded["station_id"])
    assert station == 74014  # Real/Doze via alias do seed

    for nozzle_id, expect in CHAIN_SAMPLES.items():
        r = svc.resolve_nozzle(station, nozzle_id)
        assert r.position_code == expect["position_code"]
        assert r.orientation == expect["orientation"]
        assert r.pump_id == expect["pump_id"]
        assert r.island_code == expect["island_code"]
        assert r.zone_code == expect["zone_code"]
        assert r.zone_name  # preenchido via zones do layout


def test_posto_real_seed_idempotent_no_duplication():
    svc = ForecourtLayoutService(isolated=True)
    a = svc.seed_posto_real_pilot()
    b = svc.seed_posto_real_pilot()
    assert a["id"] == b["id"]
    assert b.get("seeded") is False
    layouts_real = [
        L
        for L in svc.list_layouts(74014)
        if L.get("name") == "Posto Real V1" and L.get("status") != "ARCHIVED"
    ]
    assert len(layouts_real) == 1
    assert _nozzle_ids(b) == EXPECTED_REAL_NOZZLES
    assert len(b["islands"]) == 5
    # Sem bicos duplicados no layout
    assert len(_nozzle_ids(b)) == sum(
        len(p.get("nozzles") or []) for p in b["positions"]
    )


def test_casa_caiada_regression_isolated_from_real():
    svc = ForecourtLayoutService(isolated=True)
    real = svc.seed_posto_real_pilot()
    casa = svc.seed_casa_caiada_pilot()

    assert int(real["station_id"]) == 74014
    assert int(casa["station_id"]) == 5555
    assert _nozzle_ids(real) == EXPECTED_REAL_NOZZLES
    assert _nozzle_ids(casa) == {1, 2, 3, 4, 5, 6, 7, 8}

    # Isolamento: resolve Casa não enxerga layout Real
    r_casa = svc.resolve_nozzle(5555, 8)
    assert r_casa.position_code == "CC_B01_AVENIDA"
    assert r_casa.station_id == 5555

    r_real = svc.resolve_nozzle(74014, 8)
    assert r_real.position_code == "REAL_B02_SENSOR_03"
    assert r_real.zone_code == "ZONE_LIQUIDOS"

    # Segundo seed Casa também idempotente e não altera Real
    casa2 = svc.seed_casa_caiada_pilot()
    assert casa2["id"] == casa["id"]
    assert svc.get_active_layout(74014)["id"] == real["id"]
    assert _nozzle_ids(svc.get_active_layout(74014)) == EXPECTED_REAL_NOZZLES
