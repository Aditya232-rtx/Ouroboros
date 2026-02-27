"""
Ouroboros AI - FastAPI Application

Main API entry point with routes, middleware, and configuration.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import scan_router, status_router, reports_router, health_router, auth_router, research_router
from src.api.middleware import LoggingMiddleware, RateLimitMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Ouroboros AI",
    description="Autonomous AI-driven security vulnerability detection and remediation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ============ Middleware ============
# Order matters: LAST added = FIRST to handle request (LIFO)
# CORS must be added LAST so it processes requests FIRST (handles OPTIONS preflight)

# Custom middleware (added first = runs after CORS)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS middleware for frontend integration (added last = runs first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Routes ============
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(scan_router)
app.include_router(status_router)
app.include_router(reports_router)
app.include_router(research_router)


@app.on_event("startup")
async def startup_event():
    """Initialize resources on application startup."""
    logger.info("Ouroboros AI API starting up...")
    
    # Initialize database connection pool
    try:
        from src.database.session import init_db
        init_db()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")
    
    # Clean up incomplete scans from previous sessions
    try:
        from src.api.utils.startup import cleanup_incomplete_scans
        await cleanup_incomplete_scans()
    except Exception as e:
        logger.warning(f"Scan cleanup skipped: {e}")
    
    logger.info("Ouroboros AI API ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown."""
    logger.info("Ouroboros AI API shutting down...")
    
    # Shutdown scan executor gracefully
    try:
        from src.api.routes.scan import scan_executor
        scan_executor.shutdown(wait=False, cancel_futures=True)
        logger.info("Scan executor shutdown complete")
    except Exception as e:
        logger.warning(f"Scan executor shutdown skipped: {e}")
    
    # Close database connections (handled by SQLAlchemy engine pool)
    
    logger.info("Ouroboros AI API shutdown complete")


__all__ = ["app"]
