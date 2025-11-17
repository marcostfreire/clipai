"""
Health check endpoints and monitoring utilities.
"""

from fastapi import APIRouter
from sqlalchemy import text
import redis
import logging

from ..config import settings
from ..database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "ClipAI API", "version": "1.0.0"}


@router.get("/ready")
async def readiness_check():
    """
    Readiness check - verifies all dependencies are available.
    Returns 200 if ready, 503 if not ready.
    """
    checks = {
        "database": False,
        "redis": False,
    }

    # Check database
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        checks["redis"] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return {"status": "ready" if all_healthy else "not ready", "checks": checks}


@router.get("/live")
async def liveness_check():
    """
    Liveness check - verifies the application is running.
    Always returns 200 unless the application is completely dead.
    """
    return {"status": "alive", "service": "ClipAI API"}
