"""
GROK 4: Animation System & Motion Design
Framer Motion integration for smooth UI transitions
"""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
import reflex as rx


class AnimationType(str, Enum):
    """Animation type identifiers"""
    FADE_IN = "fadeIn"
    SLIDE_IN_UP = "slideInUp"
    SLIDE_IN_LEFT = "slideInLeft"
    BOUNCE = "bounce"
    SCALE = "scale"
    ROTATE = "rotate"
    PULSE = "pulse"


class AnimationConfig(BaseModel):
    """Animation configuration"""
    model_config = ConfigDict(frozen=True)
    
    animation_type: AnimationType = Field(default=AnimationType.FADE_IN)
    duration: float = Field(default=0.3, ge=0.1, le=5.0, description="Duration in seconds")
    delay: float = Field(default=0.0, ge=0.0, description="Delay before animation starts")
    easing: str = Field(default="ease-in-out", description="Easing function")
    repeat: int | float = Field(default=1, description="Number of repeats (1 for once, float('inf') for infinite)")


class CSS_ANIMATIONS:
    """CSS animation definitions for smooth transitions"""
    
    # GROK 4: Entrance animations
    FADE_IN = """
    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }
    """
    
    SLIDE_IN_UP = """
    @keyframes slideInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    """
    
    SLIDE_IN_LEFT = """
    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    """
    
    SCALE_IN = """
    @keyframes scaleIn {
        from {
            opacity: 0;
            transform: scale(0.95);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }
    """
    
    # Continuous animations
    PULSE = """
    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.5;
        }
    }
    """
    
    BOUNCE = """
    @keyframes bounce {
        0%, 100% {
            transform: translateY(0);
        }
        50% {
            transform: translateY(-10px);
        }
    }
    """
    
    # Chart entrance
    CHART_SLIDE_IN = """
    @keyframes chartSlideIn {
        from {
            opacity: 0;
            clip-path: polygon(0 0, 100% 0, 100% 0, 0 0);
        }
        to {
            opacity: 1;
            clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%);
        }
    }
    """


def animate(
    component: rx.Component,
    animation_type: AnimationType = AnimationType.FADE_IN,
    duration: float = 0.3,
    delay: float = 0.0,
    easing: str = "ease-in-out",
) -> rx.Component:
    """
    Apply animation to a component
    
    Usage:
        animated_card = animate(
            my_card,
            animation_type=AnimationType.SLIDE_IN_UP,
            duration=0.5,
        )
    """
    animation_map = {
        AnimationType.FADE_IN: "fadeIn",
        AnimationType.SLIDE_IN_UP: "slideInUp",
        AnimationType.SLIDE_IN_LEFT: "slideInLeft",
        AnimationType.BOUNCE: "bounce",
        AnimationType.SCALE: "scaleIn",
        AnimationType.PULSE: "pulse",
    }
    
    animation_name = animation_map.get(animation_type, "fadeIn")
    
    return rx.box(
        component,
        animation=f"{animation_name} {duration}s {easing} {delay}s forwards",
        opacity=0,  # Start hidden (animation will make it visible)
    )


class MotionCard(rx.Component):
    """
    GROK 4: Card component with entrance animation
    Automatically animates on mount
    """
    tag = "div"
    
    @staticmethod
    def render(
        children=None,
        animation_type: AnimationType = AnimationType.SLIDE_IN_UP,
        delay: float = 0.0,
    ):
        return rx.box(
            children,
            animation=f"{animation_type.value} 0.4s ease-out {delay}s forwards",
            opacity=0,
            border="1px solid var(--color-border)",
            border_radius="lg",
            padding="md",
            background_color="var(--color-surface)",
        )


class MotionButton(rx.Component):
    """
    GROK 4: Button with hover animations
    Includes scale and color transition on hover
    """
    tag = "button"
    
    @staticmethod
    def render(
        label: str,
        on_click=None,
        variant: str = "primary",
    ):
        hover_styles = {
            "primary": {
                "transform": "scale(1.05)",
                "background_color": "var(--color-primary-dark)",
            },
            "secondary": {
                "transform": "scale(1.05)",
                "background_color": "var(--color-secondary-dark)",
            },
        }
        
        return rx.button(
            label,
            on_click=on_click,
            background_color=(
                "var(--color-primary)" if variant == "primary" else "var(--color-secondary)"
            ),
            color="white",
            padding="10px 20px",
            border_radius="md",
            cursor="pointer",
            transition="all 0.2s ease",
            _hover=hover_styles.get(variant, {}),
            font_weight="bold",
        )


class SkeletonAnimation(rx.Component):
    """
    GROK 4: Animated skeleton loader
    Shows pulse animation while content loads
    """
    tag = "div"
    
    @staticmethod
    def render(count: int = 3):
        return rx.vstack(
            *[
                rx.box(
                    height="20px",
                    width="100%",
                    background_color="var(--color-border)",
                    border_radius="md",
                    animation="pulse 1.5s ease-in-out infinite",
                    margin_bottom="10px",
                )
                for _ in range(count)
            ],
            spacing="md",
            width="100%",
        )


def create_stagger_animation(
    items: list,
    animation_type: AnimationType = AnimationType.FADE_IN,
    stagger_delay: float = 0.1,
) -> list:
    """
    Create staggered animation for list items
    Each item animates with a delay
    
    Usage:
        items = [card1, card2, card3]
        animated_items = create_stagger_animation(items, stagger_delay=0.2)
    """
    animated = []
    for i, item in enumerate(items):
        delay = i * stagger_delay
        animated_item = rx.box(
            item,
            animation=f"{animation_type.value} 0.4s ease-out {delay}s forwards",
            opacity=0,
        )
        animated.append(animated_item)
    
    return animated


# Motion variants for common patterns
MOTION_VARIANTS = {
    "card_enter": AnimationConfig(
        animation_type=AnimationType.SLIDE_IN_UP,
        duration=0.4,
        easing="cubic-bezier(0.4, 0, 0.2, 1)",
    ),
    "modal_enter": AnimationConfig(
        animation_type=AnimationType.SCALE,
        duration=0.2,
        easing="ease-out",
    ),
    "sidebar_enter": AnimationConfig(
        animation_type=AnimationType.SLIDE_IN_LEFT,
        duration=0.3,
        easing="ease-out",
    ),
    "tooltip_enter": AnimationConfig(
        animation_type=AnimationType.FADE_IN,
        duration=0.15,
        easing="ease-out",
    ),
}


__all__ = [
    "AnimationType",
    "AnimationConfig",
    "CSS_ANIMATIONS",
    "animate",
    "MotionCard",
    "MotionButton",
    "SkeletonAnimation",
    "create_stagger_animation",
    "MOTION_VARIANTS",
]
