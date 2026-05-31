"""
CLAUDE 3.7 + GROK 4: Frontend Components Package
Atomic Design: Atoms, Molecules, Organisms
Includes charts, theme system, and security HOCs
"""

# Atoms
from .atoms import (
    Card,
    Badge,
    SkeletonLoader,
    LoadingSpinner,
    CardProps,
)

# Molecules
from .molecules import (
    SyncProgressBar,
    CompanySelector,
    DashboardCard,
    AuditFeedItem,
    SyncProgressBarProps,
    CompanySelectorProps,
)

# Charts & Visualization (GROK 4)
from .charts import (
    RateioChart,
    TimeSeriesChart,
    MetricsGrid,
    RateioChartData,
)

__all__ = [
    # Atoms
    "Card",
    "Badge",
    "SkeletonLoader",
    "LoadingSpinner",
    "CardProps",
    # Molecules
    "SyncProgressBar",
    "CompanySelector",
    "DashboardCard",
    "AuditFeedItem",
    "SyncProgressBarProps",
    "CompanySelectorProps",
    # Charts
    "RateioChart",
    "TimeSeriesChart",
    "MetricsGrid",
    "RateioChartData",
]
