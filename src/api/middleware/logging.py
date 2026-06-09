# src/api/middleware/logging.py
"""Request/response logging middleware for Ouroboros AI API."""

import logging
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all incoming requests and outgoing responses.
    
    Logs:
    - Request ID (generated or from X-Request-ID header)
    - Method and path
    - Client IP
    - Response status code
    - Request duration
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate or use existing request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Store in request state for use in handlers
        request.state.request_id = request_id
        
        # Log incoming request
        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {client_ip}"
        )
        
        # Time the request
        start_time = time.time()
        
        try:
            response = await call_next(request)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"EXCEPTION after {duration:.3f}s: {e}"
            )
            raise
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"-> {response.status_code} ({duration:.3f}s)"
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
