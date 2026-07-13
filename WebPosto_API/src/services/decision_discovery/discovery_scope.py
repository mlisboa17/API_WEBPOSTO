"""Escopo multitenant para rotas /api/v1/discovery/* (Sprint 2)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request

from src.infrastructure.security.jwt_utils import decode_token
from src.services.multiselect_utils import parse_empresa_codigos
from src.services.owner_analysis_models import DETECTOR_SET_SIGNATURE
from src.services.tenant_discovery_service import TenantDiscoveryService


@dataclass(frozen=True)
class DiscoveryScope:
    """Portfólio autorizado + filtro efetivo da requisição."""

    authorized_empresa_codes: frozenset[int]
    requested_empresa_codes: frozenset[int]
    empresa_query: str | None

    @property
    def is_network_view(self) -> bool:
        return len(self.requested_empresa_codes) == 0

    def allows_tenant(self, tenant_id: str | int | None) -> bool:
        if tenant_id is None:
            return False
        text = str(tenant_id).strip()
        if not text.isdigit():
            return False
        code = int(text)
        if code not in self.authorized_empresa_codes:
            return False
        if self.is_network_view:
            return True
        return code in self.requested_empresa_codes

    def empresa_snapshot_suffix(self) -> str:
        if self.is_network_view:
            return "all"
        if len(self.requested_empresa_codes) == 1:
            return str(next(iter(self.requested_empresa_codes)))
        return ",".join(str(code) for code in sorted(self.requested_empresa_codes))

    def snapshot_filename_pattern(self) -> str:
        suffix = self.empresa_snapshot_suffix().replace(",", "_")
        return f"owner_analysis_last_valid_*_{DETECTOR_SET_SIGNATURE.replace(',', '_')}_{suffix}.json"


def extract_token_payload(request: Request | None) -> dict | None:
    if request is None:
        return None
    token = None
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        return decode_token(token)
    except Exception:
        return None


def _empresa_codes_from_token(payload: dict | None) -> list[int]:
    if not payload:
        return []
    extra = payload.get("extra") or {}
    for key in ("empresa_codigos", "empresaCodigo", "company_id"):
        raw = extra.get(key) or payload.get(key)
        if raw is None:
            continue
        codes = parse_empresa_codigos(raw)
        if codes:
            return codes
    return []


class DiscoveryScopeService:
    def __init__(self, tenant_discovery: TenantDiscoveryService | None = None) -> None:
        self._tenant_discovery = tenant_discovery or TenantDiscoveryService()

    async def resolve(
        self,
        empresa_codigo: str | None,
        *,
        request: Request | None = None,
    ) -> DiscoveryScope:
        discovery = await self._tenant_discovery.discover_tenants()
        authorized = frozenset(
            tenant.empresa_codigo
            for tenant in discovery.tenants_discovered
            if tenant.empresa_codigo > 0
        )
        if not authorized:
            raise HTTPException(
                status_code=403,
                detail="Portfólio corporativo indisponível para discovery",
            )

        requested_codes = parse_empresa_codigos(empresa_codigo)
        if not requested_codes:
            requested_codes = _empresa_codes_from_token(extract_token_payload(request))

        if requested_codes:
            unauthorized = set(requested_codes) - set(authorized)
            if unauthorized:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Empresa(s) fora do portfólio autorizado: "
                        + ", ".join(str(code) for code in sorted(unauthorized))
                    ),
                )
            requested = frozenset(requested_codes)
            empresa_query = empresa_codigo or ",".join(str(c) for c in sorted(requested))
        else:
            requested = frozenset()
            empresa_query = None

        return DiscoveryScope(
            authorized_empresa_codes=authorized,
            requested_empresa_codes=requested,
            empresa_query=empresa_query,
        )

    def assert_candidate_visible(self, scope: DiscoveryScope, candidate: dict) -> None:
        tenant = candidate.get("tenant") or candidate.get("tenant_id")
        if scope.allows_tenant(tenant):
            return
        raise HTTPException(
            status_code=403,
            detail="Decisão fora do escopo corporativo autorizado",
        )
