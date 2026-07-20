"""Descoberta automática de tenants a partir de credenciais WebPosto."""

from __future__ import annotations

from dataclasses import dataclass, field
from src.utils.utc_datetime import utc_now_iso
from hashlib import sha256
from typing import Any

import httpx

from src.core.config import load_core_config
from src.core.logger import get_logger, log_structured
from src.core.management_scope import is_licensed_company
from src.core.webposto_credentials import WebPostoCredential, list_webposto_credentials
from src.services.performance.performance_metrics import performance_metrics
from src.services.snapshot_store import SnapshotStore

TENANT_REGISTRY_TTL_SECONDS = 3600


@dataclass(frozen=True)
class DiscoveredTenant:
    tenant_id: str
    tenant_name: str
    empresa_codigo: int
    credential_alias: str
    credential_fingerprint: str
    status: str = "DISCOVERED"
    error: str | None = None


@dataclass
class TenantDiscoveryResult:
    credentials_detected: int = 0
    tenants_discovered: list[DiscoveredTenant] = field(default_factory=list)
    tenants_failed: list[DiscoveredTenant] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


class TenantDiscoveryService:
    EMPRESAS_PATH = "/INTEGRACAO/EMPRESAS"

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self._config = load_core_config()
        self._registry_store = SnapshotStore("snapshots/tenant_registry", TENANT_REGISTRY_TTL_SECONDS)

    @staticmethod
    def _registry_key() -> str:
        return "tenant_registry:official_credentials"

    @staticmethod
    def _fingerprint(api_key: str) -> str:
        return sha256(api_key.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            for key in ("resultados", "data"):
                rows = payload.get(key)
                if isinstance(rows, list):
                    return [row for row in rows if isinstance(row, dict)]
        return []

    @staticmethod
    def _tenant_name(row: dict[str, Any]) -> str:
        for key in ("fantasia", "nomeFantasia", "razao", "razaoSocial", "nome"):
            value = str(row.get(key) or "").strip()
            if value:
                return value
        return "Unidade não identificada"

    async def _fetch_empresas_for_credential(
        self,
        credential: WebPostoCredential,
    ) -> tuple[list[dict[str, Any]], str | None]:
        timeout = httpx.Timeout(max(20.0, self._config.timeout_seconds), connect=5.0)
        params = {"CHAVE": credential.api_key}

        try:
            async with httpx.AsyncClient(
                base_url=self._config.webposto_base_url,
                timeout=timeout,
            ) as client:
                response = await client.get(self.EMPRESAS_PATH, params=params)
        except Exception as exc:
            return [], str(exc)[:220]

        if response.status_code in {401, 403}:
            return [], f"HTTP {response.status_code} — credencial sem acesso a EMPRESAS"

        if response.status_code >= 400:
            return [], f"HTTP {response.status_code} ao consultar EMPRESAS"

        try:
            payload = response.json()
        except Exception:
            return [], "Resposta EMPRESAS inválida"

        rows = self._rows(payload)
        if not rows:
            return [], "EMPRESAS retornou vazio para a credencial"

        return rows, None

    async def discover_tenants(
        self,
        *,
        empresa_codigo_filter: int | None = None,
        force_refresh: bool = False,
    ) -> TenantDiscoveryResult:
        cache_key = self._registry_key()
        if not force_refresh and empresa_codigo_filter is None:
            cached, expired = self._registry_store.load_stale(cache_key)
            if cached and not expired:
                performance_metrics.record_tenant_registry_hit()
                payload = cached.get("result") or {}
                return TenantDiscoveryResult(
                    credentials_detected=int(payload.get("credentials_detected") or 0),
                    tenants_discovered=[
                        DiscoveredTenant(**item) for item in payload.get("tenants_discovered") or []
                    ],
                    tenants_failed=[
                        DiscoveredTenant(**item) for item in payload.get("tenants_failed") or []
                    ],
                    limitations=list(payload.get("limitations") or []),
                )

        performance_metrics.record_tenant_registry_miss()
        result = await self._discover_tenants_live(empresa_codigo_filter=empresa_codigo_filter)

        if empresa_codigo_filter is None:
            self._registry_store.save(
                cache_key,
                {
                    "lastUpdated": utc_now_iso(),
                    "result": {
                        "credentials_detected": result.credentials_detected,
                        "tenants_discovered": [t.__dict__ for t in result.tenants_discovered],
                        "tenants_failed": [t.__dict__ for t in result.tenants_failed],
                        "limitations": result.limitations,
                    },
                },
            )
        return result

    async def _discover_tenants_live(
        self,
        *,
        empresa_codigo_filter: int | None = None,
    ) -> TenantDiscoveryResult:
        credentials = list_webposto_credentials()
        result = TenantDiscoveryResult(credentials_detected=len(credentials))

        if not credentials:
            result.limitations.append("Nenhuma credencial WebPosto oficial configurada")
            return result

        seen_empresa: set[int] = set()

        for credential in credentials:
            performance_metrics.record_empresas_request()
            rows, error = await self._fetch_empresas_for_credential(credential)
            fingerprint = self._fingerprint(credential.api_key)

            log_structured(
                self.logger,
                {
                    "event": "DISCOVERY_TENANT_TRACE",
                    "phase": "credential_probe",
                    "credential_alias": credential.env_key,
                    "credential_fingerprint": fingerprint,
                    "empresas_rows": len(rows),
                    "error": error,
                },
            )

            if error:
                result.tenants_failed.append(
                    DiscoveredTenant(
                        tenant_id="unknown",
                        tenant_name="Credencial não validada",
                        empresa_codigo=-1,
                        credential_alias=credential.env_key,
                        credential_fingerprint=fingerprint,
                        status="FAILED",
                        error=error,
                    )
                )
                continue

            for row in rows:
                raw_codigo = row.get("empresaCodigo") or row.get("codigo")
                if raw_codigo is None:
                    continue
                try:
                    empresa_codigo = int(raw_codigo)
                except (TypeError, ValueError):
                    continue

                if not is_licensed_company(empresa_codigo):
                    continue

                if empresa_codigo_filter is not None and empresa_codigo != empresa_codigo_filter:
                    continue

                if empresa_codigo in seen_empresa:
                    continue

                seen_empresa.add(empresa_codigo)
                tenant = DiscoveredTenant(
                    tenant_id=str(empresa_codigo),
                    tenant_name=self._tenant_name(row),
                    empresa_codigo=empresa_codigo,
                    credential_alias=credential.env_key,
                    credential_fingerprint=fingerprint,
                    status="VALIDATED",
                )
                result.tenants_discovered.append(tenant)

                log_structured(
                    self.logger,
                    {
                        "event": "DISCOVERY_TENANT_TRACE",
                        "phase": "tenant_validated",
                        "tenant_id": tenant.tenant_id,
                        "tenant_name": tenant.tenant_name,
                        "empresa_codigo": tenant.empresa_codigo,
                        "credential_alias": tenant.credential_alias,
                        "credential_fingerprint": fingerprint,
                    },
                )

        if not result.tenants_discovered and not result.tenants_failed:
            result.limitations.append("Nenhum tenant descoberto via EMPRESAS")

        return result
