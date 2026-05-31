"""
GROK 4: Login Page - Secure authentication interface
Features:
- JWT token handling (access + refresh)
- Rate limiting feedback (429 errors)
- Form validation with email pattern
- Loading states with animations
- Responsive mobile-first design
- Dark mode by default

CLAUDE 3.7: Rate limiter integration
GEMINI 2.0: Performance optimization (sub-100ms)
"""

import reflex as rx
from typing import Optional
import re
import httpx
import asyncio
from state_jwt import GlobalState, UserInfo, Role


# =============================================================================
# Login State
# =============================================================================

class LoginState(GlobalState):
    """Login page-specific state"""
    
    email: str = ""
    password: str = ""
    
    # Form state
    is_submitting: bool = False
    form_error: Optional[str] = None
    form_success: bool = False
    show_password: bool = False
    
    # Rate limiting
    rate_limit_blocked: bool = False
    rate_limit_remaining: int = 0
    rate_limit_reset_at: Optional[str] = None
    
    # Validation
    email_valid: bool = True
    password_valid: bool = True
    
    # Success toast
    show_success: bool = False
    
    def validate_email(self) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        self.email_valid = bool(re.match(pattern, self.email))
        return self.email_valid
    
    def validate_password(self) -> bool:
        """Validate password (min 8 chars)"""
        self.password_valid = len(self.password) >= 8
        return self.password_valid
    
    def validate_form(self) -> bool:
        """Validate entire form"""
        email_ok = self.validate_email()
        password_ok = self.validate_password()
        return email_ok and password_ok
    
    async def handle_login(self) -> None:
        """
        Submit login form
        
        GROK 4: Rate limiter feedback
        CLAUDE 3.7: Token storage in httpOnly cookies
        """
        
        # Reset state
        self.form_error = None
        self.form_success = False
        
        # Validate
        if not self.validate_form():
            self.form_error = "Invalid email or password (min 8 chars)"
            return
        
        self.is_submitting = True
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8100/api/auth/login",
                    json={
                        "email": self.email,
                        "password": self.password,
                    },
                    timeout=10
                )
            
            # Handle responses
            if response.status_code == 200:
                # Success
                data = response.json()
                
                # Store tokens via GlobalState
                await self.set_tokens_from_login(
                    access_token=data["access_token"],
                    refresh_token=data["refresh_token"],
                    user_data=data["user"],
                    expires_in=data["expires_in"]
                )
                
                self.form_success = True
                self.show_success = True
                
                # Redirect to dashboard after delay
                await asyncio.sleep(1)
                await rx.redirect("/dashboard")
            
            elif response.status_code == 429:
                # Rate limited
                self.rate_limit_blocked = True
                headers = response.headers
                self.rate_limit_remaining = int(headers.get("X-RateLimit-Remaining", 0))
                self.rate_limit_reset_at = headers.get("Retry-After")
                
                self.form_error = f"Too many login attempts. Try again in {self.rate_limit_reset_at or '15 minutes'}"
            
            elif response.status_code == 401:
                # Invalid credentials
                self.form_error = "Invalid email or password"
                self.password = ""  # Clear password
            
            elif response.status_code == 423:
                # Account locked (brute force)
                self.form_error = "Account temporarily locked due to too many failed attempts. Try again later."
                self.password = ""
            
            else:
                # Other errors
                self.form_error = f"Login failed: {response.status_code}"
        
        except httpx.TimeoutException:
            self.form_error = "Server timeout. Please try again."
        
        except Exception as e:
            self.form_error = f"Error: {str(e)}"
        
        finally:
            self.is_submitting = False
    
    async def on_email_change(self, value: str) -> None:
        """Handle email input change"""
        self.email = value
        self.validate_email()
    
    async def on_password_change(self, value: str) -> None:
        """Handle password input change"""
        self.password = value
        self.validate_password()
    
    def toggle_password_visibility(self) -> None:
        """Toggle password visibility"""
        self.show_password = not self.show_password


# =============================================================================
# Login Page Components
# =============================================================================

def login_form() -> rx.Component:
    """
    Main login form component
    
    GROK 4: Form validation + animation + responsive
    """
    
    return rx.box(
        rx.vstack(
            # Header
            rx.vstack(
                rx.heading("🔐 Sign In", size="xl"),
                rx.text(
                    "Enter your credentials to access your account",
                    color="gray",
                    size="sm",
                ),
                spacing="2",
                text_align="center",
            ),
            
            rx.divider(),
            
            # Error message
            rx.cond(
                LoginState.form_error != "",
                rx.box(
                    rx.hstack(
                        rx.text("⚠️", font_size="lg"),
                        rx.text(LoginState.form_error, size="sm"),
                        width="100%",
                        align="center",
                    ),
                    padding="3",
                    bg="rgba(239, 68, 68, 0.1)",
                    border="1px solid #ef4444",
                    border_radius="md",
                    width="100%",
                ),
                rx.empty(),
            ),
            
            # Success message
            rx.cond(
                LoginState.show_success,
                rx.box(
                    rx.hstack(
                        rx.text("✓", font_size="lg", color="green"),
                        rx.text("Login successful! Redirecting...", size="sm"),
                        width="100%",
                        align="center",
                    ),
                    padding="3",
                    bg="rgba(16, 185, 129, 0.1)",
                    border="1px solid #10b981",
                    border_radius="md",
                    width="100%",
                ),
                rx.empty(),
            ),
            
            # Email input
            rx.vstack(
                rx.text("Email Address", font_weight="bold", size="sm"),
                rx.input(
                    placeholder="user@company.com",
                    value=LoginState.email,
                    on_change=LoginState.on_email_change,
                    type_="email",
                    width="100%",
                    padding="2",
                    border="1px solid #475569",
                    border_radius="md",
                    bg="#0f172a",
                    color="white",
                    _placeholder={"color": "#94a3b8"},
                ),
                rx.cond(
                    ~LoginState.email_valid & (LoginState.email != ""),
                    rx.text("Invalid email format", color="red", size="xs"),
                    rx.empty(),
                ),
                spacing="1",
                width="100%",
            ),
            
            # Password input
            rx.vstack(
                rx.hstack(
                    rx.text("Password", font_weight="bold", size="sm"),
                    rx.spacer(),
                    rx.link(
                        rx.text("Forgot?", size="xs", color="blue"),
                        href="/forgot-password"
                    ),
                    width="100%",
                ),
                rx.hstack(
                    rx.input(
                        placeholder="••••••••",
                        value=LoginState.password,
                        on_change=LoginState.on_password_change,
                        type_=rx.cond(LoginState.show_password, "text", "password"),
                        width="100%",
                        padding="2",
                        border="1px solid #475569",
                        border_radius="md",
                        bg="#0f172a",
                        color="white",
                    ),
                    rx.button(
                        rx.cond(LoginState.show_password, "👁️", "👁️‍🗨️"),
                        on_click=LoginState.toggle_password_visibility,
                        bg="transparent",
                        border="none",
                        color="gray",
                        cursor="pointer",
                    ),
                    width="100%",
                ),
                rx.cond(
                    ~LoginState.password_valid & (LoginState.password != ""),
                    rx.text("Password must be at least 8 characters", color="red", size="xs"),
                    rx.empty(),
                ),
                spacing="1",
                width="100%",
            ),
            
            # Rate limit warning
            rx.cond(
                LoginState.rate_limit_blocked,
                rx.box(
                    rx.vstack(
                        rx.text("🚫 Rate Limited", font_weight="bold", size="sm", color="orange"),
                        rx.text(
                            LoginState.form_error,
                            size="xs",
                            color="gray",
                        ),
                        spacing="1",
                    ),
                    padding="3",
                    bg="rgba(245, 158, 11, 0.1)",
                    border="1px solid #f59e0b",
                    border_radius="md",
                    width="100%",
                ),
                rx.empty(),
            ),
            
            # Submit button
            rx.button(
                rx.cond(
                    LoginState.is_submitting,
                    rx.hstack(
                        rx.spinner(size="sm", color="white"),
                        rx.text("Signing in..."),
                    ),
                    rx.text("Sign In")
                ),
                on_click=LoginState.handle_login,
                width="100%",
                padding="2",
                bg="linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)",
                color="white",
                font_weight="bold",
                border_radius="md",
                border="none",
                cursor="pointer",
                disabled=LoginState.is_submitting | LoginState.rate_limit_blocked,
                _hover={"opacity": 0.9},
            ),
            
            # Divider
            rx.hstack(
                rx.divider(),
                rx.text("or", color="gray", size="sm", font_weight="bold"),
                rx.divider(),
                width="100%",
                spacing="2",
            ),
            
            # Sign up link
            rx.hstack(
                rx.text("Don't have an account?", color="gray", size="sm"),
                rx.link(
                    rx.text("Sign up", color="blue", size="sm", font_weight="bold"),
                    href="/signup"
                ),
                width="100%",
                justify="center",
            ),
            
            spacing="4",
            width="100%",
        ),
        
        # Styling
        width="100%",
        max_width="400px",
        padding="6",
        border="1px solid #475569",
        border_radius="lg",
        bg="#1e293b",
        box_shadow="0 10px 30px rgba(0, 0, 0, 0.5)",
    )


def login_page() -> rx.Component:
    """
    Main login page
    
    GROK 4: Mobile-first responsive + dark mode + animations
    """
    
    return rx.box(
        rx.vstack(
            # Branding
            rx.vstack(
                rx.heading("Logos", size="2xl", color="#6366F1"),
                rx.text("Enterprise Sync Platform", color="gray", size="sm"),
                spacing="1",
                text_align="center",
            ),
            
            rx.spacer(),
            
            # Login form
            login_form(),
            
            rx.spacer(),
            
            # Footer
            rx.hstack(
                rx.link(rx.text("Privacy", size="xs", color="gray"), href="/privacy"),
                rx.text("•", color="gray", size="xs"),
                rx.link(rx.text("Terms", size="xs", color="gray"), href="/terms"),
                rx.text("•", color="gray", size="xs"),
                rx.link(rx.text("Support", size="xs", color="gray"), href="/support"),
                spacing="2",
                justify="center",
                width="100%",
            ),
            
            spacing="6",
            padding="6",
            min_height="100vh",
            align="center",
            justify="center",
        ),
        
        # Background
        width="100%",
        min_height="100vh",
        bg="linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)",
        color="white",
        overflow="hidden",
    )
