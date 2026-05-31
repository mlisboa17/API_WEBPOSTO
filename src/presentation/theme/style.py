"""Theme tokens for Lionda design system."""
from typing import Dict


PALETTE: Dict[str, str] = {
    "background": "#0A0A0B",
    "cyber_blue": "#00F5FF",
    "muted": "#A0A0A0",
    "card_bg": "rgba(255,255,255,0.03)",
}


def get_token(name: str) -> str:
    return PALETTE.get(name, "#000000")
