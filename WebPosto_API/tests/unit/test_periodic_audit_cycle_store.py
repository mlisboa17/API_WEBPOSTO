from datetime import date

import pytest

from src.services.periodic_audit_cycle_store import PeriodicAuditCycleStore


def test_creates_separate_pista_and_convenience_cycles(tmp_path):
    store = PeriodicAuditCycleStore(tmp_path / "cycles.json")
    pista = store.create("5555", "PISTA", 7, "Diretoria", date(2026, 7, 1))
    loja = store.create("5555", "LOJA", 15, "Diretoria", date(2026, 7, 1))

    assert pista.centro_custo == "PISTA"
    assert loja.centro_custo == "CONVENIENCIA"
    assert len(store.list_all()) == 2
    assert pista.proxima_auditoria(date(2026, 7, 8)) == date(2026, 7, 8)
    assert pista.status(date(2026, 7, 8)) == "VENCE_HOJE"


def test_cycle_can_be_deactivated(tmp_path):
    store = PeriodicAuditCycleStore(tmp_path / "cycles.json")
    item = store.create("11495", "PISTA", 7, "Auditor", date(2026, 7, 1))

    updated = store.set_active(item.id, False)

    assert updated is not None
    assert updated.ativo is False


def test_cycle_rejects_unlicensed_company(tmp_path):
    store = PeriodicAuditCycleStore(tmp_path / "cycles.json")
    with pytest.raises(ValueError, match="UNLICENSED_COMPANY"):
        store.create("999", "PISTA", 7, "Auditor", date(2026, 7, 1))


def test_cycle_creation_is_idempotent_for_same_scope(tmp_path):
    store = PeriodicAuditCycleStore(tmp_path / "cycles.json")
    first = store.create("5555", "PISTA", 7, "Diretoria", date(2026, 7, 27))
    second = store.create("5555", "PISTA", 7, "Diretoria", date(2026, 7, 27))
    assert first.id == second.id
    assert len(store.list_all()) == 1
