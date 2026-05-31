"""
GROK 4: Color System & Design Tokens
Dynamic color system supporting Dark/Light modes
"""

from typing import TypedDict


class LogosDarkTheme(TypedDict):
    """Logos Dark Mode - Default theme"""
    primary: str
    secondary: str
    success: str
    warning: str
    danger: str
    background: str
    surface: str
    text: str
    text_secondary: str
    border: str
    

class LogosLightTheme(TypedDict):
    """Logos Light Mode - Alternative theme"""
    primary: str
    secondary: str
    success: str
    warning: str
    danger: str
    background: str
    surface: str
    text: str
    text_secondary: str
    border: str


# Logos Dark (Primary)
LOGOS_DARK: LogosDarkTheme = {
    "primary": "#6366F1",        # Indigo
    "secondary": "#8B5CF6",      # Violet
    "success": "#10B981",        # Emerald
    "warning": "#F59E0B",        # Amber
    "danger": "#EF4444",         # Red
    "background": "#0F172A",     # Near-black slate
    "surface": "#1E293B",        # Dark slate
    "text": "#F1F5F9",           # Nearly white
    "text_secondary": "#94A3B8", # Slate-400
    "border": "#334155",         # Slate-600
}

# Logos Light
LOGOS_LIGHT: LogosLightTheme = {
    "primary": "#4F46E5",        # Indigo-600
    "secondary": "#7C3AED",      # Violet-600
    "success": "#059669",        # Emerald-600
    "warning": "#D97706",        # Amber-600
    "danger": "#DC2626",         # Red-600
    "background": "#F9FAFB",     # Gray-50
    "surface": "#FFFFFF",        # White
    "text": "#111827",           # Gray-900
    "text_secondary": "#6B7280", # Gray-500
    "border": "#E5E7EB",         # Gray-200
}

# Semantic colors for UI states
SEMANTIC_COLORS = {
    "sync_active": "#10B981",     # Green
    "sync_pending": "#F59E0B",    # Amber
    "sync_error": "#EF4444",      # Red
    "rateio_positive": "#10B981", # Green
    "rateio_negative": "#EF4444", # Red
}

# Tailwind-like spacing for responsive design
SPACING = {
    "xs": "0.5rem",   # 8px
    "sm": "1rem",     # 16px
    "md": "1.5rem",   # 24px
    "lg": "2rem",     # 32px
    "xl": "3rem",     # 48px
    "2xl": "4rem",    # 64px
}

# Breakpoints for responsive design
BREAKPOINTS = {
    "mobile": "320px",
    "tablet": "640px",
    "desktop": "1024px",
    "wide": "1280px",
}
