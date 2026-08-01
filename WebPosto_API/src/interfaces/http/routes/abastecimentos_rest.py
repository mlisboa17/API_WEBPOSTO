"""Compat: reexporta router de pista (cache RAM).

Implementação canônica: `src.api.v1.endpoints.pista`.
"""

from src.api.v1.endpoints.pista import router

__all__ = ["router"]
