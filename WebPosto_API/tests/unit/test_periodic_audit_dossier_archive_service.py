from concurrent.futures import ThreadPoolExecutor

from src.services.periodic_audit_dossier_archive_service import (
    PeriodicAuditDossierArchiveService,
)
from tests.unit.test_periodic_audit_dossier_service import approved_run


def test_archive_is_immutable_idempotent_and_verified(tmp_path):
    service = PeriodicAuditDossierArchiveService(tmp_path / "dossiers")
    first_content, first_manifest = service.get_or_create(approved_run())
    second_content, second_manifest = service.get_or_create(approved_run())

    assert first_content == second_content
    assert first_manifest == second_manifest
    assert service.verify("run-123")["integrity"] == "VERIFIED"


def test_concurrent_archive_creates_only_one_manifest(tmp_path):
    service = PeriodicAuditDossierArchiveService(tmp_path / "dossiers")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: service.get_or_create(approved_run()), range(4)))
    assert len({item[1]["sha256"] for item in results}) == 1


def test_tampered_dossier_is_detected(tmp_path):
    service = PeriodicAuditDossierArchiveService(tmp_path / "dossiers")
    service.get_or_create(approved_run())
    dossier = tmp_path / "dossiers" / "run-123" / "dossier.pdf"
    dossier.write_bytes(dossier.read_bytes() + b"tampered")

    result = service.verify("run-123")
    assert result["integrity"] == "FAILED"
    assert result["reason"] == "DOSSIER_INTEGRITY_MISMATCH"
