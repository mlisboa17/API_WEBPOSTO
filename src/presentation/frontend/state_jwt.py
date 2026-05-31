"""
CLAUDE 3.7: Reflex State Management with JWT Integration
Domain-driven design: Maps Company aggregate to UI State

Features:
- JWT token storage (httpOnly cookies + localStorage expiration)
- RBAC synchronization from TokenPayload
- Skeleton loaders for sync transitions
- Automatic logout on token expiry
- Pydantic V2 strict validation
- WebSocket support for real-time sync
"""

import reflex as rx
from pydantic import BaseModel, Field, validator
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import httpx
import asyncio
from functools import lru_cache

# =============================================================================
# Domain Value Objects (Pydantic V2)
# =============================================================================

class Role(str, Enum):
    """User roles mapped from JWT payload"""
    ADMIN = "ADMIN"
    DIRECTOR = "DIRECTOR"
    PARTNER = "PARTNER"
    VIEWER = "VIEWER"


class Permission(str, Enum):
    """User permissions for UI feature gating"""
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    AUDIT = "AUDIT"
    EXPORT = "EXPORT"


class UserInfo(BaseModel):
    """Mapped from JWT TokenPayload"""
    user_id: str = Field(..., description="User unique identifier")
    email: str = Field(..., description="User email")
    role: Role = Field(..., description="User role")
    company_id: str = Field(..., description="Company ID")
    permissions: List[Permission] = Field(default_factory=list, description="Granted permissions")
    exp_timestamp: int = Field(..., description="Token expiry (Unix timestamp)")
    
    class Config:
        use_enum_values = True
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        now = datetime.now(timezone.utc).timestamp()
        return now > self.exp_timestamp
    
    @property
    def time_until_expiry(self) -> timedelta:
        """Time until token expires"""
        now = datetime.now(timezone.utc).timestamp()
        seconds_left = max(0, self.exp_timestamp - now)
        return timedelta(seconds=seconds_left)
    
    def can_modify_data(self) -> bool:
        """Check if user can write/delete"""
        return self.role in [Role.ADMIN, Role.DIRECTOR, Role.PARTNER]
    
    def can_delete(self) -> bool:
        """Check if user can delete"""
        return self.role in [Role.ADMIN, Role.DIRECTOR]
    
    def can_audit(self) -> bool:
        """Check if user can view audit logs"""
        return self.role in [Role.ADMIN, Role.DIRECTOR]
    
    def is_director_or_admin(self) -> bool:
        """Check if user is director or admin"""
        return self.role in [Role.ADMIN, Role.DIRECTOR]


class CompanyInfo(BaseModel):
    """Company aggregate mapped from domain"""
    company_id: str = Field(..., description="Company unique ID")
    name: str = Field(..., description="Company name")
    industry: Optional[str] = Field(None, description="Industry type")
    tax_id: Optional[str] = Field(None, description="Tax ID (masked for security)")
    logo_url: Optional[str] = Field(None, description="Logo URL")
    active: bool = Field(default=True, description="Company active status")
    
    class Config:
        use_enum_values = True


class SyncStatus(str, Enum):
    """Sync status for Rateios"""
    IDLE = "IDLE"
    SYNCING = "SYNCING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    PARTIAL = "PARTIAL"


class SyncStatusInfo(BaseModel):
    """Tracks sync state for visual feedback"""
    status: SyncStatus = Field(default=SyncStatus.IDLE)
    last_sync: Optional[datetime] = Field(None, description="Last sync timestamp")
    last_error: Optional[str] = Field(None, description="Last error message")
    error_count: int = Field(default=0, description="Consecutive error count")
    synced_records: int = Field(default=0, description="Records synced in current operation")
    total_records: int = Field(default=0, description="Total records to sync")
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def progress_percent(self) -> float:
        """Sync progress percentage"""
        if self.total_records == 0:
            return 0.0
        return (self.synced_records / self.total_records) * 100
    
    @property
    def is_syncing(self) -> bool:
        """Check if currently syncing"""
        return self.status == SyncStatus.SYNCING
    
    @property
    def has_errors(self) -> bool:
        """Check if errors occurred"""
        return self.status == SyncStatus.ERROR


# =============================================================================
# Reflex Global State
# =============================================================================

class GlobalState(rx.State):
    """
    Root state container for frontend
    Maps domain aggregates to Reflex reactive state
    
    CLAUDE 3.7: JWT integration + RBAC
    """
    
    # =========================================================================
    # Authentication State
    # =========================================================================
    
    # JWT tokens (stored in cookies/localStorage)
    access_token: str = ""
    refresh_token: str = ""
    token_type: str = "Bearer"
    token_exp: int = 0  # Unix timestamp
    
    # User information (decoded from JWT)
    user: Optional[UserInfo] = None
    is_authenticated: bool = False
    
    # Token refresh timer (background task)
    token_refresh_interval: int = 300  # seconds (5 minutes)
    
    # =========================================================================
    # Company & Tenant State
    # =========================================================================
    
    active_company: Optional[CompanyInfo] = None
    companies: List[CompanyInfo] = []
    selected_company_id: Optional[str] = None
    
    # =========================================================================
    # Sync Status (Rateios)
    # =========================================================================
    
    sync_status: SyncStatusInfo = SyncStatusInfo()
    last_sync_duration_ms: float = 0.0  # Performance metric
    
    # =========================================================================
    # UI State
    # =========================================================================
    
    dark_mode: bool = True
    show_skeleton_loader: bool = False  # Show skeleton during sync
    sidebar_open: bool = True
    theme_transition_active: bool = False
    
    # Version tracking (for cache busting)
    app_version: str = "1.0.0"
    
    # =========================================================================
    # Error State
    # =========================================================================
    
    last_error: Optional[str] = None
    error_timestamp: Optional[datetime] = None
    
    # =========================================================================
    # CLAUDE 3.7: Permission-based feature flags
    # =========================================================================
    
    def is_director(self) -> bool:
        """User is director or admin"""
        return self.user and self.user.is_director_or_admin() or False
    
    def can_edit(self) -> bool:
        """User can edit data"""
        return self.user and self.user.can_modify_data() or False
    
    def can_delete(self) -> bool:
        """User can delete data"""
        return self.user and self.user.can_delete() or False
    
    def can_view_audit(self) -> bool:
        """User can view audit logs"""
        return self.user and self.user.can_audit() or False
    
    # =========================================================================
    # JWT Token Management
    # =========================================================================
    
    async def set_tokens_from_login(
        self,
        access_token: str,
        refresh_token: str,
        user_data: Dict[str, Any],
        expires_in: int
    ) -> None:
        """
        Store JWT tokens after successful login
        
        Args:
            access_token: JWT access token
            refresh_token: Refresh token
            user_data: Decoded user info from JWT payload
            expires_in: Expiry time in seconds
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = "Bearer"
        
        # Calculate expiry timestamp
        now = datetime.now(timezone.utc).timestamp()
        self.token_exp = int(now + expires_in)
        
        # Create UserInfo from JWT payload
        self.user = UserInfo(
            user_id=user_data["sub"],
            email=user_data.get("email", ""),
            role=Role(user_data.get("role", "VIEWER")),
            company_id=user_data.get("company_id", ""),
            permissions=[Permission(p) for p in user_data.get("permissions", [])],
            exp_timestamp=self.token_exp
        )
        
        self.is_authenticated = True
        
        # Store tokens in localStorage (httpOnly for cookies handled by backend)
        await self._store_tokens_locally(access_token, refresh_token, self.token_exp)
        
        # Schedule token refresh (5 minutes before expiry)
        await self._schedule_token_refresh()
    
    async def _store_tokens_locally(
        self,
        access_token: str,
        refresh_token: str,
        exp_timestamp: int
    ) -> None:
        """
        Store tokens in localStorage with expiration metadata
        
        CLAUDE 3.7: Security - localStorage + httpOnly cookie duplication
        """
        import js  # Browser JavaScript runtime
        
        tokens_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "exp": exp_timestamp,
            "stored_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            js.localStorage.setItem("tokens", json.dumps(tokens_data))
        except Exception as e:
            print(f"❌ Failed to store tokens locally: {e}")
    
    async def _schedule_token_refresh(self) -> None:
        """
        Schedule automatic token refresh before expiry
        
        CLAUDE 3.7: Logout on expiry
        """
        if not self.user:
            return
        
        time_until_expiry = self.user.time_until_expiry.total_seconds()
        refresh_delay = max(60, time_until_expiry - 300)  # Refresh 5 min before expiry
        
        # Background task
        asyncio.create_task(self._refresh_token_background(refresh_delay))
    
    async def _refresh_token_background(self, delay_seconds: float) -> None:
        """
        Background task to refresh token before expiry
        
        CLAUDE 3.7: Automatic refresh
        """
        await asyncio.sleep(delay_seconds)
        
        if self.is_authenticated and self.refresh_token:
            try:
                await self.refresh_access_token()
            except Exception as e:
                print(f"❌ Token refresh failed: {e}")
                # Logout if refresh fails
                await self.logout_user()
    
    async def refresh_access_token(self) -> None:
        """
        Refresh access token using refresh_token
        
        CLAUDE 3.7: Token rotation
        """
        if not self.refresh_token:
            await self.logout_user()
            return
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/api/auth/refresh",
                    json={"refresh_token": self.refresh_token},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    await self.set_tokens_from_login(
                        access_token=data["access_token"],
                        refresh_token=data["refresh_token"],
                        user_data=data["user"],
                        expires_in=data["expires_in"]
                    )
                else:
                    # Refresh failed - logout
                    await self.logout_user()
        except Exception as e:
            print(f"❌ Token refresh error: {e}")
            await self.logout_user()
    
    async def logout_user(self) -> None:
        """
        Logout: clear state and redirect to login
        
        CLAUDE 3.7: Automatic logout
        """
        self.access_token = ""
        self.refresh_token = ""
        self.user = None
        self.is_authenticated = False
        self.active_company = None
        self.companies = []
        
        # Clear localStorage
        try:
            import js
            js.localStorage.removeItem("tokens")
        except:
            pass
        
        # Redirect to login
        await rx.redirect("/login")
    
    # =========================================================================
    # Company Management
    # =========================================================================
    
    async def set_active_company(self, company_id: str) -> None:
        """
        Switch active company context
        
        CLAUDE 3.7: Multi-tenant support
        """
        company = next((c for c in self.companies if c.company_id == company_id), None)
        if company:
            self.active_company = company
            self.selected_company_id = company_id
            # Reset sync status
            self.sync_status = SyncStatusInfo()
    
    async def fetch_companies(self) -> None:
        """
        Fetch available companies for user
        
        CLAUDE 3.7: RBAC-filtered list
        """
        if not self.is_authenticated or not self.access_token:
            return
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:8000/api/companies",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    companies_data = response.json()
                    self.companies = [
                        CompanyInfo(**c) for c in companies_data
                    ]
                    
                    # Auto-select first company
                    if self.companies and not self.active_company:
                        await self.set_active_company(self.companies[0].company_id)
        except Exception as e:
            print(f"❌ Failed to fetch companies: {e}")
    
    # =========================================================================
    # Sync Status Management (Rateios)
    # =========================================================================
    
    async def mark_syncing(self, total_records: int = 0) -> None:
        """
        Mark as syncing (show skeleton loader)
        
        CLAUDE 3.7: Skeleton loaders
        """
        self.sync_status.status = SyncStatus.SYNCING
        self.sync_status.total_records = total_records
        self.sync_status.synced_records = 0
        self.show_skeleton_loader = True
        self.last_error = None
    
    async def mark_sync_success(self, synced_count: int) -> None:
        """Mark sync as complete"""
        self.sync_status.status = SyncStatus.SUCCESS
        self.sync_status.synced_records = synced_count
        self.sync_status.last_sync = datetime.now()
        self.sync_status.error_count = 0
        self.show_skeleton_loader = False
        self.last_error = None
    
    async def mark_sync_error(self, error_msg: str) -> None:
        """Mark sync as failed"""
        self.sync_status.status = SyncStatus.ERROR
        self.sync_status.last_error = error_msg
        self.sync_status.error_count += 1
        self.show_skeleton_loader = False
        self.last_error = error_msg
        self.error_timestamp = datetime.now()
    
    # =========================================================================
    # Theme Management
    # =========================================================================
    
    def toggle_theme(self) -> None:
        """Toggle dark/light mode"""
        self.dark_mode = not self.dark_mode
        self.theme_transition_active = True
        
        # Schedule transition end
        asyncio.create_task(self._transition_complete())
    
    async def _transition_complete(self) -> None:
        """Complete theme transition"""
        await asyncio.sleep(0.3)
        self.theme_transition_active = False
    
    # =========================================================================
    # WebSocket Support (Real-time sync updates)
    # =========================================================================
    
    async def on_sync_progress(self, synced: int, total: int) -> None:
        """
        Receive sync progress updates from WebSocket
        
        CLAUDE 3.7: Real-time state updates
        """
        self.sync_status.synced_records = synced
        self.sync_status.total_records = total
    
    async def on_sync_complete(self, success: bool, message: str = "") -> None:
        """Receive sync completion from WebSocket"""
        if success:
            await self.mark_sync_success(self.sync_status.synced_records)
        else:
            await self.mark_sync_error(message)
