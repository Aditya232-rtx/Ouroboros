"""
ouroboros/init/verify.py — Post-setup verification.

Runs a comprehensive health check to confirm everything is ready.
"""

import click
import logging

logger = logging.getLogger("ouroboros.init.verify")


def run_verification() -> bool:
    """
    Verify all components are operational after ``ouroboros init``.
    Returns True if everything passes.
    """
    click.echo()
    click.secho("🔍 Verifying setup …", fg="cyan", bold=True)

    results = []

    # 1. Docker containers
    results.append(_verify_containers())

    # 2. PostgreSQL
    results.append(_verify_postgres())

    # 3. Redis
    results.append(_verify_redis())

    # 4. immudb
    results.append(_verify_immudb())

    # 5. OPA
    results.append(_verify_opa())

    # 6. Ollama
    results.append(_verify_ollama())

    # 7. SDK import
    results.append(_verify_sdk_import())

    all_ok = all(results)
    click.echo()
    if all_ok:
        click.secho("✅ All checks passed — Ouroboros is ready!", fg="green", bold=True)
        click.echo()
        click.secho("   Next steps:", fg="white", bold=True)
        click.echo("   ouroboros scan --repo https://github.com/owner/repo")
        click.echo("   ouroboros doctor          # check health anytime")
        click.echo("   ouroboros dashboard       # start the web UI")
        click.echo()
    else:
        click.secho("⚠️  Some checks failed — see above for details.", fg="yellow", bold=True)
        click.echo("   Run: ouroboros doctor    for detailed diagnostics")
        click.echo()

    return all_ok


def _verify_containers() -> bool:
    import subprocess
    try:
        out = subprocess.check_output(
            ["docker", "compose", "-p", "ouroboros", "ps", "--format", "json"],
            text=True, stderr=subprocess.DEVNULL,
        )
        running = out.count('"running"') + out.count('"Running"')
        if running >= 4:
            click.echo(f"   ✅ Docker: {running} containers running")
            return True
        else:
            click.echo(f"   ⚠️  Docker: only {running}/4 containers running")
            return running > 0
    except Exception:
        # Fallback: check individual containers
        try:
            out = subprocess.check_output(
                ["docker", "ps", "--filter", "name=ouroboros-", "--format", "{{.Names}}"],
                text=True,
            )
            count = len([l for l in out.strip().splitlines() if l.strip()])
            click.echo(f"   ✅ Docker: {count} ouroboros containers running")
            return count >= 3
        except Exception:
            click.secho("   ❌ Docker: cannot list containers", fg="red")
            return False


def _verify_postgres() -> bool:
    try:
        import psycopg2
        import os
        conn = psycopg2.connect(
            host="localhost", port=5432,
            user="ouroboros_user",
            password=os.environ.get("POSTGRES_PASSWORD", "changeme"),
            dbname="ouroboros",
            connect_timeout=5,
        )
        conn.close()
        click.echo("   ✅ PostgreSQL: connected")
        return True
    except Exception as e:
        click.secho(f"   ❌ PostgreSQL: {e}", fg="red")
        return False


def _verify_redis() -> bool:
    try:
        import redis, os
        pw = os.environ.get("REDIS_PASSWORD", "changeme")
        r = redis.Redis(host="localhost", port=6379, password=pw, socket_timeout=5)
        r.ping()
        click.echo("   ✅ Redis: PONG")
        return True
    except Exception as e:
        click.secho(f"   ❌ Redis: {e}", fg="red")
        return False


def _verify_immudb() -> bool:
    try:
        from immudb import ImmudbClient
        client = ImmudbClient(immudUrl="localhost:3322")
        client.login("immudb", "immudb")
        client.logout()
        click.echo("   ✅ immudb: authenticated")
        return True
    except Exception as e:
        click.secho(f"   ❌ immudb: {e}", fg="red")
        return False


def _verify_opa() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:8181/health", timeout=5)
        click.echo("   ✅ OPA: healthy")
        return True
    except Exception as e:
        click.secho(f"   ❌ OPA: {e}", fg="red")
        return False


def _verify_ollama() -> bool:
    try:
        import urllib.request, json
        resp = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        data = json.loads(resp.read())
        models = [m.get("name", "") for m in data.get("models", [])]
        has_model = any("qwen2.5-coder" in m for m in models)
        if has_model:
            click.echo("   ✅ Ollama: qwen2.5-coder:3b available")
            return True
        else:
            click.secho(f"   ⚠️  Ollama running but qwen2.5-coder:3b not found (models: {models})", fg="yellow")
            return False
    except Exception as e:
        click.secho(f"   ❌ Ollama: {e}", fg="red")
        return False


def _verify_sdk_import() -> bool:
    try:
        import ouroboros
        click.echo(f"   ✅ SDK: v{ouroboros.__version__}")
        return True
    except Exception as e:
        click.secho(f"   ❌ SDK import: {e}", fg="red")
        return False
