"""
ouroboros/config/ — Unified configuration management.

Handles:
  • ~/.ouroboros/config.yaml   (global user config)
  • .env generation
  • Credential management
"""

from .manager import ConfigManager, get_config

__all__ = ["ConfigManager", "get_config"]
