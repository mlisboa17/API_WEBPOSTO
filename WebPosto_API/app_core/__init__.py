"""LOGOS SPACE — app_core (Onda 1+)."""

from app_core.filial_registry import (
    Filial,
    get_filial,
    get_filiais_ativas,
    is_filial_ativa,
    list_filiais,
)

__all__ = [
    "Filial",
    "get_filial",
    "get_filiais_ativas",
    "is_filial_ativa",
    "list_filiais",
]
