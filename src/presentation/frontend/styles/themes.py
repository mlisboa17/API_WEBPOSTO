"""
GROK 4: Theme System & Dynamic Styling
Supports Dark/Light modes with runtime switching
"""

from typing import Literal, ClassVar
from pydantic import BaseModel, ConfigDict
from .colors import LOGOS_DARK, LOGOS_LIGHT, SEMANTIC_COLORS


class ThemeConfig(BaseModel):
    """
    Runtime theme configuration with Pydantic V2
    Supports hot-reload on theme changes
    """
    
    model_config = ConfigDict(
        frozen=False,
        extra="allow",  # Allow extra fields for flexibility
        validate_default=True,
    )
    
    mode: Literal["dark", "light"] = "dark"
    primary_color: str = LOGOS_DARK["primary"]
    secondary_color: str = LOGOS_DARK["secondary"]
    success_color: str = LOGOS_DARK["success"]
    warning_color: str = LOGOS_DARK["warning"]
    danger_color: str = LOGOS_DARK["danger"]
    background_color: str = LOGOS_DARK["background"]
    surface_color: str = LOGOS_DARK["surface"]
    text_color: str = LOGOS_DARK["text"]
    text_secondary_color: str = LOGOS_DARK["text_secondary"]
    border_color: str = LOGOS_DARK["border"]
    
    # Custom semantic colors
    sync_active_color: str = SEMANTIC_COLORS["sync_active"]
    sync_pending_color: str = SEMANTIC_COLORS["sync_pending"]
    sync_error_color: str = SEMANTIC_COLORS["sync_error"]
    
    @classmethod
    def dark_mode(cls) -> "ThemeConfig":
        """Factory: Dark theme (default)"""
        return cls(mode="dark", **LOGOS_DARK)
    
    @classmethod
    def light_mode(cls) -> "ThemeConfig":
        """Factory: Light theme"""
        return cls(mode="light", **LOGOS_LIGHT)
    
    def to_css_variables(self) -> dict[str, str]:
        """Convert theme to CSS custom properties"""
        return {
            "--color-primary": self.primary_color,
            "--color-secondary": self.secondary_color,
            "--color-success": self.success_color,
            "--color-warning": self.warning_color,
            "--color-danger": self.danger_color,
            "--color-bg": self.background_color,
            "--color-surface": self.surface_color,
            "--color-text": self.text_color,
            "--color-text-secondary": self.text_secondary_color,
            "--color-border": self.border_color,
        }


class Typography(BaseModel):
    """
    Typography system for consistent sizing
    Mobile-first approach
    """
    
    model_config = ConfigDict(frozen=True)
    
    # Font sizes (rem-based)
    h1: float = 2.5      # 40px
    h2: float = 2.0      # 32px
    h3: float = 1.5      # 24px
    h4: float = 1.25     # 20px
    h5: float = 1.125    # 18px
    h6: float = 1.0      # 16px
    
    body_large: float = 1.125    # 18px
    body: float = 1.0            # 16px
    body_small: float = 0.875    # 14px
    
    caption: float = 0.75        # 12px
    overline: float = 0.625      # 10px


class Shadows(BaseModel):
    """
    Shadow system for depth
    Supports 3D effect for modals/cards
    """
    
    model_config = ConfigDict(frozen=True)
    
    sm: str = "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
    md: str = "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
    lg: str = "0 10px 15px -3px rgba(0, 0, 0, 0.1)"
    xl: str = "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
    
    # For modals/overlays
    modal: str = "0 25px 50px -12px rgba(0, 0, 0, 0.25)"


class ThemeSystem(BaseModel):
    """
    Complete theme system combining all design tokens
    Single source of truth for UI styling
    """
    
    model_config = ConfigDict(frozen=False)
    
    config: ThemeConfig = ThemeConfig.dark_mode()
    typography: ClassVar[Typography] = Typography()
    shadows: ClassVar[Shadows] = Shadows()
    
    def switch_theme(self, mode: Literal["dark", "light"]) -> None:
        """Dynamically switch theme at runtime"""
        if mode == "dark":
            self.config = ThemeConfig.dark_mode()
        elif mode == "light":
            self.config = ThemeConfig.light_mode()
        else:
            raise ValueError(f"Invalid theme mode: {mode}")


# Global theme instance (singleton-like)
GLOBAL_THEME = ThemeSystem()
