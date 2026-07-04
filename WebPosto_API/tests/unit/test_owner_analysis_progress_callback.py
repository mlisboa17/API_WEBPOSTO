from __future__ import annotations

import pytest

from src.services.decision_discovery.discovery_engine import DecisionDiscoveryEngine
from src.services.tenant_discovery_service import DiscoveredTenant


def _tenant(tenant_id: str, empresa: int) -> DiscoveredTenant:
    return DiscoveredTenant(
        tenant_id=tenant_id,
        tenant_name=f"Posto {tenant_id}",
        empresa_codigo=empresa,
        credential_alias="cred",
        credential_fingerprint="fp",
    )


@pytest.mark.asyncio
async def test_tenant_progress_callback_sequence_and_failed_count() -> None:
    engine = DecisionDiscoveryEngine()
    calls: list[tuple[str, int, int]] = []
    failures = 0

    async def on_progress(record, completed: int, total: int) -> None:
        calls.append((record.status, completed, total))
        nonlocal failures
        if record.status == "FAILED":
            failures += 1

    tenants = [_tenant("5555", 5555), _tenant("11495", 11495), _tenant("74014", 74014)]
    attempts = 0

    async def mock_execute(tenant_code: str, data_inicial: str, data_final: str, **kwargs):
        nonlocal attempts
        attempts += 1
        if tenant_code == "74014":
            raise RuntimeError("tenant failed")
        return []

    engine._execute_detectors = mock_execute  # type: ignore[method-assign]

    result = await engine.discover_all_tenants(
        tenants=tenants,
        data_inicial="2026-06-26",
        data_final="2026-07-03",
        on_tenant_progress=on_progress,
    )

    assert calls == [
        ("ANALYZED", 1, 3),
        ("ANALYZED", 2, 3),
        ("FAILED", 3, 3),
    ]
    assert failures == 1
    assert len(result.tenant_records) == 3
    assert sum(1 for r in result.tenant_records if r.status == "ANALYZED") == 2
    assert sum(1 for r in result.tenant_records if r.status == "FAILED") == 1
