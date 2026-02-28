"""
ouroboros/config/manager.py — Read/write ~/.ouroboros/config.yaml + .env.

Unified config layer that both the CLI and the SDK core use.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .defaults import (
    OUROBOROS_HOME,
    CONFIG_FILE,
    ENV_FILE,
    default_config,
    generate_secret,
)

logger = logging.getLogger("ouroboros.config")

_cached_manager: Optional["ConfigManager"] = None


def get_ouroboros_home() -> Path:
    """Return the resolved ~/.ouroboros directory."""
    return Path(os.environ.get("OUROBOROS_HOME", OUROBOROS_HOME)).expanduser()


class ConfigManager:
    """
    Central config manager for the Ouroboros SDK.

    Reads from ``~/.ouroboros/config.yaml`` and can generate a ``.env`` file
    that the Pydantic ``Settings`` class consumes.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.home = get_ouroboros_home()
        self.config_path = Path(config_path) if config_path else self.home / CONFIG_FILE
        self.env_path = self.home / ENV_FILE
        self._data: Dict[str, Any] = {}
        self._load()

    # ── Public API ────────────────────────────────────────────────

    @property
    def data(self) -> Dict[str, Any]:
        return self._data

    def get(self, *keys: str, default: Any = None) -> Any:
        """Nested key lookup: ``cfg.get("ollama", "model")``."""
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
            if val is None:
                return default
        return val

    def set(self, *keys_and_value: Any) -> None:
        """
        Nested key set: ``cfg.set("ollama", "model", "qwen2.5-coder:3b")``.
        The last argument is the value, everything before it is the key path.
        """
        *keys, value = keys_and_value
        d = self._data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    def save(self) -> None:
        """Persist config to disk."""
        self.home.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as fh:
            yaml.dump(self._data, fh, default_flow_style=False, sort_keys=False)
        logger.info("Config saved → %s", self.config_path)

    def exists(self) -> bool:
        """Return True if config file exists on disk."""
        return self.config_path.exists()

    # ── .env Generation ───────────────────────────────────────────

    def generate_env(self, project_dir: Optional[Path] = None) -> Path:
        """
        Write a ``.env`` file from the current config.
        If *project_dir* is given, also writes a copy there.
        Returns the primary .env path.
        """
        lines = self._build_env_lines()
        content = "\n".join(lines) + "\n"

        # Always write to ~/.ouroboros/.env
        self.home.mkdir(parents=True, exist_ok=True)
        self.env_path.write_text(content)
        logger.info(".env written → %s", self.env_path)

        # Optionally copy to project directory
        if project_dir:
            project_env = Path(project_dir) / ".env"
            project_env.write_text(content)
            logger.info(".env copied  → %s", project_env)

        return self.env_path

    def apply_to_environment(self) -> None:
        """
        Push config values into ``os.environ`` so Pydantic Settings picks
        them up.  Idempotent — won't overwrite values already in env.
        """
        env_map = {
            ("github", "token"): "GITHUB_TOKEN",
            ("ollama", "url"): "OLLAMA_BASE_URL",
            ("ollama", "model"): "OLLAMA_MODEL",
            ("database", "url"): "DATABASE_URL",
            ("redis", "url"): "REDIS_URL",
            ("immudb", "host"): "IMMUDB_HOST",
            ("immudb", "port"): "IMMUDB_PORT",
            ("immudb", "username"): "IMMUDB_USERNAME",
            ("immudb", "password"): "IMMUDB_PASSWORD",
            ("immudb", "database"): "IMMUDB_DATABASE",
            ("opa", "url"): "OPA_URL",
            ("security", "secret_key"): "SECRET_KEY",
        }
        for keys, env_var in env_map.items():
            val = self.get(*keys)
            if val is not None:
                os.environ.setdefault(env_var, str(val))

    # ── Internals ─────────────────────────────────────────────────

    def _load(self) -> None:
        if self.config_path.exists():
            with open(self.config_path) as fh:
                self._data = yaml.safe_load(fh) or {}
        else:
            self._data = default_config()

    def _build_env_lines(self) -> list:
        """Map config dict → .env key=value lines."""
        d = self._data
        postgres_pw = d.get("docker", {}).get("postgres_password", "changeme")
        redis_pw = d.get("docker", {}).get("redis_password", "changeme")
        secret = d.get("security", {}).get("secret_key", generate_secret())

        return [
            "# Ouroboros AI — auto-generated .env",
            "# Do not edit manually; use: ouroboros config set <key> <value>",
            "",
            "# Application",
            "APP_ENV=development",
            "DEBUG=false",
            "",
            "# Database",
            f"DATABASE_URL=postgresql://ouroboros_user:{postgres_pw}@localhost:5432/ouroboros",
            "",
            "# Redis",
            f"REDIS_URL=redis://:{redis_pw}@localhost:6379/0",
            "",
            "# immudb",
            f"IMMUDB_HOST={d.get('immudb', {}).get('host', 'localhost')}",
            f"IMMUDB_PORT={d.get('immudb', {}).get('port', 3322)}",
            f"IMMUDB_USERNAME={d.get('immudb', {}).get('username', 'immudb')}",
            f"IMMUDB_PASSWORD={d.get('immudb', {}).get('password', 'immudb')}",
            f"IMMUDB_DATABASE={d.get('immudb', {}).get('database', 'ouroboros_audit')}",
            "",
            "# OPA",
            f"OPA_URL={d.get('opa', {}).get('url', 'http://localhost:8181')}",
            "",
            "# GitHub",
            f"GITHUB_TOKEN={d.get('github', {}).get('token', '')}",
            "",
            "# Ollama",
            f"OLLAMA_BASE_URL={d.get('ollama', {}).get('url', 'http://localhost:11434')}",
            f"OLLAMA_MODEL={d.get('ollama', {}).get('model', 'qwen2.5-coder:3b')}",
            "",
            "# Security",
            f"SECRET_KEY={secret}",
            "",
            "# Docker service passwords",
            f"POSTGRES_PASSWORD={postgres_pw}",
            f"REDIS_PASSWORD={redis_pw}",
        ]


def get_config(config_path: Optional[str] = None) -> ConfigManager:
    """Return a cached ConfigManager singleton."""
    global _cached_manager
    if _cached_manager is None or config_path is not None:
        _cached_manager = ConfigManager(config_path)
    return _cached_manager
