"""
Ouroboros SDK v1.0.0
Production Security Automation Platform

Input  → any GitHub repository URL
Output → vulnerability report + patched GitHub PR + PDF security docs
"""
__version__ = "1.0.0"

from .core import Ouroboros
from .cli import cli

__all__ = ["Ouroboros", "cli"]
