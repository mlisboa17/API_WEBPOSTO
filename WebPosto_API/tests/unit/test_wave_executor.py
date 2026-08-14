"""Fila da onda e aderencia ao perfil aprovado (sem rede, sem escrita)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_executor():
    """Carrega o executor por caminho: scripts/ nao e pacote importavel."""
    path = ROOT / "scripts" / "execute_wave_118508.py"
    spec = importlib.util.spec_from_file_location("execute_wave_118508", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


executor = _load_executor()

ICMS = {"cstIcmsSaida": "060"}
PIS = {"cstPisSaida": "01"}


def _profile(profile_id, *, level="PROFILE_C", eans, canary_status="PENDING", canary=None):
    return {
        "profile_id": profile_id,
        "level": level,
        "ncms": ["19053100"],
        "cests": ["1705300"],
        "tributo_icms": ICMS,
        "tributo_pis_cofins": PIS,
        "cfop_entrada": "1.102",
        "cfop_saida": "5.405",
        "quantidade_candidatos": len(eans),
        "profile_canary_status": canary_status,
        "produto_canario": canary,
        "produtos": [{"ean": ean, "precoVenda": 5.0 + index} for index, ean in enumerate(eans)],
    }


def _body(**overrides):
    body = {
        "codigoNcm": "19053100",
        "codigoCest": "1705300",
        "tributoIcms": ICMS,
        "tributoPisCofins": PIS,
        "cdCfopEntrada": "1.102",
        "cdCfopSaida": "5.405",
    }
    body.update(overrides)
    return body


def test_first_product_of_a_pending_profile_is_the_canary():
    queue = executor.build_queue([_profile("P1", eans=["1", "2", "3"])], {"PROFILE_C"}, 20)

    assert [item["is_canary"] for item in queue] == [True, False, False]


def test_declared_canary_goes_first_even_if_not_the_cheapest():
    profile = _profile("P1", eans=["1", "2", "3"], canary="3")

    queue = executor.build_queue([profile], {"PROFILE_C"}, 20)

    assert queue[0]["product"]["ean"] == "3"
    assert queue[0]["is_canary"] is True


def test_verified_profile_does_not_need_a_new_canary():
    profile = _profile("P1", eans=["1", "2"], canary_status="VERIFIED")

    queue = executor.build_queue([profile], {"PROFILE_C"}, 20)

    assert [item["is_canary"] for item in queue] == [False, False]


def test_bigger_profiles_come_first_so_one_approval_yields_more():
    small = _profile("SMALL", eans=["1"])
    big = _profile("BIG", eans=["2", "3", "4"])

    queue = executor.build_queue([small, big], {"PROFILE_C"}, 20)

    assert [item["profile"]["profile_id"] for item in queue] == ["BIG", "BIG", "BIG", "SMALL"]


def test_limit_truncates_the_queue():
    queue = executor.build_queue([_profile("P1", eans=list("12345"))], {"PROFILE_C"}, 3)

    assert len(queue) == 3


def test_levels_outside_the_wave_are_not_queued():
    profile = _profile("PD", level="PROFILE_D", eans=["1"])

    assert executor.build_queue([profile], {"PROFILE_C"}, 20) == []


def test_body_aligned_with_the_profile_has_no_divergence():
    assert executor.body_matches_profile(_body(), _profile("P1", eans=["1"])) == []


def test_body_with_another_tax_basis_diverges_from_the_profile():
    divergences = executor.body_matches_profile(
        _body(tributoIcms={"cstIcmsSaida": "000"}), _profile("P1", eans=["1"])
    )

    assert divergences == ["tributoIcms"]


def test_body_with_another_ncm_or_cfop_diverges_from_the_profile():
    divergences = executor.body_matches_profile(
        _body(codigoNcm="19059090", cdCfopSaida="5.102"), _profile("P1", eans=["1"])
    )

    assert set(divergences) == {"ncm", "cfopSaida"}


def test_zero_cost_still_requires_the_explicit_flag(monkeypatch):
    monkeypatch.delenv(executor.PENDING_COST_FLAG, raising=False)
    ok, reason = executor.validate_cost(0, {"cost_status": "PENDING"})

    assert not ok
    assert reason == "CUSTO_ZERO_SEM_AUTORIZACAO_EXPLICITA"


def test_zero_cost_passes_with_flag_and_pending_status(monkeypatch):
    monkeypatch.setenv(executor.PENDING_COST_FLAG, "true")
    ok, reason = executor.validate_cost(0, {"cost_status": "PENDING"})

    assert ok
    assert reason == "CUSTO_ZERO_AUTORIZADO"


def test_positive_cost_without_dfe_origin_is_refused(monkeypatch):
    monkeypatch.setenv(executor.PENDING_COST_FLAG, "true")
    ok, reason = executor.validate_cost(3.5, {"source": "PENDING_DFE"})

    assert not ok
    assert reason == "CUSTO_POSITIVO_SEM_ORIGEM_DFE"
