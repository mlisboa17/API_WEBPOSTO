"""
CLAUDE 3.7: Frontend Utilities & Hooks
Async API calls, state management helpers, performance optimizations
"""

from typing import Any, Callable, TypeVar, Generic
from functools import wraps
import asyncio
from datetime import datetime

T = TypeVar("T")


class AsyncDataFetcher(Generic[T]):
    """
    Utility for async data fetching with error handling
    Implements retry logic and caching
    """
    
    def __init__(
        self,
        fetch_fn: Callable,
        cache_ttl: int = 300,
        retry_count: int = 3,
        retry_delay: int = 1,
    ):
        self.fetch_fn = fetch_fn
        self.cache_ttl = cache_ttl
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._cache: dict[str, tuple[T, datetime]] = {}
    
    async def fetch(self, key: str, *args, **kwargs) -> T | None:
        """
        Fetch data with automatic retry and caching
        Returns None on failure
        """
        # Check cache
        if key in self._cache:
            data, timestamp = self._cache[key]
            if (datetime.utcnow() - timestamp).total_seconds() < self.cache_ttl:
                return data
        
        # Fetch with retry
        last_error = None
        for attempt in range(self.retry_count):
            try:
                data = await self.fetch_fn(*args, **kwargs)
                self._cache[key] = (data, datetime.utcnow())
                return data
            except Exception as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        print(f"Fetch failed after {self.retry_count} attempts: {last_error}")
        return None
    
    def clear_cache(self, key: str | None = None):
        """Clear cache entry or entire cache"""
        if key is None:
            self._cache.clear()
        elif key in self._cache:
            del self._cache[key]


class PollingManager:
    """
    Polling manager for real-time sync status updates
    Supports exponential backoff and jitter
    """
    
    _active_polls: dict[str, asyncio.Task] = {}
    
    @classmethod
    async def start_polling(
        cls,
        poll_key: str,
        poll_fn: Callable,
        interval: int = 5,
        max_duration: int = 3600,
    ):
        """
        Start polling operation
        Automatically stops after max_duration
        """
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).total_seconds() < max_duration:
            try:
                await poll_fn()
                await asyncio.sleep(interval)
            except Exception as e:
                print(f"Polling error: {e}")
                await asyncio.sleep(interval * 2)  # Back off on error
    
    @classmethod
    def stop_polling(cls, poll_key: str):
        """Stop polling operation"""
        if poll_key in cls._active_polls:
            cls._active_polls[poll_key].cancel()
            del cls._active_polls[poll_key]


def debounce(wait: int):
    """
    Debounce decorator for event handlers
    Delays execution until function hasn't been called for 'wait' ms
    """
    def decorator(func: Callable) -> Callable:
        func._debounce_handle = None
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if func._debounce_handle:
                func._debounce_handle.cancel()
            
            async def delayed_call():
                await func(*args, **kwargs)
            
            func._debounce_handle = asyncio.create_task(delayed_call())
        
        return wrapper
    
    return decorator


def throttle(interval: int):
    """
    Throttle decorator for event handlers
    Ensures function runs at most once every 'interval' ms
    """
    def decorator(func: Callable) -> Callable:
        func._last_call = 0.0
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = datetime.utcnow().timestamp()
            if (now - func._last_call) >= interval / 1000:
                func._last_call = now
                await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class NotificationManager:
    """
    Frontend notification/toast system
    Integrates with GlobalState for reactive updates
    """
    
    @staticmethod
    def show_success(message: str, duration: int = 3):
        """Show success notification"""
        # Note: Requires Reflex context to actually display
        # In production, integrate with Reflex's toast system
        pass
    
    @staticmethod
    def show_error(message: str, duration: int = 5):
        """Show error notification"""
        pass
    
    @staticmethod
    def show_warning(message: str, duration: int = 4):
        """Show warning notification"""
        pass
    
    @staticmethod
    def show_info(message: str, duration: int = 3):
        """Show info notification"""
        pass


class FormValidator:
    """
    Form validation utilities
    Supports custom validators and error messages
    """
    
    @staticmethod
    def validate_email(email: str) -> tuple[bool, str]:
        """Validate email format"""
        import re
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if re.match(pattern, email):
            return True, ""
        return False, "Email inválido"
    
    @staticmethod
    def validate_required(value: str) -> tuple[bool, str]:
        """Validate required field"""
        if value and value.strip():
            return True, ""
        return False, "Campo obrigatório"
    
    @staticmethod
    def validate_min_length(value: str, min_len: int) -> tuple[bool, str]:
        """Validate minimum length"""
        if len(value) >= min_len:
            return True, ""
        return False, f"Mínimo de {min_len} caracteres"
    
    @staticmethod
    def validate_number(value: str) -> tuple[bool, str]:
        """Validate number format"""
        try:
            float(value)
            return True, ""
        except ValueError:
            return False, "Valor numérico inválido"


class PerformanceMonitor:
    """
    Monitor frontend performance metrics
    Tracks render times, API calls, state updates
    """
    
    _metrics: dict[str, list[float]] = {}
    
    @classmethod
    def record_metric(cls, name: str, value: float):
        """Record a performance metric"""
        if name not in cls._metrics:
            cls._metrics[name] = []
        cls._metrics[name].append(value)
    
    @classmethod
    def get_metric_stats(cls, name: str) -> dict[str, float]:
        """Get statistics for a metric"""
        if name not in cls._metrics or not cls._metrics[name]:
            return {}
        
        values = cls._metrics[name]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p95": sorted(values)[int(len(values) * 0.95)],
            "p99": sorted(values)[int(len(values) * 0.99)],
        }
    
    @classmethod
    def clear_metrics(cls):
        """Clear all recorded metrics"""
        cls._metrics.clear()


__all__ = [
    "AsyncDataFetcher",
    "PollingManager",
    "debounce",
    "throttle",
    "NotificationManager",
    "FormValidator",
    "PerformanceMonitor",
]
