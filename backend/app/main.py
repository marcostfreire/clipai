"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import logging
import os

from .config import settings
from .database import init_db
from .api import videos, clips, health, auth, subscriptions, webhooks

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ClipAI API",
    description="AI-powered video clipping service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS headers to all responses FIRST (workaround for proxy stripping headers)
@app.middleware("http")
async def add_cors_headers(request, call_next):
    """Add CORS headers to all responses - must be first middleware."""
    # Handle OPTIONS request
    if request.method == "OPTIONS":
        response = JSONResponse(content={})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "600"
        return response
    
    # Process request and add CORS headers to response
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Max-Age"] = "600"
    return response

# Session middleware (required for OAuth)
app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting ClipAI API...")

    # Create storage directory
    os.makedirs(settings.storage_path, exist_ok=True)
    logger.info(f"Storage path: {settings.storage_path}")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    logger.info("ClipAI API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down ClipAI API...")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to ClipAI API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ClipAI API"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "type": type(exc).__name__,
            },
        )
    else:
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


# Include routers
app.include_router(health.router)
app.include_router(webhooks.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(videos.router, prefix="/api")
app.include_router(clips.router, prefix="/api")
app.include_router(clips.clips_router, prefix="/api")
app.include_router(subscriptions.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
