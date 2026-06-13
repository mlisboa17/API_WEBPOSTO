"""Testes Onda 1 — paridade registry Python ↔ manifest JSON."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app_core.filial_registry import discovery_summary, get_filiais_ativas, list_filiais

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "frontend" / "data" / "filiais.json"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST.exists(), "Execute: python scripts/sync_filiais_manifest.py"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_registry_count_matches_manifest(manifest: dict) -> None:
    registry = list_filiais()
    assert manifest["count"] == len(registry)
    assert len(manifest["filiais"]) == len(registry)


def test_unique_empresa_codigo(manifest: dict) -> None:
    codigos = [row["empresaCodigo"] for row in manifest["filiais"]]
    assert len(codigos) == len(set(codigos))


def test_active_filiais_consistent(manifest: dict) -> None:
    registry_active = {f.empresa_codigo for f in get_filiais_ativas()}
    manifest_active = {
        row["empresaCodigo"] for row in manifest["filiais"] if row.get("ativa") is True
    }
    assert registry_active == manifest_active


def test_no_filial_without_empresa_codigo(manifest: dict) -> None:
    for row in manifest["filiais"]:
        assert row.get("empresaCodigo")


def test_discovery_has_twelve_official() -> None:
    summary = discovery_summary()
    assert summary["oficiaisMaster"] == 12
    assert summary["registryCount"] == 12
    assert summary["codigosUnicos"] is True


def test_status_evidencia_preserved(manifest: dict) -> None:
    allowed = {"COMPROVADA", "PENDENTE_EVIDENCIA"}
    registry_by_code = {f.empresa_codigo: f for f in list_filiais()}
    for row in manifest["filiais"]:
        status = row.get("statusEvidencia")
        assert status in allowed
        assert registry_by_code[row["empresaCodigo"]].status_evidencia == status
    assert manifest["activeCount"] == sum(1 for row in manifest["filiais"] if row.get("ativa") is True)
    pendente_ativa = [
        row["empresaCodigo"]
        for row in manifest["filiais"]
        if row.get("statusEvidencia") == "PENDENTE_EVIDENCIA" and row.get("ativa") is True
    ]
    assert pendente_ativa == []
