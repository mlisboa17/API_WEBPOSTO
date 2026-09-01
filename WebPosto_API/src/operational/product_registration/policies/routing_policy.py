"""Politica de roteamento: empresa exata, sem fallback, CHAVE_ONLY."""

from __future__ import annotations

from .decision import PolicyDecision

POLICY_NAME = "routing_policy"
POLICY_VERSION = "1.0.0"


class RoutingPolicy:
    """Impede o incidente 2481344: chave de outra filial grava sem erro HTTP."""

    name = POLICY_NAME
    version = POLICY_VERSION

    def evaluate(
        self,
        *,
        requested_company: int,
        resolved_company: int | None,
        resolved_variable: str | None,
        body_has_empresa_codigo: bool,
        query_has_empresa_codigo: bool,
    ) -> PolicyDecision:
        reasons: list[str] = []
        allowed = True
        if resolved_company is None:
            allowed = False
            reasons.append("Credencial nao resolvida para a empresa informada")
        elif int(requested_company) != int(resolved_company):
            allowed = False
            reasons.append(
                f"Empresa pedida {requested_company} difere da resolvida {resolved_company}"
            )
        if body_has_empresa_codigo or query_has_empresa_codigo:
            allowed = False
            reasons.append("empresaCodigo e proibido no body e na query do endpoint legado")
        if allowed:
            reasons.append("CHAVE_ONLY com correspondencia exata da empresa")
        return PolicyDecision(
            policy_name=POLICY_NAME,
            policy_version=POLICY_VERSION,
            inputs={
                "requested_company": requested_company,
                "resolved_company": resolved_company,
                "resolved_variable": resolved_variable,
                "routing": "CHAVE_ONLY",
            },
            decision="ROUTE_OK" if allowed else "ROUTE_REJECTED",
            confidence="HIGH",
            reasons=reasons,
            allowed=allowed,
        )
