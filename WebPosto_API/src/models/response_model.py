from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from src.models.error_model import WebPostoError


@dataclass
class WebPostoResponse:
    success: bool
    data: Optional[Any] = None
    error: Optional[WebPostoError] = None
    from_cache: bool = False
    stale: bool = False

    @classmethod
    def ok(
        cls,
        data: Any,
        *,
        from_cache: bool = False,
        stale: bool = False,
    ) -> "WebPostoResponse":
        return cls(
            success=True,
            data=data,
            error=None,
            from_cache=from_cache,
            stale=stale,
        )

    @classmethod
    def fail(cls, error: WebPostoError) -> "WebPostoResponse":
        return cls(success=False, data=None, error=error, from_cache=False, stale=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error.to_dict() if self.error else None,
            "from_cache": self.from_cache,
            "stale": self.stale,
        }
