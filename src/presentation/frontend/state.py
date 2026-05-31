"""
CLAUDE 3.7: GlobalState - DDD State Management Layer
Pydantic V2 with strict typing for Reflex state synchronization
"""

from typing import ClassVar, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    """Role-based access control"""
    PARTNER = "partner"
    DIRECTOR = "director"
    VIEWER = "viewer"


class SyncStatus(str, Enum):
    """Data synchronization status"""
    IDLE = "idle"
    SYNCING = "syncing"
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class UserSession(BaseModel):
    """
    User session state - Atomic Design (Atom)
    Contains user identity and permissions
    """
    
    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        from_attributes=True,
    )
    
    user_id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User full name")
    role: UserRole = Field(default=UserRole.VIEWER, description="User role")
    is_authenticated: bool = Field(default=False, description="Auth state")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def has_permission(self, required_role: UserRole | list[UserRole]) -> bool:
        """Check if user has required permission"""
        if isinstance(required_role, list):
            return self.role in required_role
        return self.role == required_role or self.role == UserRole.DIRECTOR
    
    def is_director(self) -> bool:
        """Shortcut: check if director"""
        return self.role == UserRole.DIRECTOR
    
    def is_partner(self) -> bool:
        """Shortcut: check if partner"""
        return self.role in [UserRole.PARTNER, UserRole.DIRECTOR]


class CompanyInfo(BaseModel):
    """
    Active company context - Atomic Design (Atom)
    """
    
    model_config = ConfigDict(frozen=False)
    
    empresa_id: str = Field(..., description="Company ID")
    name: str = Field(..., description="Company name")
    status: Literal["active", "inactive"] = Field(default="active")
    last_sync: datetime | None = Field(default=None)


class SyncStatusInfo(BaseModel):
    """
    Synchronization status tracking - Atomic Design (Atom)
    """
    
    model_config = ConfigDict(frozen=False)
    
    status: SyncStatus = Field(default=SyncStatus.IDLE)
    last_sync: datetime | None = Field(default=None)
    progress_percent: int = Field(default=0, ge=0, le=100)
    error_message: str | None = Field(default=None)
    records_synced: int = Field(default=0, ge=0)
    total_records: int | None = Field(default=None)
    
    @property
    def is_syncing(self) -> bool:
        return self.status == SyncStatus.SYNCING
    
    @property
    def has_error(self) -> bool:
        return self.status == SyncStatus.ERROR


class GlobalState(BaseModel):
    """
    CLAUDE 3.7: Global application state
    Molecule: Composed of atomic states
    
    Used by Reflex for reactive updates:
    - Changes trigger UI re-render
    - Cached in Redis for performance
    - Version-controlled for optimistic locking
    """
    
    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        from_attributes=True,
        extra="forbid",
    )
    
    # User session
    user: UserSession | None = Field(default=None)
    
    # Active company context
    active_company: CompanyInfo | None = Field(default=None)
    available_companies: list[CompanyInfo] = Field(default_factory=list)
    
    # Sync status
    sync_status: SyncStatusInfo = Field(default_factory=SyncStatusInfo)
    
    # UI state
    is_dark_mode: bool = Field(default=True, description="Theme: Dark by default")
    sidebar_open: bool = Field(default=True)
    notification_count: int = Field(default=0, ge=0)
    
    # Versioning for optimistic locking
    version: int = Field(default=1, ge=1, description="State version")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # State management (class-level)
    _cache_ttl: ClassVar[int] = 3600  # 1 hour in seconds
    _redis_key: ClassVar[str] = "global_state"
    
    def is_authenticated(self) -> bool:
        """Check if user is logged in"""
        return self.user is not None and self.user.is_authenticated
    
    def get_user_role(self) -> UserRole | None:
        """Get current user role"""
        return self.user.role if self.user else None
    
    def can_view_analytics(self) -> bool:
        """Check analytics permission"""
        return self.is_authenticated() and self.user.is_partner()
    
    def can_modify_data(self) -> bool:
        """Check modification permission"""
        return self.is_authenticated() and self.user.is_director()
    
    def mark_syncing(self, total: int = 0) -> None:
        """Start sync operation"""
        self.sync_status.status = SyncStatus.SYNCING
        self.sync_status.progress_percent = 0
        self.sync_status.records_synced = 0
        self.sync_status.total_records = total if total > 0 else None
        self.sync_status.error_message = None
    
    def mark_sync_success(self) -> None:
        """Mark sync completed"""
        self.sync_status.status = SyncStatus.SUCCESS
        self.sync_status.progress_percent = 100
        self.sync_status.last_sync = datetime.utcnow()
    
    def mark_sync_error(self, error: str) -> None:
        """Mark sync failed"""
        self.sync_status.status = SyncStatus.ERROR
        self.sync_status.error_message = error
    
    def set_active_company(self, company: CompanyInfo) -> None:
        """Switch active company"""
        self.active_company = company
        self.version += 1
        self.updated_at = datetime.utcnow()
    
    def toggle_theme(self) -> None:
        """Switch between dark/light mode"""
        self.is_dark_mode = not self.is_dark_mode
        self.updated_at = datetime.utcnow()
    
    def increment_version(self) -> None:
        """Increment version for optimistic locking"""
        self.version += 1
        self.updated_at = datetime.utcnow()
