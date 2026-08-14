"""Verificação de duplicidade (ativos + inativos) — FASE 5."""

from __future__ import annotations

from typing import Any

from .schemas import ProductAnalysis


class DuplicateChecker:
    """Verifica se EAN já existe em produtos ativos/inativos."""

    def __init__(
        self,
        active_products: dict[str, dict[str, Any]] | None = None,
        inactive_products: dict[str, dict[str, Any]] | None = None,
    ):
        self.active_products = active_products or {}
        self.inactive_products = inactive_products or {}

    def find_duplicate(self, ean: str) -> dict[str, Any] | None:
        """Retorna produto ativo ou inativo com o EAN, ou None."""
        ean_normalized = str(ean).strip()
        
        # Buscar em ativos
        if ean_normalized in self.active_products:
            return {
                "status": "ACTIVE",
                **self.active_products[ean_normalized],
            }
        
        # Buscar em inativos
        if ean_normalized in self.inactive_products:
            return {
                "status": "INACTIVE",
                **self.inactive_products[ean_normalized],
            }
        
        return None

    def check_and_update_analysis(
        self,
        analysis: ProductAnalysis,
    ) -> ProductAnalysis:
        """Atualiza análise com resultado de duplicidade."""
        duplicate = self.find_duplicate(analysis.ean)
        
        if duplicate:
            status = duplicate.get("status")
            if status == "ACTIVE":
                analysis.status = "BLOCKED"
                analysis.gate = "BLOCKED_ALREADY_REGISTERED_ACTIVE"
                analysis.validation_issues.append(
                    f"EAN {analysis.ean} já registrado como ativo: "
                    f"produtoCodigo={duplicate.get('produtoCodigo')}"
                )
                analysis.risk_level = "ALTO_RISCO"
            else:  # INACTIVE
                analysis.status = "REVIEW_REQUIRED"
                analysis.validation_issues.append(
                    f"EAN {analysis.ean} encontrado como inativo: "
                    f"produtoCodigo={duplicate.get('produtoCodigo')} — "
                    "verificar se deve reativar ou criar novo"
                )
                analysis.risk_level = "MÉDIO_RISCO"
        
        return analysis
