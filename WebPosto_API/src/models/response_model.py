from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from src.models.error_model import WebPostoError


@dataclass
class WebPostoResponse:
    success: bool
    data: Optional[Any] = None
    error: Optional[WebPostoError] = None

    @classmethod
    def ok(cls, data: Any) -> "WebPostoResponse":
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(cls, error: WebPostoError) -> "WebPostoResponse":
        return cls(success=False, data=None, error=error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error.to_dict() if self.error else None,
        }
