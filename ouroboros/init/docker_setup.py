"""
ouroboros/init/docker_setup.py — Docker infrastructure management.

Brings up PostgreSQL, Redis, immudb, OPA via docker compose and waits
for all health checks to pass.
"""

import os
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional

import click

logger = logging.getLogger("ouroboros.init.docker_setup")

# The bundled compose file shipped with the SDK
_COMPOSE_FILE = Path(__file__).resolve().parent.parent.parent / "docker-compose.sdk.yml"
# Fallback: if running from cloned repo, use root compose
_COMPOSE_FALLBACK = Path(__file__).resolve().parent.parent.parent / "docker-compose.yml"


def get_compose_file() -> Path:
    """Return the best available compose file."""
    if _COMPOSE_FILE.exists():
        return _COMPOSE_FILE
    if _COMPOSE_FALLBACK.exists():
        return _COMPOSE_FALLBACK
    raise FileNotFoundError(
        "Cannot find docker-compose.sdk.yml or docker-compose.yml.\n"
        "Make sure you're running from the Ouroboros project directory."
    )


def get_compose_cmd(compose_file: Optional[Path] = None) -> list:
    """Return the docker compose base command."""
    cf = compose_file or get_compose_file()
    return ["docker", "compose", "-f", str(cf), "-p", "ouroboros"]


def docker_up(env: dict | None = None, compose_file: Optional[Path] = None) -> bool:
    """
    Pull images and start all infrastructure services.
    Returns True if successful.
    """
    cmd = get_compose_cmd(compose_file)
    full_env = {**os.environ, **(env or {})}

    click.echo()
    click.secho("🐳 Starting Docker infrastructure …", fg="cyan", bold=True)

    # Pull images first
    click.echo("   Pulling container images …")
    try:
        subprocess.run(
            [*cmd, "pull"],
            env=full_env, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        click.secho(f"   ⚠️  Pull warning: {e.stderr.decode()[:200]}", fg="yellow")

    # Start services
    click.echo("   Starting services …")
    try:
        subprocess.run(
            [*cmd, "up", "-d", "--wait"],
            env=full_env, check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        # --wait may not be supported on older compose; fall back
        try:
            subprocess.run(
                [*cmd, "up", "-d"],
                env=full_env, check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            click.secho(f"   ❌ Docker compose up failed: {e.stderr.decode()[:300]}", fg="red")
            return False

    return True


def docker_down(compose_file: Optional[Path] = None) -> bool:
    """Stop all infrastructure services."""
    cmd = get_compose_cmd(compose_file)
    try:
        subprocess.run([*cmd, "down"], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        click.secho(f"❌ docker compose down failed: {e.stderr.decode()[:200]}", fg="red")
        return False


def wait_for_services(timeout: int = 90) -> dict:
    """
    Wait for all 4 infrastructure services to become healthy.
    Returns a dict of ``{service_name: (ok, detail)}``.
    """
    click.echo("   Waiting for services to be ready …")
    start = time.time()
    results = {}

    checks = [
        ("PostgreSQL", _check_postgres),
        ("Redis", _check_redis),
        ("immudb", _check_immudb),
        ("OPA", _check_opa),
    ]

    for name, fn in checks:
        ok = False
        detail = ""
        while time.time() - start < timeout:
            ok, detail = fn()
            if ok:
                break
            time.sleep(2)
        results[name] = (ok, detail)
        status = "✅" if ok else "❌"
        click.echo(f"   {status} {name}: {detail}")

    return results


def _check_postgres() -> tuple:
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost", port=5432,
            user="ouroboros_user",
            password=os.environ.get("POSTGRES_PASSWORD", "changeme"),
            dbname="ouroboros",
            connect_timeout=3,
        )
        conn.close()
        return True, "connected"
    except Exception as e:
        return False, str(e)[:80]


def _check_redis() -> tuple:
    try:
        import redis
        pw = os.environ.get("REDIS_PASSWORD", "changeme")
        r = redis.Redis(host="localhost", port=6379, password=pw, socket_timeout=3)
        r.ping()
        return True, "PONG"
    except Exception as e:
        return False, str(e)[:80]


def _check_immudb() -> tuple:
    try:
        from immudb import ImmudbClient
        client = ImmudbClient(immudUrl="localhost:3322")
        client.login("immudb", "immudb")
        client.logout()
        return True, "authenticated"
    except Exception as e:
        return False, str(e)[:80]


def _check_opa() -> tuple:
    try:
        import urllib.request
        req = urllib.request.urlopen("http://localhost:8181/health", timeout=3)
        return True, "healthy"
    except Exception as e:
        return False, str(e)[:80]


def init_databases() -> None:
    """Create the immudb audit database if it doesn't exist."""
    click.echo("   Initializing databases …")
    try:
        from immudb import ImmudbClient
        client = ImmudbClient(immudUrl="localhost:3322")
        client.login("immudb", "immudb")
        try:
            client.createDatabase("ouroboros_audit")
            click.echo("   ✅ immudb: ouroboros_audit database created")
        except Exception:
            click.echo("   ✅ immudb: ouroboros_audit database exists")
        client.logout()
    except Exception as e:
        click.secho(f"   ⚠️  immudb init skipped: {e}", fg="yellow")

    # PostgreSQL tables are auto-created by SQLAlchemy on first API start
    click.echo("   ✅ PostgreSQL: schema created on first API start")
