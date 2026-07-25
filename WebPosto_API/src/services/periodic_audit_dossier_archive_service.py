"""Arquivo imutável e verificação criptográfica do dossiê aprovado."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.services.json_file_lock import InterProcessFileLock
from src.services.periodic_audit_dossier_service import PeriodicAuditDossierService
from src.services.periodic_audit_run_service import PeriodicAuditRun


class PeriodicAuditDossierArchiveService:
    def __init__(
        self,
        root: str | Path = ".runtime/periodic_audits/dossiers",
        generator: PeriodicAuditDossierService | None = None,
    ) -> None:
        self._root = Path(root)
        self._generator = generator or PeriodicAuditDossierService()

    def get_or_create(self, run: PeriodicAuditRun) -> tuple[bytes, dict]:
        self._validate_run_id(run.id)
        directory = self._root / run.id
        pdf_path = directory / "dossier.pdf"
        manifest_path = directory / "manifest.json"
        with InterProcessFileLock(manifest_path):
            if manifest_path.exists() or pdf_path.exists():
                return self._verified_files(run.id)
            content = self._generator.generate(run)
            digest = hashlib.sha256(content).hexdigest()
            manifest = {
                "schemaVersion": 1,
                "runId": run.id,
                "sha256": digest,
                "sizeBytes": len(content),
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "approvedAt": run.aprovado_em.isoformat() if run.aprovado_em else None,
                "immutable": True,
            }
            self._atomic_write(pdf_path, content)
            self._atomic_write(
                manifest_path,
                json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            return content, manifest

    def verify(self, run_id: str) -> dict:
        try:
            self._validate_run_id(run_id)
        except ValueError as exc:
            return {"runId": run_id, "integrity": "FAILED", "reason": str(exc)}
        try:
            _, manifest = self._verified_files(run_id)
            return {**manifest, "integrity": "VERIFIED"}
        except FileNotFoundError:
            return {"runId": run_id, "integrity": "NOT_ARCHIVED"}
        except ValueError as exc:
            return {"runId": run_id, "integrity": "FAILED", "reason": str(exc)}

    def _verified_files(self, run_id: str) -> tuple[bytes, dict]:
        directory = self._root / run_id
        pdf_path = directory / "dossier.pdf"
        manifest_path = directory / "manifest.json"
        if not pdf_path.exists() and not manifest_path.exists():
            raise FileNotFoundError(run_id)
        if not pdf_path.exists() or not manifest_path.exists():
            raise ValueError("DOSSIER_ARCHIVE_INCOMPLETE")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            content = pdf_path.read_bytes()
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("DOSSIER_ARCHIVE_UNREADABLE") from exc
        digest = hashlib.sha256(content).hexdigest()
        if (
            manifest.get("runId") != run_id
            or manifest.get("sha256") != digest
            or manifest.get("sizeBytes") != len(content)
            or manifest.get("immutable") is not True
        ):
            raise ValueError("DOSSIER_INTEGRITY_MISMATCH")
        return content, manifest

    @staticmethod
    def _validate_run_id(run_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9-]{1,80}", run_id):
            raise ValueError("INVALID_RUN_ID")

    @staticmethod
    def _atomic_write(target: Path, content: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("wb", dir=target.parent, delete=False) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temp = Path(handle.name)
            os.replace(temp, target)
        finally:
            if temp and temp.exists():
                temp.unlink(missing_ok=True)
