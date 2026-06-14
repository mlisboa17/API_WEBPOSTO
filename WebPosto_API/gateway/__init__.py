"""Onda 2 — Gateway WebPosto unificado."""
from gateway.webposto_client import ENDPOINTS, WebPostoClient, build_params, token_fingerprint
from gateway.webposto_errors import (
    WebPostoAuthError,
    WebPostoDataError,
    WebPostoGatewayError,
    WebPostoRateLimitError,
    WebPostoServerError,
    WebPostoSnapshotGuardError,
)
from gateway.webposto_types import PaginationState, WebPostoLogEvent, WebPostoResponse

__all__ = [
    "ENDPOINTS",
    "PaginationState",
    "WebPostoAuthError",
    "WebPostoClient",
    "WebPostoDataError",
    "WebPostoGatewayError",
    "WebPostoLogEvent",
    "WebPostoRateLimitError",
    "WebPostoResponse",
    "WebPostoServerError",
    "WebPostoSnapshotGuardError",
    "build_params",
    "token_fingerprint",
]
