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
    # TEMPORARY: Increased for testing - reduce in production
    AUTHENTICATED_LIMIT: Tuple[int, int] = (1000, 60)  # 1000 req/min
    UNAUTHENTICATED_LIMIT: Tuple[int, int] = (1000, 60)  # 1000 req/min - Increased for dev
    
    def __init__(self, app):
        super().__init__(app)
        # Track requests: {identifier: [(timestamp, count)]}
        self._request_counts: Dict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Get identifier (API key or IP)
        identifier = request.headers.get("X-API-Key") or (request.client.host if request.client else "unknown_client")
        
        # Determine limit based on authentication
        if request.headers.get("X-API-Key"):
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
