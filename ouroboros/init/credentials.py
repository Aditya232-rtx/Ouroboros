"""
ouroboros/init/credentials.py — Interactive credential collection.

Prompts the user for required secrets and auto-generates passwords.
"""

import click
import logging
from typing import Dict, Any

from ouroboros.config.defaults import generate_secret

logger = logging.getLogger("ouroboros.init.credentials")


def collect_credentials(existing: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Interactively collect credentials from the user.

    Returns a config dict ready to merge into ConfigManager.
    """
    existing = existing or {}

    click.echo()
    click.secho("🔑 Credential Setup", fg="cyan", bold=True)
    click.echo("   We need a few things to get started.\n")

    # ── GitHub Token (required) ───────────────────────────────────
    current_token = existing.get("github", {}).get("token", "")
    if current_token:
        masked = current_token[:4] + "…" + current_token[-4:]
        click.echo(f"   Current GitHub token: {masked}")
        reuse = click.confirm("   Keep existing token?", default=True)
        if reuse:
            github_token = current_token
        else:
            github_token = _prompt_github_token()
    else:
        github_token = _prompt_github_token()

    # ── Auto-generate service passwords ───────────────────────────
    postgres_pw = existing.get("docker", {}).get("postgres_password") or generate_secret(24)
    redis_pw = existing.get("docker", {}).get("redis_password") or generate_secret(24)
    secret_key = existing.get("security", {}).get("secret_key") or generate_secret(48)

    click.echo()
    click.secho("   ✅ Service passwords auto-generated", fg="green")

    # ── Ollama URL ────────────────────────────────────────────────
    default_ollama = existing.get("ollama", {}).get("url", "http://localhost:11434")
    ollama_url = click.prompt(
        "   Ollama server URL",
        default=default_ollama,
        show_default=True,
    )

    return {
        "version": "2.0.0",
        "github": {"token": github_token},
        "ollama": {
            "url": ollama_url,
            "model": "qwen2.5-coder:3b",
        },
        "database": {
            "url": f"postgresql://ouroboros_user:{postgres_pw}@localhost:5432/ouroboros",
        },
        "redis": {
            "url": f"redis://:{redis_pw}@localhost:6379/0",
        },
        "immudb": {
            "host": "localhost",
            "port": 3322,
            "username": "immudb",
            "password": "immudb",
            "database": "ouroboros_audit",
        },
        "opa": {
            "url": "http://localhost:8181",
        },
        "security": {
            "secret_key": secret_key,
        },
        "docker": {
            "postgres_password": postgres_pw,
            "redis_password": redis_pw,
        },
    }


def _prompt_github_token() -> str:
    """Prompt for GitHub token with validation."""
    while True:
        token = click.prompt(
            "   GitHub Personal Access Token",
            hide_input=True,
        )
        token = token.strip()
        if token.startswith(("ghp_", "github_pat_", "gho_", "ghu_", "ghs_")):
            return token
        if len(token) > 20:
            # Probably valid even if prefix doesn't match
            click.secho("   ⚠️  Token doesn't have a standard prefix, but accepting it.", fg="yellow")
            return token
        click.secho("   ❌ Token looks too short. Get one at: https://github.com/settings/tokens", fg="red")
