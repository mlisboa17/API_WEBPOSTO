from src.services.periodic_audit_dossier_archive_service import PeriodicAuditDossierArchiveService
from src.services.periodic_audit_dossier_backup_service import PeriodicAuditDossierBackupService
from tests.unit.test_periodic_audit_dossier_service import approved_run


def services(tmp_path):
    archive_root = tmp_path / "dossiers"
    backup_root = tmp_path / "backups"
    archive = PeriodicAuditDossierArchiveService(archive_root)
    backup = PeriodicAuditDossierBackupService(archive_root, backup_root)
    archive.get_or_create(approved_run())
    return archive, backup, archive_root, backup_root


def test_backup_is_verified_and_idempotent(tmp_path):
    _, backup, _, _ = services(tmp_path)
    first = backup.backup("run-123", "auditor")
    second = backup.backup("run-123", "auditor")

    assert first["operation"] == "BACKUP_CREATED"
    assert second["operation"] == "BACKUP_REUSED"
    assert first["sha256"] == second["sha256"]
    assert backup.verify_backup("run-123")["integrity"] == "VERIFIED"


def test_restore_preserves_original_hash(tmp_path):
    archive, backup, archive_root, _ = services(tmp_path)
    expected = backup.backup("run-123", "auditor")["sha256"]
    for path in (archive_root / "run-123").iterdir():
        path.unlink()
    (archive_root / "run-123").rmdir()

    restored = backup.restore("run-123", "admin")

    assert restored["operation"] == "RESTORE_COMPLETED"
    assert restored["sha256"] == expected
    assert archive.verify("run-123")["sha256"] == expected


def test_tampered_backup_cannot_be_restored(tmp_path):
    _, backup, archive_root, backup_root = services(tmp_path)
    backup.backup("run-123", "auditor")
    (backup_root / "run-123" / "dossier.pdf").write_bytes(b"tampered")
    for path in (archive_root / "run-123").iterdir():
        path.unlink()
    (archive_root / "run-123").rmdir()

    try:
        backup.restore("run-123", "admin")
    except ValueError as exc:
        assert str(exc) == "DOSSIER_BACKUP_INTEGRITY_MISMATCH"
    else:
        raise AssertionError("restauração adulterada deveria falhar")


def test_restore_does_not_overwrite_corrupted_primary(tmp_path):
    _, backup, archive_root, _ = services(tmp_path)
    backup.backup("run-123", "auditor")
    (archive_root / "run-123" / "dossier.pdf").write_bytes(b"corrupted")

    try:
        backup.restore("run-123", "admin")
    except ValueError as exc:
        assert str(exc) == "DOSSIER_PRIMARY_CORRUPTED"
    else:
        raise AssertionError("arquivo primário corrompido não pode ser sobrescrito")


def test_backup_rejects_path_traversal(tmp_path):
    service = PeriodicAuditDossierBackupService(tmp_path / "dossiers", tmp_path / "backups")
    assert service.verify_backup("../outside") == {
        "runId": "../outside",
        "integrity": "FAILED",
        "reason": "INVALID_RUN_ID",
    }
