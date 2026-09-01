"""Backup verificável e restauração segura dos dossiês de auditoria."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.services.json_file_lock import InterProcessFileLock


class PeriodicAuditDossierBackupService:
    def __init__(
        self,
        archive_root: str | Path = ".runtime/periodic_audits/dossiers",
        backup_root: str | Path = ".runtime/periodic_audits/dossier_backups",
        retention_days: int = 2555,
    ) -> None:
        if retention_days < 365:
            raise ValueError("DOSSIER_RETENTION_TOO_SHORT")
        self._archive_root = Path(archive_root)
        self._backup_root = Path(backup_root)
        self._retention_days = retention_days

    def backup(self, run_id: str, actor: str) -> dict:
        self._validate_run_id(run_id)
        source = self._archive_root / run_id
        destination = self._backup_root / run_id
        with InterProcessFileLock(destination / "backup-record.json"):
            content, manifest = self._read_verified(source, run_id)
            existing = self._try_read_verified(destination, run_id)
            if existing and existing[1]["sha256"] == manifest["sha256"]:
                result = self._record(run_id, actor, "BACKUP_REUSED", manifest)
                return {**result, "retentionDays": self._retention_days}
            self._atomic_write(destination / "dossier.pdf", content)
            self._atomic_write(
                destination / "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            result = self._record(run_id, actor, "BACKUP_CREATED", manifest)
            self._atomic_write(
                destination / "backup-record.json",
                json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            return {**result, "retentionDays": self._retention_days}

    def restore(self, run_id: str, actor: str) -> dict:
        self._validate_run_id(run_id)
        source = self._backup_root / run_id
        destination = self._archive_root / run_id
        with InterProcessFileLock(destination / "manifest.json"):
            content, manifest = self._read_verified(source, run_id)
            current = self._try_read_verified(destination, run_id)
            if current:
                if current[1]["sha256"] != manifest["sha256"]:
                    raise ValueError("DOSSIER_RESTORE_CONFLICT")
                return self._record(run_id, actor, "RESTORE_NOT_NEEDED", manifest)
            if (destination / "dossier.pdf").exists() or (destination / "manifest.json").exists():
                raise ValueError("DOSSIER_PRIMARY_CORRUPTED")
            self._atomic_write(destination / "dossier.pdf", content)
            self._atomic_write(
                destination / "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            self._read_verified(destination, run_id)
            return self._record(run_id, actor, "RESTORE_COMPLETED", manifest)

    def verify_backup(self, run_id: str) -> dict:
        try:
            self._validate_run_id(run_id)
            _, manifest = self._read_verified(self._backup_root / run_id, run_id)
            return {
                "runId": run_id,
                "integrity": "VERIFIED",
                "sha256": manifest["sha256"],
                "retentionDays": self._retention_days,
            }
        except FileNotFoundError:
            return {"runId": run_id, "integrity": "NOT_BACKED_UP"}
        except ValueError as exc:
            return {"runId": run_id, "integrity": "FAILED", "reason": str(exc)}

    @staticmethod
    def _validate_run_id(run_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9-]{1,80}", run_id):
            raise ValueError("INVALID_RUN_ID")

    def _record(self, run_id: str, actor: str, operation: str, manifest: dict) -> dict:
        event = {
            "runId": run_id,
            "operation": operation,
            "actor": actor,
            "occurredAt": datetime.now(timezone.utc).isoformat(),
            "sha256": manifest["sha256"],
        }
        log = self._backup_root / "_operations.jsonl"
        with InterProcessFileLock(log):
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        return event

    @staticmethod
    def _try_read_verified(directory: Path, run_id: str) -> tuple[bytes, dict] | None:
        try:
            return PeriodicAuditDossierBackupService._read_verified(directory, run_id)
        except FileNotFoundError:
            return None
        except ValueError:
            return None

    @staticmethod
    def _read_verified(directory: Path, run_id: str) -> tuple[bytes, dict]:
        pdf = directory / "dossier.pdf"
        manifest_path = directory / "manifest.json"
        if not pdf.exists() and not manifest_path.exists():
            raise FileNotFoundError(run_id)
        if not pdf.exists() or not manifest_path.exists():
            raise ValueError("DOSSIER_BACKUP_INCOMPLETE")
        try:
            content = pdf.read_bytes()
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("DOSSIER_BACKUP_UNREADABLE") from exc
        digest = hashlib.sha256(content).hexdigest()
        if (
            manifest.get("runId") != run_id
            or manifest.get("sha256") != digest
            or manifest.get("sizeBytes") != len(content)
            or manifest.get("immutable") is not True
        ):
            raise ValueError("DOSSIER_BACKUP_INTEGRITY_MISMATCH")
        return content, manifest

    @staticmethod
    def _atomic_write(target: Path, content: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("wb", dir=target.parent, delete=False) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temporary = Path(handle.name)
            os.replace(temporary, target)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
