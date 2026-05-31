"""
CLAUDE 3.7: Atomic Design Components - Base Level (Atoms)
Small, reusable, single-purpose UI components
"""

from typing import Optional, Callable
from pydantic import BaseModel, ConfigDict, Field
import reflex as rx


class CardProps(BaseModel):
    """Card component properties"""
    model_config = ConfigDict(frozen=False)
    
    title: str = Field(..., description="Card title")
    description: str | None = Field(default=None)
    icon: str | None = Field(default=None)
    variant: str = Field(default="default", description="Card style variant")
    onClick: Callable | None = Field(default=None, description="Click handler")


class Card(rx.Component):
    """
    Atomic Design: ATOM
    Basic card container with title and content
    """
    tag = "div"
    
    # Props
    title: rx.Var[str]
    description: rx.Var[str] | None = None
    variant: rx.Var[str] = "default"
    
    @staticmethod
    def render(title: str, description: str | None = None, children=None):
        return rx.box(
            rx.vstack(
                # Card header
                rx.hstack(
                    rx.heading(title, size="md", font_weight="bold"),
                    spacing="md",
                ),
                # Card description
                rx.cond(
                    description is not None,
                    rx.text(description, font_size="sm", color="gray"),
                ),
                # Card content
                rx.box(children) if children else None,
                spacing="md",
                width="100%",
            ),
            border="1px solid",
            border_color="var(--color-border)",
            border_radius="lg",
            padding="md",
            background_color="var(--color-surface)",
            box_shadow="var(--shadow-md)",
        )


class Badge(rx.Component):
    """
    Atomic Design: ATOM
    Status badge with color coding
    """
    tag = "span"
    
    status: rx.Var[str]
    
    @staticmethod
    def render(status: str):
        color_map = {
            "active": "#10B981",
            "pending": "#F59E0B",
            "error": "#EF4444",
            "success": "#10B981",
        }
        
        return rx.box(
            rx.text(status, font_size="xs", font_weight="bold"),
            background_color=color_map.get(status.lower(), "#6B7280"),
            color="white",
            padding="px py",
            border_radius="full",
            display="inline-block",
        )


class SkeletonLoader(rx.Component):
    """
    Atomic Design: ATOM
    Placeholder loader for async content
    """
    tag = "div"
    
    @staticmethod
    def render():
        return rx.box(
            rx.vstack(
                rx.skeleton(height="20px", width="100%"),
                rx.skeleton(height="20px", width="80%"),
                rx.skeleton(height="40px", width="100%"),
                spacing="md",
            ),
            animation="pulse",
        )


class LoadingSpinner(rx.Component):
    """
    Atomic Design: ATOM
    Animated loading indicator
    """
    tag = "div"
    
    @staticmethod
    def render(size: str = "md"):
        return rx.spinner(
            color="var(--color-primary)",
            size=size,
        )
