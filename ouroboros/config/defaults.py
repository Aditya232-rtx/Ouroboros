"""
ouroboros/config/defaults.py — Default configuration values.

Single source of truth for all default settings.
"""

import secrets

# ── Paths ──────────────────────────────────────────────────────────
OUROBOROS_HOME = "~/.ouroboros"
CONFIG_FILE = "config.yaml"
ENV_FILE = ".env"
LOGS_DIR = "logs"

# ── Docker ─────────────────────────────────────────────────────────
DOCKER_COMPOSE_PROJECT = "ouroboros"

# ── PostgreSQL ─────────────────────────────────────────────────────
POSTGRES_IMAGE = "postgres:15-alpine"
POSTGRES_HOST = "127.0.0.1"
POSTGRES_PORT = 5432
POSTGRES_DB = "ouroboros"
POSTGRES_USER = "ouroboros_user"

# ── Redis ──────────────────────────────────────────────────────────
REDIS_IMAGE = "redis:7-alpine"
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379

# ── immudb ─────────────────────────────────────────────────────────
IMMUDB_IMAGE = "codenotary/immudb:latest"
IMMUDB_HOST = "127.0.0.1"
IMMUDB_PORT = 3322
IMMUDB_USER = "immudb"
IMMUDB_PASSWORD = "immudb"
IMMUDB_DATABASE = "ouroboros_audit"

# ── OPA ────────────────────────────────────────────────────────────
OPA_IMAGE = "openpolicyagent/opa:latest"
OPA_HOST = "127.0.0.1"
OPA_PORT = 8181

# ── Ollama ─────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5-coder:3b"

# ── API ────────────────────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8000

# ── Full default config ───────────────────────────────────────────
def default_config() -> dict:
    """Return the full default config dict."""
    return {
        "version": "2.0.0",
        "github": {
            "token": "",
        },
        "ollama": {
            "url": OLLAMA_BASE_URL,
            "model": OLLAMA_MODEL,
        },
        "database": {
            "url": f"postgresql://{POSTGRES_USER}:changeme@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
        },
        "redis": {
            "url": f"redis://:{{}}" + f"@{REDIS_HOST}:{REDIS_PORT}/0",
        },
        "immudb": {
            "host": IMMUDB_HOST,
            "port": IMMUDB_PORT,
            "username": IMMUDB_USER,
            "password": IMMUDB_PASSWORD,
            "database": IMMUDB_DATABASE,
        },
        "opa": {
            "url": f"http://{OPA_HOST}:{OPA_PORT}",
        },
        "security": {
            "secret_key": "",
        },
        "docker": {
            "postgres_password": "",
            "redis_password": "",
        },
    }


def generate_secret(length: int = 48) -> str:
    """Generate a cryptographically secure random string."""
    return secrets.token_urlsafe(length)
