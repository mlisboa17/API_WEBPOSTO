from io import BytesIO

import pytest
from pypdf import PdfWriter

from src.services.periodic_audit_pdf_store import PeriodicAuditPdfStore


def pdf_bytes() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    writer.write(output)
    return output.getvalue()


def test_valid_pdf_is_private_and_idempotent(tmp_path):
    store = PeriodicAuditPdfStore(tmp_path / "evidence")
    first = store.save("run-1", pdf_bytes(), "../../prestacao julho.pdf", "auditor")
    second = store.save("run-1", pdf_bytes(), "duplicate.pdf", "auditor")

    assert first == second
    assert first["filename"] == "prestacao_julho.pdf"
    assert first["pages"] == 1
    assert first["storage"] == "PRIVATE_RUNTIME"
    assert len(store.list("run-1")) == 1


def test_invalid_or_encrypted_pdf_is_rejected(tmp_path):
    store = PeriodicAuditPdfStore(tmp_path / "evidence")
    with pytest.raises(ValueError, match="INVALID_PDF_SIGNATURE"):
        store.save("run-1", b"not-a-pdf", "fake.pdf", "auditor")

    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    writer.encrypt("secret")
    writer.write(output)
    with pytest.raises(ValueError, match="ENCRYPTED_PDF_NOT_ALLOWED"):
        store.save("run-1", output.getvalue(), "locked.pdf", "auditor")
