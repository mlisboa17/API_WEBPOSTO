from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class WebPostoError:
    system: str = "webposto"
    endpoint: str = ""
    status: int = 500
    type: str = "UNKNOWN_ERROR"
    message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
