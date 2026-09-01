"""Bateria de testes de negócio — Rush Intelligence V3."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.services.rush_heatmap_engine import (
    FuelEvent,
    RushWindow,
    calculate_attendant_productivity,
    calculate_forecourt_imbalance,
    calculate_heat_score,
    calculate_island_pressure,
    detect_rush,
    diagnose_suspicions,
    heat_color,
    reset_engine_state_for_tests,
)

TZ = ZoneInfo("America/Recife")
BASE = datetime(2026, 8, 1, 10, 0, tzinfo=TZ)


def _ev(
    i: int,
    *,
    frentista: str,
    fid: int,
    ilha: int,
    minute: int,
    litros: float = 40.0,
    pendente: bool = False,
    empresa: int = 74014,
) -> FuelEvent:
    # bico: ilha1 -> 1-2, ilha2 -> 3-4, ilha3 -> 5-6
    bico = (ilha - 1) * 2 + 1
    bomba = ilha * 2 - 1
    t1 = BASE + timedelta(minutes=minute)
    return FuelEvent(
        id=i,
        empresa=empresa,
        bico=bico,
        bomba=bomba,
        ilha=ilha,
        combustivel="Gasolina",
        frentista_id=fid,
        frentista_nome=frentista,
        t1=t1,
        t2=t1 + timedelta(minutes=3),
        litros=litros,
        valor=litros * 6.0,
        pendente=pendente,
    )


def test_heat_score_formula_and_colors():
    s = calculate_heat_score(45, 30, 0.2, 1.0)
    assert s > 0
    assert heat_color(25) == "YELLOW"
    assert heat_color(45) == "ORANGE"
    assert heat_color(70) == "RED"
    assert heat_color(90) == "RED_HOT"
    assert heat_color(10) == "GREEN"


def test_1_joao_28_vs_pedro_9_absolute_visible():
    """Teste 1: diferença absoluta 28 × 9 visível + LOW_RUSH_PRODUCTIVITY."""
    reset_engine_state_for_tests()
    events: list[FuelEvent] = []
    n = 1
    # Mesma janela ativa (0–27 min): 28 vs 9 — contraste absoluto, não turno curto
    for m in range(28):
        events.append(_ev(n, frentista="João", fid=1, ilha=1, minute=m))
        n += 1
    for m in range(9):
        events.append(_ev(n, frentista="Pedro", fid=2, ilha=2, minute=int(m * 27 / 8)))
        n += 1

    rush = RushWindow(
        empresa=74014,
        start=BASE,
        end=BASE + timedelta(minutes=40),
        event_ids=[e.id for e in events],
        label="10:00-10:40",
    )
    prod = calculate_attendant_productivity(events, rush=rush)
    assert prod[0]["frentista_nome"] == "João"
    assert prod[0]["abastecimentos"] == 28
    pedro = next(p for p in prod if p["frentista_nome"] == "Pedro")
    assert pedro["abastecimentos"] == 9

    sus = diagnose_suspicions(
        empresa=74014,
        rush=rush,
        productivity=prod,
        island_pressure=calculate_island_pressure(events, empresa=74014, rush=rush),
        events=events,
        recurrence_hits={},
    )
    low = [s for s in sus if s["type"] == "LOW_RUSH_PRODUCTIVITY"]
    assert low, sus
    assert low[0]["severity"] == "ORANGE"
    assert "28 × 9" in low[0]["evidence"]["comparativo_absoluto"]


def test_2_isolated_orange_recurring_red():
    """Teste 2: 1x laranja; 4/5 rushes → vermelho."""
    reset_engine_state_for_tests()
    events = [_ev(i, frentista="João", fid=1, ilha=1, minute=i) for i in range(20)]
    # Pedro espalhado na mesma janela (baixa densidade = baixa taxa e baixo absoluto)
    events += [
        _ev(100 + i, frentista="Pedro", fid=2, ilha=2, minute=int(i * 19 / 5))
        for i in range(6)
    ]
    rush = RushWindow(
        empresa=74014,
        start=BASE,
        end=BASE + timedelta(minutes=30),
        event_ids=[e.id for e in events],
        label="R1",
    )
    prod = calculate_attendant_productivity(events, rush=rush)
    islands = calculate_island_pressure(events, empresa=74014, rush=rush)

    iso = diagnose_suspicions(
        empresa=74014,
        rush=rush,
        productivity=prod,
        island_pressure=islands,
        events=events,
        recurrence_hits={"74014:2": 1},
    )
    low = next(s for s in iso if s["type"] == "LOW_RUSH_PRODUCTIVITY")
    assert low["severity"] == "ORANGE"
    assert 40 <= low["heat_score"] < 60

    rec = diagnose_suspicions(
        empresa=74014,
        rush=rush,
        productivity=prod,
        island_pressure=islands,
        events=events,
        recurrence_hits={"74014:2": 4},
    )
    red = next(s for s in rec if s["type"] == "RECURRING_LOW_RUSH_PRODUCTIVITY")
    assert red["severity"] in {"RED", "RED_HOT"}
    assert red["heat_score"] >= 60


def test_3_poor_operational_positioning():
    """Teste 3: Ilha 1 saturada × Ilha 3 ociosa com frentista."""
    reset_engine_state_for_tests()
    events: list[FuelEvent] = []
    n = 1
    # pressão alta ilha 1
    for m in range(20):
        events.append(_ev(n, frentista="Ana", fid=10, ilha=1, minute=m, pendente=True))
        n += 1
    # ilha 3 ociosa com frentista (poucos eventos)
    events.append(_ev(n, frentista="Carlos", fid=11, ilha=3, minute=5, pendente=False))
    n += 1

    rush = RushWindow(
        empresa=74014,
        start=BASE,
        end=BASE + timedelta(minutes=30),
        event_ids=[e.id for e in events],
        label="POS",
    )
    # força utilização via known capacity + pendentes
    islands = [
        {
            "ilha": 1,
            "capacidade_bicos": 2,
            "bicos_ocupados_proxy": 2,
            "abastecimentos_janela": 20,
            "utilizacao": 0.95,
            "frentistas": ["Ana"],
        },
        {
            "ilha": 3,
            "capacidade_bicos": 2,
            "bicos_ocupados_proxy": 0,
            "abastecimentos_janela": 1,
            "utilizacao": 0.30,
            "frentistas": ["Carlos"],
        },
    ]
    assert calculate_forecourt_imbalance(islands) >= 0.45
    prod = calculate_attendant_productivity(events, rush=rush)
    sus = diagnose_suspicions(
        empresa=74014,
        rush=rush,
        productivity=prod,
        island_pressure=islands,
        events=events,
    )
    types = {s["type"] for s in sus}
    assert "POOR_OPERATIONAL_POSITIONING" in types


def test_4_vehicle_direction_failure():
    """Teste 4: frentista+bico livre na ilha ociosa + demanda na saturada."""
    reset_engine_state_for_tests()
    islands = [
        {
            "ilha": 1,
            "capacidade_bicos": 2,
            "bicos_ocupados_proxy": 2,
            "abastecimentos_janela": 25,
            "utilizacao": 0.95,
            "frentistas": ["Ana"],
        },
        {
            "ilha": 3,
            "capacidade_bicos": 2,
            "bicos_ocupados_proxy": 0,
            "abastecimentos_janela": 1,
            "utilizacao": 0.25,
            "frentistas": ["Carlos"],
        },
    ]
    events = [
        _ev(1, frentista="Ana", fid=10, ilha=1, minute=0, pendente=True),
        _ev(2, frentista="Carlos", fid=11, ilha=3, minute=1),
    ]
    rush = RushWindow(
        empresa=74014,
        start=BASE,
        end=BASE + timedelta(minutes=30),
        event_ids=[1, 2],
        label="DIR",
    )
    prod = calculate_attendant_productivity(events, rush=rush)
    sus = diagnose_suspicions(
        empresa=74014,
        rush=rush,
        productivity=prod,
        island_pressure=islands,
        events=events,
    )
    assert any(s["type"] == "VEHICLE_DIRECTION_FAILURE_SUSPECTED" for s in sus)


def test_5_structural_saturation_no_blame():
    """Teste 5: 100% bicos ocupados → STRUCTURAL_SATURATION sem culpar equipe."""
    reset_engine_state_for_tests()
    events = [
        _ev(1, frentista="A", fid=1, ilha=1, minute=0, pendente=True),
        _ev(2, frentista="B", fid=2, ilha=1, minute=1, pendente=True),
        _ev(3, frentista="C", fid=3, ilha=2, minute=2, pendente=True),
        _ev(4, frentista="D", fid=4, ilha=2, minute=3, pendente=True),
    ]
    events[0] = replace(events[0], bico=1, pendente=True)
    events[1] = replace(events[1], bico=2, pendente=True)
    events[2] = replace(events[2], bico=3, pendente=True)
    events[3] = replace(events[3], bico=4, pendente=True)

    rush = RushWindow(
        empresa=74014,
        start=BASE,
        end=BASE + timedelta(minutes=20),
        event_ids=[1, 2, 3, 4],
        label="SAT",
    )
    prod = calculate_attendant_productivity(events, rush=rush)
    islands = calculate_island_pressure(events, empresa=74014, rush=rush)
    sus = diagnose_suspicions(
        empresa=74014,
        rush=rush,
        productivity=prod,
        island_pressure=islands,
        events=events,
        structural_bicos_total=4,
    )
    assert len(sus) == 1
    assert sus[0]["type"] == "STRUCTURAL_SATURATION"
    assert "não culpar" in sus[0]["evidence"]["nota"].casefold() or "Saturação" in sus[0]["evidence"]["nota"]


def test_6_short_shift_high_rate_not_flagged():
    """Teste 6: Pedro 30 min alta taxa/hora — absoluto menor, sem marca de baixa prod."""
    reset_engine_state_for_tests()
    events: list[FuelEvent] = []
    n = 1
    # João 60 min ~ 20 abast
    for m in range(0, 60, 3):
        events.append(_ev(n, frentista="João", fid=1, ilha=1, minute=m))
        n += 1
    # Pedro 30 min densos — 10 abast em 30 min (taxa alta)
    for m in range(0, 30, 3):
        events.append(_ev(n, frentista="Pedro", fid=2, ilha=2, minute=m))
        n += 1

    rush = RushWindow(
        empresa=74014,
        start=BASE,
        end=BASE + timedelta(minutes=60),
        event_ids=[e.id for e in events],
        label="RATE",
    )
    prod = calculate_attendant_productivity(events, rush=rush)
    pedro = next(p for p in prod if p["frentista_nome"] == "Pedro")
    joao = next(p for p in prod if p["frentista_nome"] == "João")
    assert pedro["abastecimentos"] < joao["abastecimentos"]
    assert pedro["abastecimentos_hora"] >= joao["abastecimentos_hora"] * 0.85

    sus = diagnose_suspicions(
        empresa=74014,
        rush=rush,
        productivity=prod,
        island_pressure=calculate_island_pressure(events, empresa=74014, rush=rush),
        events=events,
    )
    flagged = [
        s
        for s in sus
        if s["subject_name"] == "Pedro"
        and s["type"]
        in {"LOW_RUSH_PRODUCTIVITY", "RECURRING_LOW_RUSH_PRODUCTIVITY"}
    ]
    assert flagged == [], flagged


def test_detect_rush_finds_window():
    events = [_ev(i, frentista="X", fid=1, ilha=1, minute=i) for i in range(15)]
    rushes = detect_rush(events, window_minutes=30, min_abs=8)
    assert rushes
    assert rushes[0].empresa == 74014
