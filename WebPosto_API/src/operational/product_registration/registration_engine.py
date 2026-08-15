"""Fachada publica do motor permanente de cadastro."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .audit import RegistrationAuditTrail
from .company_credentials import resolve_credential
from .dfe_cost_resolver import cost_from_index
from .engine_schemas import ProductRegistrationRequest, ProductRegistrationResult, RiskAuthorization
from .final_wave import pick_icms_row
from .gateway import ProductPostVerifier, WebPostoRegistrationGateway
from .policies.execution_policy import ExecutionPolicy
from .preflight import ProductPreflightService
from .stores import RegistrationCheckpointStore, RegistrationLockStore


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
    ) -> None:
        self.checkpoint = RegistrationCheckpointStore(checkpoint_path)
        self.lock = RegistrationLockStore(lock_path or checkpoint_path.with_name("wave_lock.json"))
        self.preflight_service = ProductPreflightService(self.checkpoint)
        self.gateway = gateway
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
        if self.gateway is None:
            preview.mensagem = "Gateway ausente; escrita recusada nesta consolidacao"
            preview.status = "PREFLIGHT_BLOCKED"
            preview.riscos.append("NO_GATEWAY")
            return preview
        raise RuntimeError("Escrita real deve passar pelo executor de onda com gateway injetado")

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
