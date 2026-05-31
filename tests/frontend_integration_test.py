"""
FRONTEND: Integration Test & Type Validation
CLAUDE 3.7 + GROK 4: Verify all imports and types are correct
"""

import pytest
from typing import TYPE_CHECKING

# Test imports
try:
    from src.presentation.frontend.state import GlobalState, UserSession, UserRole, CompanyInfo, SyncStatusInfo
    from src.presentation.frontend.styles import GLOBAL_THEME, LOGOS_DARK, LOGOS_LIGHT
    from src.presentation.frontend.components import (
        Card, Badge, SkeletonLoader, LoadingSpinner,
        SyncProgressBar, CompanySelector, DashboardCard, AuditFeedItem,
        RateioChart, TimeSeriesChart, MetricsGrid,
    )
    from src.presentation.frontend.router import PermissionRouter, require_auth, require_director
    from src.presentation.frontend.utils import (
        AsyncDataFetcher, PollingManager, debounce, throttle,
        NotificationManager, FormValidator, PerformanceMonitor,
    )
    from src.presentation.frontend.animations import (
        AnimationType, AnimationConfig, animate, MotionCard, MotionButton,
    )
    IMPORTS_OK = True
except ImportError as e:
    IMPORTS_OK = False
    IMPORT_ERROR = str(e)


class TestFrontendState:
    """Test GlobalState and domain models"""
    
    def test_user_session_creation(self):
        """Test UserSession instantiation"""
        user = UserSession(
            user_id="test_user",
            email="test@example.com",
            name="Test User",
            role=UserRole.PARTNER,
            is_authenticated=True,
        )
        assert user.user_id == "test_user"
        assert user.is_partner()
        assert not user.is_director()
    
    def test_global_state_creation(self):
        """Test GlobalState instantiation"""
        state = GlobalState()
        assert state.version == 1
        assert state.is_dark_mode is True
        assert state.is_authenticated() is False
    
    def test_global_state_methods(self):
        """Test GlobalState helper methods"""
        user = UserSession(
            user_id="user1",
            email="user@test.com",
            name="User",
            role=UserRole.DIRECTOR,
            is_authenticated=True,
        )
        
        state = GlobalState(user=user)
        assert state.is_authenticated() is True
        assert state.can_modify_data() is True
        assert state.get_user_role() == UserRole.DIRECTOR
    
    def test_sync_status_transitions(self):
        """Test SyncStatus state transitions"""
        sync = SyncStatusInfo(status=SyncStatusInfo.status)
        
        # Start sync
        sync.status = "syncing"
        assert sync.is_syncing
        
        # Complete sync
        sync.status = "success"
        assert not sync.has_error
    
    def test_theme_switching(self):
        """Test theme configuration"""
        from src.presentation.frontend.styles import ThemeSystem
        
        theme = ThemeSystem()
        assert theme.config.mode == "dark"
        
        theme.switch_theme("light")
        assert theme.config.mode == "light"
        
        theme.switch_theme("dark")
        assert theme.config.mode == "dark"


class TestFormValidator:
    """Test form validation utilities"""
    
    def test_email_validation(self):
        """Test email format validation"""
        valid, msg = FormValidator.validate_email("test@example.com")
        assert valid is True
        
        invalid, msg = FormValidator.validate_email("invalid-email")
        assert invalid is False
        assert "Email inválido" in msg
    
    def test_required_field(self):
        """Test required field validation"""
        valid, msg = FormValidator.validate_required("value")
        assert valid is True
        
        invalid, msg = FormValidator.validate_required("")
        assert invalid is False
        assert "obrigatório" in msg
    
    def test_number_validation(self):
        """Test number validation"""
        valid, msg = FormValidator.validate_number("123.45")
        assert valid is True
        
        invalid, msg = FormValidator.validate_number("not-a-number")
        assert invalid is False


class TestPermissionRouter:
    """Test route protection"""
    
    def test_register_protected_route(self):
        """Test protected route registration"""
        PermissionRouter.register_protected_route(
            path="/admin",
            required_role=UserRole.DIRECTOR,
        )
        assert "/admin" in PermissionRouter._protected_routes
    
    def test_create_auth_page_wrapper(self):
        """Test page wrapper creation"""
        def test_page():
            return "Test Page"
        
        wrapped = PermissionRouter.create_auth_page_wrapper(
            test_page,
            required_role=UserRole.PARTNER,
        )
        assert callable(wrapped)


class TestAnimations:
    """Test animation system"""
    
    def test_animation_config(self):
        """Test animation configuration"""
        config = AnimationConfig(
            animation_type=AnimationType.FADE_IN,
            duration=0.5,
            delay=0.1,
        )
        assert config.animation_type == AnimationType.FADE_IN
        assert config.duration == 0.5
        assert config.delay == 0.1
    
    def test_motion_variants(self):
        """Test motion variants"""
        from src.presentation.frontend.animations import MOTION_VARIANTS
        
        assert "card_enter" in MOTION_VARIANTS
        assert "modal_enter" in MOTION_VARIANTS
        assert "sidebar_enter" in MOTION_VARIANTS


class TestThemeSystem:
    """Test theme configuration"""
    
    def test_theme_colors(self):
        """Test theme color definitions"""
        assert len(LOGOS_DARK) > 0
        assert len(LOGOS_LIGHT) > 0
        assert "primary" in LOGOS_DARK
        assert "primary" in LOGOS_LIGHT
    
    def test_theme_css_variables(self):
        """Test CSS variable generation"""
        config = GLOBAL_THEME.config
        css_vars = config.to_css_variables()
        
        assert "--color-primary" in css_vars
        assert "--color-secondary" in css_vars
        assert "--color-text" in css_vars


# Integration test
def test_imports():
    """Verify all imports successful"""
    assert IMPORTS_OK, f"Import failed: {IMPORT_ERROR if 'IMPORT_ERROR' in dir() else 'Unknown error'}"


def test_full_workflow():
    """Test complete state workflow"""
    # Create user
    user = UserSession(
        user_id="test",
        email="test@test.com",
        name="Test",
        role=UserRole.DIRECTOR,
        is_authenticated=True,
    )
    
    # Create state
    state = GlobalState(user=user)
    
    # Set active company
    company = CompanyInfo(empresa_id="comp1", name="Test Company")
    state.set_active_company(company)
    
    # Start sync
    state.mark_syncing(total=100)
    assert state.sync_status.is_syncing
    
    # Complete sync
    state.mark_sync_success()
    assert state.sync_status.status.value == "success"
    
    # Verify version incremented
    assert state.version > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
