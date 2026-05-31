from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Iterable

from pydantic import BaseModel, Field, field_validator


class TaxContext(BaseModel):
    cnpj: str = Field(..., min_length=14, max_length=18)
    regime: str
    cnae: str = Field(..., min_length=7, max_length=7)
    uf: str = Field(..., min_length=2, max_length=2)

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj(cls, value: str) -> str:
        digits = "".join(char for char in value if char.isdigit())
        if len(digits) != 14:
            raise ValueError("CNPJ must contain 14 digits")
        return value

    @field_validator("cnae")
    @classmethod
    def validate_cnae(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 7:
            raise ValueError("CNAE must be 7 digits")
        return value

    @field_validator("uf")
    @classmethod
    def validate_uf(cls, value: str) -> str:
        normalized = value.upper()
        if len(normalized) != 2 or not normalized.isalpha():
            raise ValueError("UF must be a 2-letter code")
        return normalized


class TaxMatrix(BaseModel):
    ncm: str = Field(..., min_length=8, max_length=8)
    cst: str = Field(..., min_length=3, max_length=3)
    monofasico: bool = False
    aliquota_pis: Decimal = Decimal("0")
    aliquota_cofins: Decimal = Decimal("0")

    @field_validator("ncm")
    @classmethod
    def validate_ncm(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 8:
            raise ValueError("NCM must be 8 digits")
        return value

    @field_validator("cst")
    @classmethod
    def validate_cst(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 3:
            raise ValueError("CST must be 3 digits")
        return value


class ProductAuditInput(BaseModel):
    sku: str
    descricao: str
    ncm: str | None = None
    cst: str | None = None
    regime: str
    preco_venda: Decimal = Decimal("0")
    custo: Decimal = Decimal("0")
    taxa_cartao: Decimal = Decimal("0")
    centro_custo: Decimal = Decimal("0")
    quantidade: Decimal = Decimal("1")
    pis_pago: Decimal = Decimal("0")
    cofins_pago: Decimal = Decimal("0")

    @field_validator("ncm")
    @classmethod
    def validate_optional_ncm(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.isdigit() or len(value) != 8:
            raise ValueError("NCM must be 8 digits")
        return value


class AuditFinding(BaseModel):
    sku: str
    severity: str
    message: str
    recoverable_credit: Decimal = Decimal("0")
    risk_score: int = 0
    suggested_ncm: str | None = None
    audit_hash: str


@dataclass(frozen=True)
class AdelaideAuditTrail:
    sku: str
    message: str
    payload_hash: str


class AdelaideEngine:
    """Domain engine for tax consistency, recovery and immutable audit findings."""

    def __init__(self, ncm_catalog: dict[str, str] | None = None):
        self.ncm_catalog = ncm_catalog or {
            "22030000": "Cerveja de malte",
            "22021000": "Bebidas não alcoólicas",
            "27101932": "Gasolina C comum",
        }

    def validate_cst_for_regime(self, context: TaxContext, matrix: TaxMatrix) -> bool:
        if matrix.monofasico and context.regime.upper().replace(" ", "_") == "LUCRO_REAL":
            return matrix.cst == "060"
        return True

    def detect_convenience_ncm(self, product: ProductAuditInput) -> str | None:
        if not product.ncm:
            return None
        normalized = product.descricao.lower()
        if "cerv" in normalized or "cerveja" in normalized:
            return "22030000"
        if "refri" in normalized or "refrigerante" in normalized:
            return "22021000"
        return product.ncm if product.ncm in self.ncm_catalog else None

    def compute_recoverable_credit(self, product: ProductAuditInput, matrix: TaxMatrix) -> Decimal:
        try:
            if not matrix.monofasico:
                return Decimal("0")
            paid = product.pis_pago + product.cofins_pago
            expected = Decimal("0")
            recoverable = (paid - expected) * product.quantidade
            return max(recoverable, Decimal("0"))
        except (InvalidOperation, TypeError):
            return Decimal("0")

    def compute_real_margin(self, product: ProductAuditInput) -> Decimal:
        try:
            denominator = product.preco_venda if product.preco_venda else Decimal("0")
            if denominator == 0:
                return Decimal("0")
            net = product.preco_venda - (
                product.custo + product.taxa_cartao + product.centro_custo + product.pis_pago + product.cofins_pago
            )
            return ((net / denominator) * Decimal("100")).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ZeroDivisionError):
            return Decimal("0")

    def build_audit_hash(self, parts: Iterable[str]) -> str:
        payload = "|".join(parts)
        return sha256(payload.encode("utf-8")).hexdigest()

    def audit_product(self, context: TaxContext, product: ProductAuditInput, matrix: TaxMatrix) -> AuditFinding:
        suggested_ncm = self.detect_convenience_ncm(product)
        severity = "ok"
        message = "Matriz tributária consistente"
        risk_score = 18

        if not product.ncm:
            severity = "critico"
            message = "Item sem NCM cadastrado"
            risk_score = 92
        elif suggested_ncm and suggested_ncm != product.ncm:
            severity = "critico"
            message = "NCM divergente da descrição do produto"
            risk_score = 81
        elif not self.validate_cst_for_regime(context, matrix):
            severity = "alto"
            message = "CST incompatível com regime tributário"
            risk_score = 74
        elif matrix.monofasico and (product.pis_pago > 0 or product.cofins_pago > 0):
            severity = "credito"
            message = "Possível bitributação de PIS/COFINS monofásico"
            risk_score = 63

        recoverable = self.compute_recoverable_credit(product, matrix)
        audit_hash = self.build_audit_hash([
            context.cnpj,
            product.sku,
            product.descricao,
            product.ncm or "SEM_NCM",
            severity,
            str(recoverable),
        ])
        return AuditFinding(
            sku=product.sku,
            severity=severity,
            message=message,
            recoverable_credit=recoverable,
            risk_score=risk_score,
            suggested_ncm=suggested_ncm,
            audit_hash=audit_hash,
        )
