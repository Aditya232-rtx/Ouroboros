"""
ouroboros/doctor/ — Health check diagnostics.

``ouroboros doctor`` runs comprehensive checks on all services
and reports their status with actionable fix suggestions.
"""

from .checks import run_doctor

__all__ = ["run_doctor"]
