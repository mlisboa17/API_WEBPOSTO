from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, getcontext
from hashlib import sha256
from typing import Iterable, List, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.entities.tax_audit import FiscalMatrix, SaleAuditRecord, TaxDiscrepancy


getcontext().prec = 28
FOUR_DECIMALS = Decimal("0.0001")
MONOFASICO_PREFIXES = ("15", "22")


def quantize_decimal(value: Decimal) -> Decimal:
    return value.quantize(FOUR_DECIMALS, rounding=ROUND_HALF_UP)


class TaxAPIClient(Protocol):
    async def fetch_ncm_and_rate(self, sku: str) -> dict:
        """Return fiscal lookup data without coupling the app layer to external providers."""


class SaleRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    sku: str
    description: str = Field(default="ITEM SEM DESCRICAO")
    ncm: str
    cest: str | None = None
    cst: str = "01"
    cnae: str = "4731800"
    regime: str = "LUCRO_REAL"
    uf: str = "PE"
    tax_rate: Decimal
    price: Decimal
    cost: Decimal = Decimal("0.0000")
    effective_tax: Decimal = Decimal("0.0000")
    card_fee: Decimal = Decimal("0.0000")
    cost_center: Decimal = Decimal("0.0000")
    quantity: int
    sold_at: datetime

    @field_validator("tax_rate", "price", "cost", "effective_tax", "card_fee", "cost_center")
    @classmethod
    def quantize_values(cls, value: Decimal) -> Decimal:
        return quantize_decimal(value)


def is_monofasico_candidate(record: SaleRecord, matrix: FiscalMatrix) -> bool:
    return matrix.monofasico or record.ncm.startswith(MONOFASICO_PREFIXES)


def regime_factor(regime: str) -> Decimal:
    normalized = regime.upper().replace(" ", "_")
    if normalized == "LUCRO_REAL":
        return Decimal("1.0000")
    return Decimal("0.3500")


def validate_ncm_cest(record: SaleRecord, matrix: FiscalMatrix) -> list[str]:
    findings: list[str] = []
    if record.ncm != matrix.ncm:
        findings.append("NCM divergente da base nacional 2026")
    if record.uf.upper() == "PE" and matrix.cest and record.cest and record.cest != matrix.cest:
        findings.append("CEST divergente das regras de PE")
    if record.uf.upper() == "PE" and matrix.ncm.startswith("00"):
        findings.append("NCM genérico com exposição SEFAZ")
    return findings


def compute_real_margin(record: SaleRecord) -> Decimal:
    gross = quantize_decimal(record.price * Decimal(record.quantity))
    if gross <= 0:
        return Decimal("0.0000")
    net = gross - record.cost - record.effective_tax - record.card_fee - record.cost_center
    return quantize_decimal((net / gross) * Decimal("100"))


def build_matrix_from_payload(record: SaleRecord, payload: dict) -> FiscalMatrix:
    national_rate = quantize_decimal(Decimal(str(payload.get("rate", record.tax_rate))))
    pis_rate = quantize_decimal(Decimal(str(payload.get("aliquota_pis", national_rate * Decimal("0.1784")))))
    cofins_rate = quantize_decimal(Decimal(str(payload.get("aliquota_cofins", national_rate * Decimal("0.8216")))))
    return FiscalMatrix(
        uf=str(payload.get("uf", record.uf)).upper(),
        regime=record.regime.upper().replace(" ", "_"),
        cnae=str(payload.get("cnae", record.cnae)),
        ncm=str(payload.get("ncm", record.ncm)),
        cest=payload.get("cest", record.cest),
        cst=str(payload.get("cst", record.cst)),
        monofasico=bool(payload.get("monofasico", str(payload.get("ncm", record.ncm)).startswith(MONOFASICO_PREFIXES))),
        aliquota_pis=pis_rate,
        aliquota_cofins=cofins_rate,
        aliquota_icms=quantize_decimal(Decimal(str(payload.get("aliquota_icms", "18.0000")))),
        effective_tax_rate=national_rate,
        source=str(payload.get("source", "BASE_NACIONAL_2026_PE")),
    )


def calculate_recoverable_credit(record: SaleRecord, matrix: FiscalMatrix) -> Decimal:
    if not is_monofasico_candidate(record, matrix):
        return Decimal("0.0000")
    gross = quantize_decimal(record.price * Decimal(record.quantity))
    effective_rate = quantize_decimal(matrix.aliquota_pis + matrix.aliquota_cofins)
    recoverable = gross * (effective_rate / Decimal("100")) * regime_factor(record.regime)
    return quantize_decimal(recoverable)


def checksum_for_discrepancy(record: SaleRecord, matrix: FiscalMatrix, recoverable: Decimal) -> str:
    fingerprint = "|".join(
        [
            record.sku,
            record.ncm,
            matrix.ncm,
            str(record.tax_rate),
            str(matrix.effective_tax_rate),
            str(recoverable),
        ]
    )
    return sha256(fingerprint.encode("utf-8")).hexdigest()


async def compute_recovery(sales: Iterable[SaleRecord], tax_api: TaxAPIClient, window_days: int = 90) -> List[TaxDiscrepancy]:
    cutoff = datetime.utcnow() - timedelta(days=window_days)
    candidates = [sale for sale in sales if sale.sold_at >= cutoff]
    results: List[TaxDiscrepancy] = []

    for sale in candidates:
        payload = await tax_api.fetch_ncm_and_rate(sale.sku)
        matrix = build_matrix_from_payload(sale, payload)
        findings = validate_ncm_cest(sale, matrix)
        recoverable = calculate_recoverable_credit(sale, matrix)
        margin = compute_real_margin(sale)
        if margin < Decimal("4.0000"):
            findings.append("Margem real abaixo do piso executivo")

        if findings or recoverable > Decimal("0.0000") or matrix.effective_tax_rate != sale.tax_rate:
            reason = "; ".join(findings) or "Segregação monofásica detectada"
            results.append(
                TaxDiscrepancy(
                    sku=sale.sku,
                    local_ncm=sale.ncm,
                    national_ncm=matrix.ncm,
                    local_rate=quantize_decimal(sale.tax_rate),
                    national_rate=matrix.effective_tax_rate,
                    discrepancy_amount=recoverable,
                    severity="critico" if findings else "alerta",
                    reason=reason,
                    checksum=checksum_for_discrepancy(sale, matrix, recoverable),
                )
            )

    return results
