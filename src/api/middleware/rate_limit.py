# src/api/middleware/rate_limit.py
"""Rate limiting middleware for Ouroboros AI API."""

import logging
import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    
    For production, use Redis-based rate limiting for distributed
    deployments.
    
    Limits:
    - 100 requests per minute per API key
    - 10 requests per minute for unauthenticated requests
    """
    
    # Rate limits: (requests, window_seconds)
    AUTHENTICATED_LIMIT: Tuple[int, int] = (100, 60)  # 100 req/min
    UNAUTHENTICATED_LIMIT: Tuple[int, int] = (20, 60)  # 20 req/min
    
    def __init__(self, app):
        super().__init__(app)
        # Track requests: {identifier: [(timestamp, count)]}
        self._request_counts: Dict[str, list] = defaultdict(list)
    
    # Paths exempt from rate limiting (read-only monitoring endpoints)
    EXEMPT_PREFIXES = ("/status/", "/health", "/ready", "/live")
    
    async def dispatch(self, request: Request, call_next):
        # Exempt monitoring/polling endpoints from rate limiting
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return await call_next(request)
        
        # Get identifier (API key or IP)
        identifier = request.headers.get("X-API-Key") or (request.client.host if request.client else "unknown_client")
        
        # Determine limit based on authentication
        # Check both API key and cookie-based auth
        has_api_key = bool(request.headers.get("X-API-Key"))
        has_cookie_auth = bool(request.cookies.get("access_token"))
        
        if has_api_key or has_cookie_auth:
            max_requests, window = self.AUTHENTICATED_LIMIT
        else:
            max_requests, window = self.UNAUTHENTICATED_LIMIT
        
        # Check rate limit
        if self._is_rate_limited(identifier, max_requests, window):
            logger.warning(f"Rate limit exceeded for {identifier}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": f"Rate limit exceeded. Max {max_requests} requests per {window} seconds.",
                    "retry_after": window,
                },
                headers={"Retry-After": str(window)},
            )
        
        # Record this request
        self._record_request(identifier)
        
        return await call_next(request)
    
    def _is_rate_limited(
        self, identifier: str, max_requests: int, window: int
    ) -> bool:
        """Check if identifier has exceeded rate limit."""
        now = time.time()
        cutoff = now - window
        
        # Clean old entries and count recent requests
        recent_requests = [
            ts for ts in self._request_counts[identifier]
            if ts > cutoff
        ]
        self._request_counts[identifier] = recent_requests
        
        return len(recent_requests) >= max_requests
    
    def _record_request(self, identifier: str):
        """Record a request for rate limiting."""
        self._request_counts[identifier].append(time.time())
        
        # Periodic cleanup: if more than 1000 identifiers tracked, prune stale
        if len(self._request_counts) > 1000:
            now = time.time()
            stale = [k for k, v in self._request_counts.items() if not v or v[-1] < now - 120]
            for k in stale:
                del self._request_counts[k]
