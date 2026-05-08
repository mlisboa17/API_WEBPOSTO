from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "webposto-service"}


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"ready": True, "service": "webposto-service"}
