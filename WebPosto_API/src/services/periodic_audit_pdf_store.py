"""Armazenamento privado e validação estrutural de PDFs de auditoria."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader

from src.services.json_file_lock import InterProcessFileLock


MAX_PDF_BYTES = 20 * 1024 * 1024
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class PeriodicAuditPdfStore:
    def __init__(self, root: str | Path = ".runtime/periodic_audits/evidence") -> None:
        self._root = Path(root)

    def save(self, run_id: str, content: bytes, filename: str, actor: str) -> dict:
        if not content or len(content) > MAX_PDF_BYTES:
            raise ValueError("INVALID_PDF_SIZE")
        if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-2048:]:
            raise ValueError("INVALID_PDF_SIGNATURE")
        try:
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise ValueError("ENCRYPTED_PDF_NOT_ALLOWED")
            pages = len(reader.pages)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("INVALID_PDF_STRUCTURE") from exc
        if pages < 1 or pages > 500:
            raise ValueError("INVALID_PDF_PAGE_COUNT")

        digest = hashlib.sha256(content).hexdigest()
        safe_name = SAFE_NAME.sub("_", Path(filename or "prestacao-contas.pdf").name)
        if not safe_name.lower().endswith(".pdf"):
            safe_name += ".pdf"
        directory = self._root / run_id
        metadata_path = directory / "metadata.json"
        with InterProcessFileLock(metadata_path):
            directory.mkdir(parents=True, exist_ok=True)
            records = self.list(run_id)
            existing = next((item for item in records if item["sha256"] == digest), None)
            if existing:
                return existing
            evidence_id = str(uuid4())
            target = directory / f"{evidence_id}.pdf"
            self._atomic_write(target, content)
            record = {
                "id": evidence_id,
                "runId": run_id,
                "filename": safe_name,
                "sha256": digest,
                "sizeBytes": len(content),
                "pages": pages,
                "uploadedAt": datetime.now(timezone.utc).isoformat(),
                "uploadedBy": actor,
                "storage": "PRIVATE_RUNTIME",
            }
            records.append(record)
            self._atomic_write(
                metadata_path,
                json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            return record

    def list(self, run_id: str) -> list[dict]:
        path = self._root / run_id / "metadata.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def read(self, run_id: str, evidence_id: str) -> bytes | None:
        if not re.fullmatch(r"[0-9a-f-]{36}", evidence_id):
            return None
        path = self._root / run_id / f"{evidence_id}.pdf"
        try:
            return path.read_bytes()
        except OSError:
            return None

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
