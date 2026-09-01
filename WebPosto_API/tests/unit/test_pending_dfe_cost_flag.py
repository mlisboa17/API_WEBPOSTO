"""Custo zero exige autorizacao explicita da execucao (sem rede, sem escrita)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_executor():
    """Carrega o executor por caminho: scripts/ nao e pacote importavel."""
    path = ROOT / "scripts" / "execute_microbatch_118508.py"
    spec = importlib.util.spec_from_file_location("execute_microbatch_118508", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


executor = _load_executor()

DFE_PRODUCT = {"custo": {"source": "DFE", "cost_status": "RESOLVED"}}
PENDING_PRODUCT = {
    "custo": {
        "source": "PENDING_DFE",
        "cost_status": "PENDING",
        "cost_risk": "ASSUMED_BY_OWNER",
        "requires_cost_update": True,
    }
}


@pytest.fixture(autouse=True)
def clear_flag(monkeypatch):
    monkeypatch.delenv(executor.PENDING_COST_FLAG, raising=False)


def test_positive_cost_from_dfe_is_accepted():
    ok, reason = executor.validate_cost(6.3878, DFE_PRODUCT)

    assert ok
    assert reason == "CUSTO_DFE"


def test_zero_cost_is_refused_without_the_flag():
    """Comportamento padrao preservado: custo zero nao passa."""
    ok, reason = executor.validate_cost(0, PENDING_PRODUCT)

    assert not ok
    assert reason == "CUSTO_ZERO_SEM_AUTORIZACAO_EXPLICITA"


def test_zero_cost_is_accepted_with_the_flag(monkeypatch):
    monkeypatch.setenv(executor.PENDING_COST_FLAG, "true")

    ok, reason = executor.validate_cost(0, PENDING_PRODUCT)

    assert ok
    assert reason == "CUSTO_ZERO_AUTORIZADO"


def test_flag_alone_does_not_authorize_product_without_pending_status(monkeypatch):
    monkeypatch.setenv(executor.PENDING_COST_FLAG, "true")

    ok, reason = executor.validate_cost(0, DFE_PRODUCT)

    assert not ok
    assert reason == "CUSTO_ZERO_SEM_STATUS_PENDENTE"


@pytest.mark.parametrize("value", ["", "false", "1", "yes", "TRUE_ISH"])
def test_only_the_exact_true_value_authorizes(monkeypatch, value):
    monkeypatch.setenv(executor.PENDING_COST_FLAG, value)

    ok, _ = executor.validate_cost(0, PENDING_PRODUCT)

    assert not ok


def test_flag_accepts_case_and_spacing_variations_of_true(monkeypatch):
    monkeypatch.setenv(executor.PENDING_COST_FLAG, " True ")

    assert executor.pending_cost_allowed()


def test_missing_and_negative_costs_are_refused():
    assert executor.validate_cost(None, PENDING_PRODUCT) == (False, "CUSTO_AUSENTE")
    assert executor.validate_cost(-1, PENDING_PRODUCT) == (False, "CUSTO_NEGATIVO")


def test_positive_cost_without_dfe_origin_is_refused():
    ok, reason = executor.validate_cost(5.0, PENDING_PRODUCT)

    assert not ok
    assert reason == "CUSTO_POSITIVO_SEM_ORIGEM_DFE"


def test_flag_is_not_persisted_in_env_file():
    """A autorizacao vale para o processo: nao pode estar no .env versionado."""
    for name in (".env", ".env.example"):
        path = ROOT / name
        if path.is_file():
            assert executor.PENDING_COST_FLAG not in path.read_text(encoding="utf-8", errors="ignore")
