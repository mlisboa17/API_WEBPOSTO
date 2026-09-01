"""Extração conservadora e conciliação do PDF de Prestação de Contas."""

from __future__ import annotations

import re
from decimal import Decimal
from io import BytesIO
from typing import Any

from pypdf import PdfReader


MONEY = r"-?\d{1,3}(?:\.\d{3})*,\d{2}"
TOTAL_RE = re.compile(
    rf"Total\s+({MONEY})\s+({MONEY})\s+({MONEY})\s+({MONEY})",
    re.IGNORECASE,
)
PERIOD_RE = re.compile(
    r"Data Inicial:\s*(\d{2}/\d{2}/\d{4}).*?Data Final:\s*(\d{2}/\d{2}/\d{4})",
    re.IGNORECASE | re.DOTALL,
)


def _decimal(value: str | int | float | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    normalized = str(value).replace("R$", "").strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except Exception:  # noqa: BLE001
        return None


class PeriodicAuditPdfReconciliationService:
    def extract(self, content: bytes) -> dict[str, Any]:
        reader = PdfReader(BytesIO(content), strict=True)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return self.extract_text(text, len(reader.pages))

    @staticmethod
    def extract_text(text: str, pages: int) -> dict[str, Any]:
        period = PERIOD_RE.search(text)
        total = TOTAL_RE.search(text)
        if not total:
            raise ValueError("PDF_TOTALS_NOT_FOUND")
        start = period.group(1) if period else None
        end = period.group(2) if period else None
        values = [_decimal(item) for item in total.groups()]
        return {
            "period": {"start": start, "end": end},
            "pages": pages,
            "paymentSummary": {
                "presented": str(values[0]),
                "withdrawals": str(values[1]),
                "calculated": str(values[2]),
                "difference": str(values[3]),
            },
            "extractionStatus": "TOTALS_EXTRACTED",
        }

    def reconcile(self, pdf: dict[str, Any], api: dict[str, Any]) -> dict[str, Any]:
        pdf_withdrawals = _decimal((pdf.get("paymentSummary") or {}).get("withdrawals"))
        api_withdrawals = _decimal(
            (((api.get("sangriaIntelligence") or {}).get("fluxo") or {}).get("SANGRIA") or {}).get("valor")
        )
        comparisons = [
            self._comparison("withdrawals", pdf_withdrawals, api_withdrawals),
            self._comparison(
                "presented",
                _decimal((pdf.get("paymentSummary") or {}).get("presented")),
                None,
            ),
            self._comparison(
                "calculated",
                _decimal((pdf.get("paymentSummary") or {}).get("calculated")),
                None,
            ),
            self._comparison(
                "difference",
                _decimal((pdf.get("paymentSummary") or {}).get("difference")),
                None,
            ),
        ]
        comparable = [item for item in comparisons if item["status"] != "API_VALUE_UNAVAILABLE"]
        return {
            "status": (
                "MATCH"
                if comparable and all(item["status"] == "MATCH" for item in comparable)
                else "DIVERGENT"
                if comparable
                else "INSUFFICIENT_API_COVERAGE"
            ),
            "comparisons": comparisons,
            "automaticApprovalAllowed": False,
            "reviewRequired": True,
        }

    @staticmethod
    def _comparison(name: str, pdf_value: Decimal | None, api_value: Decimal | None) -> dict:
        if api_value is None:
            return {
                "metric": name,
                "pdf": str(pdf_value) if pdf_value is not None else None,
                "api": None,
                "difference": None,
                "status": "API_VALUE_UNAVAILABLE",
            }
        difference = (pdf_value or Decimal("0")) - api_value
        return {
            "metric": name,
            "pdf": str(pdf_value) if pdf_value is not None else None,
            "api": str(api_value),
            "difference": str(difference),
            "status": "MATCH" if abs(difference) <= Decimal("0.05") else "DIVERGENT",
        }
