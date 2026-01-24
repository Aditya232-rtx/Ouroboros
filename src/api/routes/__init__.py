# src/api/routes/__init__.py
"""API route modules for Ouroboros AI."""

from src.api.routes.scan import router as scan_router
from src.api.routes.status import router as status_router
from src.api.routes.reports import router as reports_router
from src.api.routes.health import router as health_router

__all__ = [
    "scan_router",
    "status_router",
    "reports_router",
    "health_router",
]
