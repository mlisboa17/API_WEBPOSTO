"""Shared style tokens for the Lionda executive UI."""

BACKGROUND = "#070708"
SURFACE = "rgba(255,255,255,0.03)"
SURFACE_SOFT = "rgba(255,255,255,0.015)"
TEXT_MUTED = "#A0A0A0"
CYAN = "#00F5FF"
CYAN_SOFT = "rgba(0,245,255,0.18)"
GREEN = "#00FF7F"
RED = "#FF4D4D"
AMBER = "#FFB020"
GRADIENT_BORDER = "linear-gradient(135deg, rgba(0,245,255,0.85), rgba(255,255,255,0.08))"


def glass_panel_style() -> dict:
    return {
        "bg": SURFACE,
        "border": "1px solid rgba(255,255,255,0.08)",
        "border_radius": "24px",
        "backdrop_filter": "blur(20px)",
        "box_shadow": "0 10px 50px rgba(0,0,0,0.28)",
    }


def neon_border_style(color: str = CYAN) -> dict:
    return {
        "border": f"1px solid {color}",
        "box_shadow": f"0 0 0 1px {color} inset, 0 0 24px rgba(0,245,255,0.12)",
    }
"""Theme styles and helpers for Logos 'Lionda' aesthetic."""
from typing import Dict


def global_css() -> str:
    return """
/* Logos-themed gradients and custom scrollbars */
:root{
  --logos-deep-indigo: #0b1020;
  --logos-cyber-green: #00ff9f;
  --card-glow: rgba(99,102,241,0.12);
}
body{
  background: linear-gradient(135deg,var(--logos-deep-indigo),#021b20);
  color: #e6eef6;
  -webkit-font-smoothing:antialiased;
}

/* Custom Scrollbar */
*::-webkit-scrollbar{height:12px;width:12px}
*::-webkit-scrollbar-thumb{background:linear-gradient(180deg,var(--logos-cyber-green),#5eead4);border-radius:8px}
/* Card subtle neon */
.logos-card{background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));border:1px solid rgba(99,102,241,0.06);box-shadow:0 6px 18px rgba(2,6,23,0.6);border-radius:12px}

/* Small utility */
.glass-blur{backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}

"""


def theme_vars() -> Dict[str, str]:
    return {
        "primary": "#6366F1",
        "accent": "#00FF9F",
    }
