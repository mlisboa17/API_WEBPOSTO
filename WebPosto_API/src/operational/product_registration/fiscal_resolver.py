"""Classificação fiscal automática — FASE 5."""

from __future__ import annotations

from typing import Any

from .schemas import ProductAnalysis


class FiscalResolver:
    """Resolve modelo fiscal baseado em NCM, descrição, regime, UF."""

    # Modelo BONO aplicável (comprovado)
    BONO_MODEL = {
        "category": "BISCOITO_RECHEADO",
        "aplicavel_a": [
            "biscoitos",
            "chocolates",
            "bebidas leve processada",
            "doces embalados",
        ],
        "bloqueado_para": [
            "combustíveis",
            "medicamentos",
            "cigarros",
            "pilhas",
            "brinquedos",
            "bebidas alcóolicas",
            "higiene",
        ],
        "ncm_range": ["19000000", "19059900"],
        "tributo_icms": {
            "cstEntrada": "060",
            "cstSaida": "060",
            "percentualIcmsEntrada": 0.0,
            "percentualIcmsSaida": 0.0,
            "dsCsosnEntrada": "0",
            "dsCsosnSaida": "0",
        },
        "tributo_pis_cofins": {
            "cstPisEntrada": "50",
            "cstPisSaida": "01",
            "percentualPisEntrada": 0.65,
            "percentualPisSaida": 0.65,
            "percentualBaseCalculoPisEntrada": 100,
            "percentualBaseCalculoPisSaida": 100,
            "cstCofinsEntrada": "50",
            "cstCofinsSaida": "01",
            "percentualCofinsEntrada": 3.0,
            "percentualCofinsSaida": 3.0,
            "percentualBaseCalculoCofinsEntrada": 100,
            "percentualBaseCalculoCofinsEntrada": 100,
        },
    }

    BLOCKED_KEYWORDS = [
        "combustível",
        "gasolina",
        "álcool",
        "gás",
        "medicamento",
        "cigarro",
        "cigarrilha",
    ]

    def __init__(self):
        self.models: dict[str, dict[str, Any]] = {
            "BISCOITO_RECHEADO": self.BONO_MODEL,
        }

    def check_blocked(self, description: str) -> str | None:
        """Verifica se produto está bloqueado por palavras-chave."""
        desc_lower = description.lower()
        for keyword in self.BLOCKED_KEYWORDS:
            if keyword in desc_lower:
                return f"BLOCKED_KEYWORD_{keyword.upper()}"
        return None

    def resolve(
        self,
        analysis: ProductAnalysis,
        ncm: str | None = None,
        description: str = "",
    ) -> ProductAnalysis:
        """Atribui modelo fiscal ou bloqueia."""
        
        # Verificar bloqueios
        blocked = self.check_blocked(description)
        if blocked:
            analysis.status = "BLOCKED"
            analysis.gate = blocked
            analysis.validation_issues.append(f"Produto bloqueado: {blocked}")
            analysis.risk_level = "ALTO_RISCO"
            return analysis

        # NCM obrigatório
        if not ncm:
            analysis.status = "REVIEW_REQUIRED"
            analysis.validation_issues.append("NCM não informado")
            analysis.risk_level = "ALTO_RISCO"
            return analysis

        # Normalizar NCM (8 dígitos)
        ncm_normalized = "".join(c for c in ncm if c.isdigit()).zfill(8)[-8:]
        analysis.ncm = ncm_normalized

        # Aplicar BONO para alimentos/biscoitos
        if ncm_normalized.startswith("19"):  # Alimentos processados
            analysis.tributo_icms = self.BONO_MODEL["tributo_icms"]
            analysis.tributo_pis_cofins = self.BONO_MODEL["tributo_pis_cofins"]
            analysis.field_provenance["icms_model"] = {
                "source": "FISCAL_RESOLVER_BONO",
                "confidence": "HIGH",
            }
            analysis.field_provenance["pis_cofins_model"] = {
                "source": "FISCAL_RESOLVER_BONO",
                "confidence": "HIGH",
            }

        return analysis
