from fastapi import APIRouter
from src.infrastructure.config.database import engine

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint verifies DB connectivity."""
    # Simple DB check
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
    except Exception:
        return {"status": "unhealthy", "service": "webposto-service", "db": "down"}
    return {"status": "healthy", "service": "webposto-service", "db": "ok"}


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"ready": True, "service": "webposto-service"}
