"""Helpers compartilhados — discovery multitenant."""

from __future__ import annotations

from typing import Any

from src.services.decision_discovery import DecisionDiscoveryEngine
from src.services.decision_discovery.discovery_scope import DiscoveryScope
from src.services.decision_discovery.models import DiscoveryResult
from src.services.tenant_discovery_service import TenantDiscoveryService


async def discover_for_scope(
    engine: DecisionDiscoveryEngine,
    scope: DiscoveryScope,
    *,
    data_inicial: str,
    data_final: str,
    top_n: int,
) -> DiscoveryResult:
    """Executa discovery apenas nos tenants autorizados pelo escopo."""
    discovery = await TenantDiscoveryService().discover_tenants()
    if scope.is_network_view:
        tenants = [
            tenant
            for tenant in discovery.tenants_discovered
            if scope.allows_tenant(tenant.tenant_id)
        ]
    else:
        tenants = [
            tenant
            for tenant in discovery.tenants_discovered
            if tenant.empresa_codigo in scope.requested_empresa_codes
        ]

    return await engine.discover_all_tenants(
        tenants,
        data_inicial=data_inicial,
        data_final=data_final,
        top_n=top_n,
    )


def discovery_response_data(result: DiscoveryResult, *, top_n: int) -> dict[str, Any]:
    if top_n == 1:
        return {
            "decision": result.top_decision.to_dict() if result.top_decision else None,
            "message": result.message,
            "execution_time_ms": result.execution_time_ms,
            "detectors_executed": result.detectors_executed,
        }
    return {
        "decisions": [candidate.to_dict() for candidate in result.all_candidates],
        "count": len(result.all_candidates),
        "message": result.message,
        "execution_time_ms": result.execution_time_ms,
        "detectors_executed": result.detectors_executed,
    }
