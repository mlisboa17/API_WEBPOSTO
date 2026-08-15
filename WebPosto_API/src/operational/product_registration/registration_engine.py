"""Fachada publica do motor permanente de cadastro."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx

from .audit import RegistrationAuditTrail
from .company_credentials import resolve_credential
from .dfe_cost_resolver import cost_from_index
from .engine_schemas import ProductRegistrationRequest, ProductRegistrationResult, RiskAuthorization
from .final_wave import pick_icms_row
from .gateway import (
    ProductPostVerifier,
    WebPostoRegistrationGateway,
    find_recent_by_ean,
)
from .policies.execution_policy import ExecutionPolicy
from .preflight import ProductPreflightService
from .stores import RegistrationCheckpointStore, RegistrationLockStore

DEFAULT_BASE_URL = "https://web.qualityautomacao.com.br"


class CompanyCredentialResolver:
    """Exige correspondencia exata. Nunca registra o valor da credencial."""

    def resolve(self, empresa: int, env: dict[str, str] | None = None):
        return resolve_credential(empresa, env=env)


class DfeCostResolver:
    """Custo somente de NF-e autorizada, nao cancelada, EAN exato, mais recente."""

    def from_index(self, ean: str, index: dict[str, tuple]):
        return cost_from_index(ean, index)


class FiscalProfileResolver:
    """Nunca aplica perfil so por prefixo de NCM."""

    def pick_icms(self, rows, *, verified_references, expected_cst_entrada=None, expected_rate=None):
        return pick_icms_row(
            rows,
            verified_references=verified_references,
            expected_cst_entrada=expected_cst_entrada,
            expected_rate=expected_rate,
        )


class RegistrationBatchExecutor:
    """Execucao sequencial com checkpoint apos cada produto e skip pre-POST continuo."""

    def __init__(
        self,
        service: "ProductRegistrationService",
        lock: RegistrationLockStore,
        *,
        execution_policy: ExecutionPolicy | None = None,
    ) -> None:
        self.service = service
        self.lock = lock
        self.policy = execution_policy or ExecutionPolicy()

    def run(self, requests: list[ProductRegistrationRequest], batch_id: str) -> dict[str, Any]:
        results: list[ProductRegistrationResult] = []
        planned = sum(1 for item in requests if item.authorization.execute)
        lock_decision = self.policy.should_create_lock(planned)
        if lock_decision.allowed:
            started = self.lock.create_running_if_posts(planned, batch_id)
            if not started and not self.lock.can_start()[0]:
                return {"status": "LOCKED", "results": [], "posts": 0}
        posts = 0
        created = 0
        skipped = 0
        halted = None
        for request in requests:
            result = (
                self.service.register(request, request.authorization)
                if request.authorization.execute
                else self.service.preflight(request)
            )
            results.append(result)
            if result.status == "SKIPPED_PRE_POST":
                skipped += 1
                continue
            if result.status == "PREFLIGHT_BLOCKED":
                skipped += 1
                continue
            if result.post_enviado:
                posts += 1
            if result.status == "CREATED_AND_VERIFIED":
                created += 1
            outcome = self.policy.on_post_outcome(result.status)
            if not outcome.allowed:
                halted = result.status
                break
        final = "COMPLETED" if not halted else "PARTIAL"
        if lock_decision.allowed and posts:
            self.lock.persist(
                status=final,
                post_count=posts,
                created=created,
                skipped=skipped,
                halted_reason=halted,
                batch_id=batch_id,
            )
        return {
            "status": final if planned else "DRY_RUN",
            "results": results,
            "posts": posts,
            "created": created,
            "skipped": skipped,
            "halted": halted,
        }


class ProductRegistrationService:
    """Fachada: preflight, register, verify, resume e status."""

    def __init__(
        self,
        checkpoint_path: Path,
        lock_path: Path | None = None,
        *,
        gateway: WebPostoRegistrationGateway | None = None,
        verifier: ProductPostVerifier | None = None,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self.checkpoint = RegistrationCheckpointStore(checkpoint_path)
        self.lock = RegistrationLockStore(lock_path or checkpoint_path.with_name("wave_lock.json"))
        self.preflight_service = ProductPreflightService(self.checkpoint)
        self.base_url = base_url
        self.gateway = gateway or WebPostoRegistrationGateway(base_url)
        self.verifier = verifier
        self.audit = RegistrationAuditTrail()
        self.credentials = CompanyCredentialResolver()
        self.costs = DfeCostResolver()
        self.fiscal = FiscalProfileResolver()

    def preflight(self, request: ProductRegistrationRequest, **kwargs: Any) -> ProductRegistrationResult:
        result = self.preflight_service.run(request, **kwargs)
        self.audit.record("preflight", ean=request.ean, extra={"status": result.status})
        return result

    def register(
        self,
        request: ProductRegistrationRequest,
        authorization: RiskAuthorization | None = None,
        **kwargs: Any,
    ) -> ProductRegistrationResult:
        if authorization is not None:
            request = request.model_copy(update={"authorization": authorization})
        preview = self.preflight(request, **kwargs)
        if preview.status != "DRY_RUN":
            return preview
        if not request.authorization.execute:
            return preview
        raise RuntimeError(
            "register() com execute exige post_product() via esta fachada; "
            "scripts nao podem chamar o gateway diretamente"
        )

    def post_product(
        self,
        client: httpx.Client,
        reader: Any,
        key: str,
        body: dict[str, Any],
        *,
        ean: str,
        from_code: int,
        pause_seconds: float = 1.5,
    ) -> tuple[str, httpx.Response | None, dict[str, Any] | None, str | None]:
        """Unico caminho operacional de POST. Timeout resolve por GET."""
        if "empresaCodigo" in body:
            raise ValueError("empresaCodigo e proibido no body do endpoint legado")
        self.audit.record("post_attempt", ean=ean, extra={"from_code": from_code})
        for attempt in (1, 2, 3):
            try:
                response = self.gateway.post_once(client, key, body)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                existing = find_recent_by_ean(reader, key, ean, from_code)
                if existing is not None:
                    return "TIMEOUT_BUT_CREATED", None, existing, str(exc)
                if attempt == 3:
                    return "TIMEOUT_UNCONFIRMED", None, None, str(exc)
                time.sleep(pause_seconds * attempt)
                continue
            if response.status_code == 429 and attempt < 3:
                time.sleep(self.gateway.wait_retry_after(response))
                continue
            return "RESPONSE", response, None, None
        return "TIMEOUT_UNCONFIRMED", None, None, "tentativas esgotadas"

    async def post_once_async(self, client: httpx.AsyncClient, key: str, body: dict[str, Any]):
        if "empresaCodigo" in body:
            raise ValueError("empresaCodigo e proibido no body do endpoint legado")
        return await self.gateway.post_once_async(client, key, body)

    def verify(self, product_code: int, expected: dict[str, Any], *, key: str) -> dict[str, Any]:
        if self.verifier is None:
            raise RuntimeError("Verifier nao configurado")
        return self.verifier.verify(
            key,
            produto_codigo=product_code,
            ean=str(expected["ean"]),
            expected_ncm=str(expected["ncm"]),
            expected_cest=expected.get("cest"),
            expected_sale=float(expected["preco_venda"]),
            expected_cost=float(expected["preco_custo"]),
        )

    def resume(self, batch_id: str) -> dict[str, Any]:
        lock = self.lock.load()
        if lock.get("status") != "RUNNING":
            return {"ok": False, "reason": "BATCH_NOT_RUNNING", "batch_id": batch_id}
        return {"ok": True, "batch_id": batch_id, "lock": {k: v for k, v in lock.items() if k != "key"}}

    def status(self, batch_id: str) -> dict[str, Any]:
        lock = self.lock.load()
        return {
            "batch_id": batch_id,
            "lock": lock,
            "checkpoint_records": len(self.checkpoint.load()),
        }
