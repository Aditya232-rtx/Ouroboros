# src/api/middleware/auth.py
"""Authentication middleware for Ouroboros AI API."""

import logging
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import settings

logger = logging.getLogger(__name__)

# API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)) -> str:
    """
    Verify the API key from the request header.
    
    This is a FastAPI dependency that can be added to routes
    requiring authentication.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Validate against configured API keys
    valid_keys = settings.api_keys if hasattr(settings, "api_keys") else []
    
    if api_key not in valid_keys:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )
    
    return api_key


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce API key authentication on all endpoints.
    
    Skips authentication for:
    - Health check endpoints (/health, /ready, /live)
    - OpenAPI documentation (/docs, /redoc, /openapi.json)
    """
    
    SKIP_AUTH_PATHS = {
        "/health",
        "/ready",
        "/live",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for certain paths
        if request.url.path in self.SKIP_AUTH_PATHS:
            return await call_next(request)
        
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return self._unauthorized_response("Missing API key")
        
        # Validate key
        valid_keys = settings.api_keys if hasattr(settings, "api_keys") else []
        
        if api_key not in valid_keys:
            logger.warning(f"Invalid API key from {request.client.host}")
            return self._unauthorized_response("Invalid API key")
        
        # Store user info in request state
        request.state.api_key = api_key
        
        return await call_next(request)
    
    def _unauthorized_response(self, detail: str):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized", "detail": detail},
            headers={"WWW-Authenticate": "ApiKey"},
        )
