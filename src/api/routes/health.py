# src/api/routes/health.py
"""Health check endpoint for Ouroboros AI."""

import logging
import shutil
import time
from datetime import datetime
from fastapi import APIRouter
from sqlalchemy import text

from src.api.schemas import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

# Track startup time
_startup_time = time.time()

# Cache security tool availability (doesn't change at runtime)
_tools_cache: dict = {}
_tools_cache_time: float = 0


def _check_tools() -> str:
    """Check security tool availability (cached for 5 minutes)."""
    global _tools_cache, _tools_cache_time
    now = time.time()
    if now - _tools_cache_time < 300:  # 5 min cache
        return _tools_cache.get("result", "unknown")
    
    tools_status = []
    for tool in ["semgrep", "checkov", "nuclei", "codeql"]:
        if shutil.which(tool):
            tools_status.append(tool)
    
    if len(tools_status) == 4:
        result = "all_available"
    elif len(tools_status) > 0:
        result = f"partial ({', '.join(tools_status)})"
    else:
        result = "none_available"
    
    _tools_cache = {"result": result}
    _tools_cache_time = now
    return result


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of the Ouroboros AI service.",
)
async def health_check() -> HealthResponse:
    """Return health status of all components."""
    components = {}
    
    # Check database connection using existing session factory
    try:
        from src.database.session import SessionLocal
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            components["database"] = "healthy"
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        components["database"] = "unhealthy"
    
    # Check Redis
    try:
        from src.database.redis import get_redis_client
        client = get_redis_client()
        client.ping()
        components["redis"] = "healthy"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        components["redis"] = "unhealthy"
    
    # Check Docker (for sandbox)
    try:
        import docker
        client = docker.from_env()
        client.ping()
        components["docker"] = "healthy"
    except Exception as e:
        logger.warning(f"Docker health check failed: {e}")
        components["docker"] = "unhealthy"
    
    # Check security tools (cached)
    components["security_tools"] = _check_tools()
    
    # Determine overall status
    critical_components = ["database"]
    overall_healthy = all(
        components.get(c) == "healthy" for c in critical_components
    )
    
    return HealthResponse(
        status="healthy" if overall_healthy else "degraded",
        version="1.0.0",
        uptime_seconds=time.time() - _startup_time,
        components=components,
    )


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Kubernetes readiness probe endpoint.",
)
async def readiness_probe() -> dict:
    """Simple readiness check for Kubernetes."""
    return {"ready": True}


@router.get(
    "/live",
    summary="Liveness probe",
    description="Kubernetes liveness probe endpoint.",
)
async def liveness_probe() -> dict:
    """Simple liveness check for Kubernetes."""
    return {"alive": True}
