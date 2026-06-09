# src/api/routes/health.py
"""Health check endpoint for Ouroboros AI."""

import logging
import time
from datetime import datetime
from fastapi import APIRouter

from src.api.schemas import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

# Track startup time
_startup_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of the Ouroboros AI service.",
)
async def health_check() -> HealthResponse:
    """Return health status of all components."""
    components = {}
    
    # Check database connection
    try:
        from src.database.connection import get_db_session
        async with get_db_session() as session:
            await session.execute("SELECT 1")
        components["database"] = "healthy"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        components["database"] = "unhealthy"
    
    # Check Redis (if configured)
    try:
        from config.settings import settings
        if settings.redis_url:
            import aioredis
            redis = aioredis.from_url(settings.redis_url)
            await redis.ping()
            components["redis"] = "healthy"
            await redis.close()
        else:
            components["redis"] = "not_configured"
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
    
    # Check security tools availability
    import shutil
    tools_status = []
    for tool in ["semgrep", "checkov", "nuclei", "codeql"]:
        if shutil.which(tool):
            tools_status.append(tool)
    
    if len(tools_status) == 4:
        components["security_tools"] = "all_available"
    elif len(tools_status) > 0:
        components["security_tools"] = f"partial ({', '.join(tools_status)})"
    else:
        components["security_tools"] = "none_available"
    
    # Determine overall status
    critical_components = ["database", "docker"]
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
async def readiness_probe():
    """Simple readiness check for Kubernetes."""
    return {"ready": True}


@router.get(
    "/live",
    summary="Liveness probe",
    description="Kubernetes liveness probe endpoint.",
)
async def liveness_probe():
    """Simple liveness check for Kubernetes."""
    return {"alive": True}
