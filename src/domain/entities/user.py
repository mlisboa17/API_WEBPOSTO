"""
CLAUDE 3.7: User Domain Entity with RBAC & DDD Patterns
Implements:
- Domain entity (not ORM model)
- Business logic for permissions
- Value objects for roles
- Aggregate root pattern
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Set
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime, timezone


class Role(str, Enum):
    """User roles (value object)"""
    ADMIN = "ADMIN"
    DIRECTOR = "DIRECTOR"
    PARTNER = "PARTNER"
    VIEWER = "VIEWER"


class Permission(str, Enum):
    """Available permissions (value object)"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    AUDIT = "audit"
    ADMIN = "admin"
    EXPORT = "export"


class RolePermissionMap:
    """Role to permission mapping (static)"""
    
    PERMISSIONS = {
        Role.ADMIN: {
            Permission.READ, Permission.WRITE, Permission.DELETE,
            Permission.AUDIT, Permission.ADMIN, Permission.EXPORT
        },
        Role.DIRECTOR: {
            Permission.READ, Permission.WRITE, Permission.DELETE,
            Permission.AUDIT, Permission.EXPORT
        },
        Role.PARTNER: {
            Permission.READ, Permission.WRITE, Permission.EXPORT
        },
        Role.VIEWER: {
            Permission.READ
        }
    }
    
    @staticmethod
    def get_permissions(role: Role) -> Set[Permission]:
        """Get all permissions for role"""
        return RolePermissionMap.PERMISSIONS.get(role, set())
    
    @staticmethod
    def has_permission(role: Role, permission: Permission) -> bool:
        """Check if role has specific permission"""
        return permission in RolePermissionMap.get_permissions(role)


class UserId(BaseModel):
    """Value object for user ID"""
    model_config = ConfigDict(frozen=True)
    
    value: str = Field(..., min_length=1)
    
    def __str__(self):
        return self.value
    
    def __eq__(self, other):
        if isinstance(other, UserId):
            return self.value == other.value
        return False


class UserEmail(BaseModel):
    """Value object for email"""
    model_config = ConfigDict(frozen=True)
    
    value: str = Field(..., min_length=5, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    
    @field_validator('value')
    def normalize_email(cls, v):
        """Normalize email (lowercase)"""
        return v.lower()
    
    def __str__(self):
        return self.value


class UserEntity(BaseModel):
    """
    User Domain Entity (Aggregate Root)
    - Not tied to ORM
    - Contains business logic
    - Pure domain logic
    """
    model_config = ConfigDict(strict=True)
    
    # Identity
    user_id: UserId = Field(...)
    email: UserEmail = Field(...)
    name: str = Field(..., min_length=1, max_length=255)
    
    # Role & permissions
    role: Role = Field(...)
    company_id: str = Field(..., min_length=1)
    
    # State
    is_active: bool = Field(default=True)
    is_email_verified: bool = Field(default=False)
    is_mfa_enabled: bool = Field(default=False)
    
    # Audit trail
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login_at: datetime = Field(default=None)
    last_password_change: datetime = Field(default=None)
    
    # Security
    login_attempts: int = Field(default=0)
    is_locked: bool = Field(default=False)
    lock_until: datetime = Field(default=None)
    
    # ========================================================================
    # Business Logic Methods (Domain)
    # ========================================================================
    
    def has_permission(self, permission: Permission) -> bool:
        """
        Check if user has specific permission
        
        Args:
            permission: Permission to check
            
        Returns:
            True if user has permission
        """
        if not self.is_active:
            return False
        
        return RolePermissionMap.has_permission(self.role, permission)
    
    def can_write(self) -> bool:
        """Can user write/edit data?"""
        return self.has_permission(Permission.WRITE)
    
    def can_delete(self) -> bool:
        """Can user delete data?"""
        return self.has_permission(Permission.DELETE)
    
    def can_audit(self) -> bool:
        """Can user view audit logs?"""
        return self.has_permission(Permission.AUDIT)
    
    def is_director_or_admin(self) -> bool:
        """Is user director or admin?"""
        return self.role in (Role.DIRECTOR, Role.ADMIN)
    
    def is_admin(self) -> bool:
        """Is user admin?"""
        return self.role == Role.ADMIN
    
    def record_login_attempt(self, success: bool = False) -> None:
        """
        Record login attempt (for brute-force protection)
        
        Args:
            success: Whether login succeeded
        """
        if success:
            self.login_attempts = 0
            self.last_login_at = datetime.now(timezone.utc)
            self.is_locked = False
        else:
            self.login_attempts += 1
            
            if self.login_attempts >= 5:
                self.is_locked = True
                self.lock_until = datetime.now(timezone.utc) + \
                    timedelta(minutes=15)
    
    def is_temporarily_locked(self) -> bool:
        """Is user temporarily locked out?"""
        if not self.is_locked:
            return False
        
        # Check if lock has expired
        if self.lock_until and datetime.now(timezone.utc) > self.lock_until:
            self.is_locked = False
            self.login_attempts = 0
            return False
        
        return True
    
    def unlock(self) -> None:
        """Unlock user account"""
        self.is_locked = False
        self.login_attempts = 0
        self.lock_until = None
    
    def update_password(self) -> None:
        """Record password change"""
        self.last_password_change = datetime.now(timezone.utc)
    
    def enable_mfa(self) -> None:
        """Enable multi-factor authentication"""
        self.is_mfa_enabled = True
    
    def disable_mfa(self) -> None:
        """Disable multi-factor authentication"""
        self.is_mfa_enabled = False
    
    def verify_email(self) -> None:
        """Mark email as verified"""
        self.is_email_verified = True
    
    # ========================================================================
    # Validation Methods
    # ========================================================================
    
    def can_perform_action(self, permission: Permission) -> bool:
        """
        Check if user can perform action (composite check)
        
        Args:
            permission: Action permission
            
        Returns:
            True if user can perform action
        """
        # Must be active
        if not self.is_active:
            return False
        
        # Must not be locked
        if self.is_temporarily_locked():
            return False
        
        # Must have permission
        if not self.has_permission(permission):
            return False
        
        return True
    
    def to_auth_payload(self) -> dict:
        """Convert to JWT token payload"""
        return {
            "sub": str(self.user_id),
            "email": str(self.email),
            "role": self.role.value,
            "company_id": self.company_id,
            "is_mfa_enabled": self.is_mfa_enabled
        }
    
    # ========================================================================
    # Temporal Methods
    # ========================================================================
    
    def days_since_last_login(self) -> int:
        """Days since last login"""
        if not self.last_login_at:
            return None
        
        delta = datetime.now(timezone.utc) - self.last_login_at
        return delta.days
    
    def days_since_password_change(self) -> int:
        """Days since password last changed"""
        if not self.last_password_change:
            return None
        
        delta = datetime.now(timezone.utc) - self.last_password_change
        return delta.days
    
    def should_change_password(self, max_days: int = 90) -> bool:
        """Should user change password? (security policy)"""
        days = self.days_since_password_change()
        return days is None or days > max_days


# ============================================================================
# Factory Methods
# ============================================================================

def create_user(
    user_id: str,
    email: str,
    name: str,
    role: Role = Role.VIEWER,
    company_id: str = ""
) -> UserEntity:
    """Factory method for creating users"""
    return UserEntity(
        user_id=UserId(value=user_id),
        email=UserEmail(value=email),
        name=name,
        role=role,
        company_id=company_id
    )


# ============================================================================
# Examples
# ============================================================================

if __name__ == "__main__":
    from timedelta import timedelta
    
    print("👤 User Domain Entity Examples")
    
    # Create user
    user = create_user(
        user_id="usr_123",
        email="director@company.com",
        name="João Silva",
        role=Role.DIRECTOR,
        company_id="comp_456"
    )
    
    print(f"\n✅ User created: {user.name}")
    print(f"   Role: {user.role}")
    print(f"   Can write: {user.can_write()}")
    print(f"   Can audit: {user.can_audit()}")
    print(f"   Is director: {user.is_director_or_admin()}")
    
    # Test login attempts
    print(f"\n📊 Login attempts:")
    for i in range(1, 7):
        user.record_login_attempt(success=False)
        print(f"   Attempt {i}: locked={user.is_locked}")
    
    # Test unlock
    user.unlock()
    print(f"   After unlock: locked={user.is_locked}")
    
    # Test permissions by role
    print(f"\n🔐 Permissions by role:")
    for role in Role:
        perms = RolePermissionMap.get_permissions(role)
        print(f"   {role.value}: {[p.value for p in perms]}")
