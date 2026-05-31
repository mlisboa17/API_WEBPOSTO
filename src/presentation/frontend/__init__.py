"""
Reflex Frontend Application - DDD Presentation Layer

CLAUDE 3.7: State management, components, routing with permissions
GROK 4: UI components, themes, animations
GEMINI 2.0: Performance optimization, caching

Note: Import from submodules to avoid loading Reflex unless needed
"""

# Domain models (no Reflex dependency)
from .state import GlobalState

__all__ = ["GlobalState"]
