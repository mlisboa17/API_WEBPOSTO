"""Preflight: valida campos, empresa, checkpoint, existencia e gates."""

from __future__ import annotations

from typing import Any

from .company_credentials import resolve_credential
from .duplicate_detection import DuplicateDetectionService
from .engine_schemas import ProductRegistrationRequest, ProductRegistrationResult
from .gtin_service import GtinValidationService
from .policies.cost_policy import CostPolicy
from .policies.fiscal_policy import FiscalPolicy
from .policies.routing_policy import RoutingPolicy
from .registration_body import RegistrationBodyBuilder
from .stores import RegistrationCheckpointStore


class ProductPreflightService:
    """Produz body_preview e hash sem escrever na API."""

    def __init__(
        self,
        checkpoint: RegistrationCheckpointStore,
        *,
        gtin: GtinValidationService | None = None,
        duplicates: DuplicateDetectionService | None = None,
        body_builder: RegistrationBodyBuilder | None = None,
        cost_policy: CostPolicy | None = None,
        routing_policy: RoutingPolicy | None = None,
        fiscal_policy: FiscalPolicy | None = None,
    ) -> None:
        self.checkpoint = checkpoint
        self.gtin = gtin or GtinValidationService()
        self.duplicates = duplicates or DuplicateDetectionService()
        self.body_builder = body_builder or RegistrationBodyBuilder()
        self.cost_policy = cost_policy or CostPolicy()
        self.routing_policy = routing_policy or RoutingPolicy()
        self.fiscal_policy = fiscal_policy or FiscalPolicy()

    def run(
        self,
        request: ProductRegistrationRequest,
        *,
        catalog: list[dict[str, Any]] | None = None,
        catalog_by_ean: dict[str, dict[str, Any]] | None = None,
        env: dict[str, str] | None = None,
    ) -> ProductRegistrationResult:
        decisions: list[dict[str, Any]] = []
        riscos: list[str] = []

        try:
            credential = resolve_credential(request.empresa, env=env)
            resolved_company = credential.empresa_codigo
            resolved_variable = credential.variable_name
        except Exception as exc:
            resolved_company = None
            resolved_variable = None
            riscos.append(str(exc))

        routing = self.routing_policy.evaluate(
            requested_company=request.empresa,
            resolved_company=resolved_company,
            resolved_variable=resolved_variable,
            body_has_empresa_codigo=False,
            query_has_empresa_codigo=False,
        )
        decisions.append(routing.model_dump())
        if not routing.allowed:
            return self._blocked(request, "ROTEAMENTO", decisions, riscos)

        gtin = self.gtin.validate(request.ean)
        if not gtin["ok"]:
            riscos.extend(str(item) for item in gtin["issues"])
            return self._blocked(request, "GTIN", decisions, riscos)

        existing = self.checkpoint.get(request.ean)
        if existing:
            return ProductRegistrationResult(
                status="ALREADY_REGISTERED",
                ean=request.ean,
                empresa=request.empresa,
                produto_codigo=existing.get("codProduto") or existing.get("produto_existente"),
                checkpoint={"ean": request.ean, "status": existing.get("status")},
                evidencias={"checkpoint": existing.get("status")},
                decisions=decisions,
                dry_run=not request.authorization.execute,
                mensagem="EAN ja presente no checkpoint",
            )

        if catalog_by_ean and request.ean in catalog_by_ean:
            found = catalog_by_ean[request.ean]
            return ProductRegistrationResult(
                status="ALREADY_REGISTERED",
                ean=request.ean,
                empresa=request.empresa,
                produto_codigo=found.get("produtoCodigo"),
                decisions=decisions,
                dry_run=True,
                mensagem="EAN ja existe no catalogo",
            )

        if catalog:
            duplicate = self.duplicates.classify_description(
                request.descricao,
                catalog,
                candidate_family=request.familia_comercial,
            )
            if duplicate.get("decision"):
                decisions.append(duplicate["decision"].model_dump())
                if duplicate["action"] != "CONTINUE":
                    return ProductRegistrationResult(
                        status="SKIPPED_PRE_POST",
                        ean=request.ean,
                        empresa=request.empresa,
                        produto_codigo=(duplicate["matches"][0] or {}).get("produtoCodigo"),
                        decisions=decisions,
                        riscos=[duplicate["decision"].decision],
                        dry_run=True,
                        mensagem=duplicate["action"],
                    )

        if request.preco_venda <= 0:
            return self._blocked(request, "PRECO_VENDA_INVALIDO", decisions, riscos)

        ncm_declared = self.fiscal_policy.empty_is_not_zero("ncm", request.ncm)
        decisions.append(ncm_declared.model_dump())
        if not ncm_declared.allowed:
            return self._blocked(request, "NCM_AUSENTE", decisions, riscos)

        if not request.perfil_fiscal.get("tributo_icms"):
            return self._blocked(request, "PAYLOAD_FISCAL_AUSENTE", decisions, riscos)
        if request.authorization.accept_fiscal_risk is False and request.perfil_fiscal.get(
            "requires_accountant_review"
        ):
            fiscal = self.fiscal_policy.accept_owner_inference(
                selection_reason=str(request.perfil_fiscal.get("selection_reason") or "INFERENCIA"),
                accept_fiscal_risk=False,
            )
            decisions.append(fiscal.model_dump())
            return self._blocked(request, "RISCO_FISCAL_NAO_ACEITO", decisions, riscos)

        cost = self.cost_policy.evaluate(
            cost=request.custo,
            cost_source=request.cost_source,
            cost_status=request.cost_status,
            sale_price=request.preco_venda,
            allow_pending_dfe_cost=request.authorization.allow_pending_dfe_cost,
            accept_negative_margin=request.authorization.accept_negative_margin,
        )
        decisions.append(cost.model_dump())
        if not cost.allowed:
            return self._blocked(request, cost.decision, decisions, riscos)

        body = self.body_builder.build(request)
        body_hash = self.body_builder.hash(body)
        return ProductRegistrationResult(
            status="DRY_RUN",
            ean=request.ean,
            empresa=request.empresa,
            body_hash=body_hash,
            body_sanitized=self.body_builder.sanitize(body),
            decisions=decisions,
            evidencias=self.cost_policy.sanitize_evidence(request.cost_evidence),
            dry_run=True,
            mensagem="Preflight aprovado; escrita exige --execute",
        )

    def _blocked(
        self,
        request: ProductRegistrationRequest,
        reason: str,
        decisions: list[dict[str, Any]],
        riscos: list[str],
    ) -> ProductRegistrationResult:
        return ProductRegistrationResult(
            status="PREFLIGHT_BLOCKED",
            ean=request.ean,
            empresa=request.empresa,
            decisions=decisions,
            riscos=[*riscos, reason],
            dry_run=True,
            mensagem=reason,
        )
