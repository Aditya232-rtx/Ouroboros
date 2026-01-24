"""
Ouroboros AI - FastAPI Application

Main API entry point with routes, middleware, and configuration.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import scan_router, status_router, reports_router, health_router
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
# Order matters: first added = outermost (runs first on request, last on response)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware (innermost to outermost)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Note: AuthMiddleware can be enabled for production
# Uncomment the following line to enable API key authentication:
# app.add_middleware(AuthMiddleware)

# ============ Routes ============
app.include_router(health_router)
app.include_router(scan_router)
app.include_router(status_router)
app.include_router(reports_router)


@app.on_event("startup")
async def startup_event():
    """Initialize resources on application startup."""
    logger.info("Ouroboros AI API starting up...")
    
    # Initialize database connection pool
    try:
        from src.database.connection import init_db
        await init_db()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")
    
    logger.info("Ouroboros AI API ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown."""
    logger.info("Ouroboros AI API shutting down...")
    
    # Close database connections
    try:
        from src.database.connection import close_db
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.warning(f"Database cleanup skipped: {e}")
    
    logger.info("Ouroboros AI API shutdown complete")


__all__ = ["app"]
