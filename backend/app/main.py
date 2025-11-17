"""Main FastAPI application."""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os
import time

from .config import settings
from .database import init_db
from .api import videos, clips, health, auth, subscriptions, webhooks

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,  # Force DEBUG to see all headers
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
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

# AGGRESSIVE CORS BYPASS STRATEGY - LAYER 1: Log ALL requests
class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        logger.info(f"🔵 Incoming {request.method} {request.url.path}")
        logger.debug(f"Headers: {dict(request.headers)}")
        logger.debug(f"Client: {request.client}")
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(f"🟢 Response {response.status_code} for {request.method} {request.url.path} ({process_time:.3f}s)")
        logger.debug(f"Response Headers: {dict(response.headers)}")
        
        return response

# AGGRESSIVE CORS BYPASS STRATEGY - LAYER 2: Nuclear CORS headers
class AggressiveCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """Ultra-aggressive CORS middleware that forces headers on EVERY response."""
        
        # Get origin - use wildcard if not present
        origin = request.headers.get("origin", "*")
        
        # Handle preflight OPTIONS requests immediately
        if request.method == "OPTIONS":
            logger.warning(f"⚠️ PREFLIGHT OPTIONS detected for {request.url.path} from origin: {origin}")
            
            # Create response with explicit headers
            response = Response(
                status_code=200,
                content=b"",
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Expose-Headers": "*",
                    "Access-Control-Max-Age": "86400",
                    "Vary": "Origin",
                    "X-Content-Type-Options": "nosniff",
                }
            )
            
            logger.info(f"✅ PREFLIGHT response headers: {dict(response.headers)}")
            return response
        
        # Process the actual request
        response = await call_next(request)
        
        # NUCLEAR OPTION: Recreate response with CORS headers baked in
        # This ensures headers are present even if Cloudflare strips them
        from starlette.responses import Response as StarletteResponse
        
        # Get response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        # Create new response with forced headers
        new_response = StarletteResponse(
            content=body,
            status_code=response.status_code,
            headers={
                **dict(response.headers),
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Expose-Headers": "*",
                "Vary": "Origin",
            },
            media_type=response.headers.get("content-type"),
        )
        
        # Anti-caching for auth endpoints
        if "/auth/" in request.url.path:
            new_response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            new_response.headers["Pragma"] = "no-cache"
            new_response.headers["Expires"] = "0"
        
        logger.debug(f"🔧 Forced CORS headers on response for {request.url.path}")
        
        return new_response

# AGGRESSIVE CORS BYPASS STRATEGY - LAYER 3: Cloudflare-specific headers
class CloudflareBypassMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """Add headers specifically to bypass Cloudflare filtering."""
        response = await call_next(request)
        
        # Tell Cloudflare to preserve headers
        response.headers["CF-Cache-Status"] = "DYNAMIC"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        
        # Force content type
        if "application/json" in str(response.headers.get("content-type", "")):
            response.headers["Content-Type"] = "application/json; charset=utf-8"
        
        return response

# Apply middlewares in strategic order
app.add_middleware(RequestLoggerMiddleware)
app.add_middleware(AggressiveCORSMiddleware)
app.add_middleware(CloudflareBypassMiddleware)

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
