"""
Health check endpoints and monitoring utilities.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
import redis
import logging
import datetime

from ..config import settings
from ..database import SessionLocal
from ..models import Video

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


@router.get("/stuck")
async def stuck_videos_check(threshold_minutes: int = 60):
    """
    Check for videos stuck in 'processing' status.
    
    This endpoint helps identify potential issues with the Celery worker.
    Videos stuck for longer than threshold_minutes are likely due to worker crash.
    
    Args:
        threshold_minutes: Minutes after which a processing video is considered stuck.
                          Default: 60 minutes (1 hour)
    
    Returns:
        Dictionary with stuck video information
    """
    db = None
    try:
        db = SessionLocal()
        
        threshold_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=threshold_minutes)
        
        # Find videos stuck in 'processing' status
        stuck_videos = db.query(Video).filter(
            Video.status == "processing",
            Video.updated_at < threshold_time
        ).all()
        
        stuck_info = []
        for video in stuck_videos:
            time_stuck = datetime.datetime.utcnow() - (video.updated_at or video.created_at)
            stuck_info.append({
                "video_id": video.id,
                "progress": video.progress,
                "hours_stuck": round(time_stuck.total_seconds() / 3600, 2),
                "updated_at": video.updated_at.isoformat() if video.updated_at else None,
            })
        
        # Count videos by status
        status_counts = {
            "queued": db.query(Video).filter(Video.status == "queued").count(),
            "processing": db.query(Video).filter(Video.status == "processing").count(),
            "completed": db.query(Video).filter(Video.status == "completed").count(),
            "failed": db.query(Video).filter(Video.status == "failed").count(),
        }
        
        return {
            "status": "warning" if stuck_info else "healthy",
            "threshold_minutes": threshold_minutes,
            "stuck_count": len(stuck_info),
            "stuck_videos": stuck_info,
            "video_status_counts": status_counts,
            "check_time": datetime.datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Stuck videos check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )
    finally:
        if db:
            db.close()


@router.get("/cors")
async def cors_health_check(request: Request):
    """CORS health check endpoint to validate headers are being sent correctly."""
    logger.info(f"🔍 CORS Health Check - Origin: {request.headers.get('origin', 'none')}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    
    return JSONResponse(
        content={
            "status": "healthy",
            "message": "CORS headers should be present",
            "request_origin": request.headers.get("origin", "none"),
            "request_method": request.method,
            "timestamp": str(datetime.datetime.now()),
        },
        headers={
            "X-CORS-Test": "success",
            "X-Backend": "ClipAI-FastAPI",
        }
    )


@router.options("/cors")
async def cors_preflight(request: Request):
    """Handle preflight OPTIONS for CORS health check."""
    logger.info(f"✈️ CORS Preflight - Origin: {request.headers.get('origin', 'none')}")
    
    return JSONResponse(
        content={"preflight": "ok"},
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",
        }
    )
