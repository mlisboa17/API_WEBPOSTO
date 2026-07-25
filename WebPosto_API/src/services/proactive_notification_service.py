"""Notificações executivas proativas com outbox idempotente e webhook opcional."""

from __future__ import annotations

import json
import os
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.services.json_file_lock import InterProcessFileLock


class ProactiveNotificationService:
    def __init__(
        self,
        path: str | Path = ".runtime/proactive_notifications.json",
        webhook_url: str | None = None,
        sender: Callable[[str, dict], None] | None = None,
    ) -> None:
        self._path = Path(path)
        self._webhook_url = webhook_url if webhook_url is not None else os.getenv("EXECUTIVE_NOTIFICATION_WEBHOOK_URL")
        self._sender = sender or self._send_webhook

    def dispatch(self, radar: dict[str, Any]) -> dict[str, Any]:
        created = []
        with InterProcessFileLock(self._path):
            state = self._load()
            records = state.setdefault("notifications", {})
            for insight in radar.get("priorities") or []:
                audiences = ["DIRECTOR"]
                if insight.get("severity") == "CRITICAL" or insight.get("type") == "OPPORTUNITY":
                    audiences.insert(0, "PRESIDENT")
                for audience in audiences:
                    notification_id = f"{radar['day']}:{insight['id']}:{audience}"
                    if notification_id in records:
                        continue
                    record = {
                        "id": notification_id,
                        "day": radar["day"],
                        "audience": audience,
                        "type": insight["type"],
                        "title": insight["title"],
                        "evidence": insight["evidence"],
                        "confidence": insight["confidence"],
                        "estimatedImpactBRL": insight["estimatedImpactBRL"],
                        "impactLabel": insight["impactLabel"],
                        "responsible": insight["suggestedOwner"],
                        "recommendedAction": insight["recommendedAction"],
                        "dueInDays": insight["dueInDays"],
                        "lineage": insight["lineage"],
                        "createdAt": datetime.now(timezone.utc).isoformat(),
                        "delivery": {
                            "inApp": "AVAILABLE",
                            "webhook": "PENDING" if self._webhook_url else "NOT_CONFIGURED",
                        },
                    }
                    records[notification_id] = record
                    created.append(record)
            self._save(state)
        delivered = 0
        if self._webhook_url:
            for record in created:
                try:
                    self._sender(self._webhook_url, record)
                    self._set_webhook_status(record["id"], "DELIVERED")
                    delivered += 1
                except Exception:  # noqa: BLE001
                    self._set_webhook_status(record["id"], "FAILED")
        return {
            "created": len(created),
            "webhookDelivered": delivered,
            "webhookConfigured": bool(self._webhook_url),
        }

    def list(self, audience: str | None = None) -> list[dict[str, Any]]:
        values = list((self._load().get("notifications") or {}).values())
        if audience:
            values = [item for item in values if item.get("audience") == audience]
        return sorted(values, key=lambda item: item["createdAt"], reverse=True)

    def homologate_webhook(self, url: str | None = None) -> dict[str, Any]:
        target = (url or self._webhook_url or "").strip()
        if not target:
            return {
                "status": "NOT_CONFIGURED",
                "webhookConfigured": False,
                "message": "Defina EXECUTIVE_NOTIFICATION_WEBHOOK_URL ou informe url no corpo.",
                "containsBusinessData": False,
            }
        payload = {
            "type": "WEBHOOK_HOMOLOGATION",
            "source": "logos-webposto",
            "at": datetime.now(timezone.utc).isoformat(),
            "containsBusinessData": False,
        }
        try:
            self._sender(target, payload)
            return {
                "status": "DELIVERED",
                "webhookConfigured": True,
                "endpoint": target.split("?")[0],
                "containsBusinessData": False,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "FAILED",
                "webhookConfigured": True,
                "endpoint": target.split("?")[0],
                "error": exc.__class__.__name__,
                "containsBusinessData": False,
            }

    def _set_webhook_status(self, notification_id: str, status: str) -> None:
        with InterProcessFileLock(self._path):
            state = self._load()
            record = (state.get("notifications") or {}).get(notification_id)
            if record:
                record["delivery"]["webhook"] = status
                record["delivery"]["attemptedAt"] = datetime.now(timezone.utc).isoformat()
                self._save(state)

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self._path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {"notifications": {}}
        except (OSError, json.JSONDecodeError):
            return {"schemaVersion": 1, "notifications": {}}

    def _save(self, value: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self._path.parent, delete=False) as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
                temporary = Path(handle.name)
            os.replace(temporary, self._path)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

    @staticmethod
    def _send_webhook(url: str, payload: dict) -> None:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            if response.status >= 300:
                raise RuntimeError(f"WEBHOOK_HTTP_{response.status}")
