"""
ouroboros/doctor/checks.py — Comprehensive health diagnostics.

Checks every component and prints actionable remediation steps.
"""

import os
import shutil
import subprocess
import sys
import json
import logging
from pathlib import Path
from typing import List, Tuple

import click

from ouroboros.config.manager import ConfigManager

logger = logging.getLogger("ouroboros.doctor")


class Check:
    """Single health check result."""

    def __init__(self, name: str, ok: bool, detail: str, fix: str = ""):
        self.name = name
        self.ok = ok
        self.detail = detail
        self.fix = fix


def run_doctor(verbose: bool = False) -> bool:
    """
    Run all health checks and print a diagnostic report.
    Returns True if all critical checks pass.
    """
    click.echo()
    click.secho("🩺 Ouroboros Doctor", fg="cyan", bold=True)
    click.echo("   Running comprehensive health checks …\n")

    checks: List[Check] = []

    # ── System ────────────────────────────────────────────────────
    click.secho("   System", fg="white", bold=True)
    checks.append(_check_python())
    checks.append(_check_git())
    checks.append(_check_docker())
    checks.append(_check_ollama())
    _print_checks(checks[-4:])

    # ── Config ────────────────────────────────────────────────────
    click.secho("\n   Configuration", fg="white", bold=True)
    checks.append(_check_config())
    checks.append(_check_github_token())
    _print_checks(checks[-2:])

    # ── Infrastructure ────────────────────────────────────────────
    click.secho("\n   Infrastructure", fg="white", bold=True)
    checks.append(_check_postgres())
    checks.append(_check_redis())
    checks.append(_check_immudb())
    checks.append(_check_opa())
    _print_checks(checks[-4:])

    # ── LLM ───────────────────────────────────────────────────────
    click.secho("\n   LLM Model", fg="white", bold=True)
    checks.append(_check_ollama_model())
    _print_checks(checks[-1:])

    # ── SDK ───────────────────────────────────────────────────────
    click.secho("\n   SDK", fg="white", bold=True)
    checks.append(_check_sdk_packages())
    _print_checks(checks[-1:])

    # ── Summary ───────────────────────────────────────────────────
    passed = sum(1 for c in checks if c.ok)
    total = len(checks)
    failed = [c for c in checks if not c.ok]

    click.echo()
    if not failed:
        click.secho(f"   ✅ All {total} checks passed", fg="green", bold=True)
    else:
        click.secho(f"   {passed}/{total} checks passed, {len(failed)} failed", fg="yellow", bold=True)
        click.echo()
        click.secho("   Fixes:", fg="white", bold=True)
        for c in failed:
            if c.fix:
                click.echo(f"   • {c.name}: {c.fix}")

    click.echo()
    return len(failed) == 0


def _print_checks(checks: List[Check]):
    for c in checks:
        icon = "✅" if c.ok else "❌"
        click.echo(f"     {icon} {c.name}: {c.detail}")


# ── Individual checks ─────────────────────────────────────────────

def _check_python() -> Check:
    v = sys.version_info
    ok = v >= (3, 11)
    return Check("Python", ok, f"{v.major}.{v.minor}.{v.micro}",
                  "Install Python 3.11+: https://python.org")


def _check_git() -> Check:
    if shutil.which("git"):
        return Check("Git", True, "installed")
    return Check("Git", False, "not found", "Install git: https://git-scm.com")


def _check_docker() -> Check:
    if not shutil.which("docker"):
        return Check("Docker", False, "not found",
                      "Install Docker Desktop: https://docker.com/get-started")
    try:
        out = subprocess.check_output(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return Check("Docker", True, f"v{out}")
    except Exception:
        return Check("Docker", False, "daemon not running",
                      "Start Docker Desktop")


def _check_ollama() -> Check:
    if not shutil.which("ollama"):
        return Check("Ollama", False, "not found",
                      "Install: curl -fsSL https://ollama.com/install.sh | sh")
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        return Check("Ollama", True, "running")
    except Exception:
        return Check("Ollama", False, "not running",
                      "Start Ollama: ollama serve")


def _check_config() -> Check:
    cfg = ConfigManager()
    if cfg.exists():
        return Check("Config", True, str(cfg.config_path))
    return Check("Config", False, "not found",
                  "Run: ouroboros init")


def _check_github_token() -> Check:
    cfg = ConfigManager()
    token = cfg.get("github", "token") or os.environ.get("GITHUB_TOKEN", "")
    if token and len(token) > 10:
        masked = token[:4] + "…" + token[-4:]
        return Check("GitHub Token", True, masked)
    return Check("GitHub Token", False, "not set",
                  "Run: ouroboros config set github.token <your-token>")


def _check_postgres() -> Check:
    try:
        import psycopg2
        pw = os.environ.get("POSTGRES_PASSWORD", "changeme")
        conn = psycopg2.connect(
            host="localhost", port=5432, user="ouroboros_user",
            password=pw, dbname="ouroboros", connect_timeout=3,
        )
        conn.close()
        return Check("PostgreSQL", True, "localhost:5432")
    except Exception as e:
        return Check("PostgreSQL", False, str(e)[:60],
                      "Run: ouroboros up")


def _check_redis() -> Check:
    try:
        import redis
        pw = os.environ.get("REDIS_PASSWORD", "changeme")
        r = redis.Redis(host="localhost", port=6379, password=pw, socket_timeout=3)
        r.ping()
        return Check("Redis", True, "localhost:6379")
    except Exception as e:
        return Check("Redis", False, str(e)[:60],
                      "Run: ouroboros up")


def _check_immudb() -> Check:
    try:
        from immudb import ImmudbClient
        client = ImmudbClient(immudUrl="localhost:3322")
        client.login("immudb", "immudb")
        client.logout()
        return Check("immudb", True, "localhost:3322")
    except Exception as e:
        return Check("immudb", False, str(e)[:60],
                      "Run: ouroboros up")


def _check_opa() -> Check:
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:8181/health", timeout=3)
        return Check("OPA", True, "localhost:8181")
    except Exception as e:
        return Check("OPA", False, str(e)[:60],
                      "Run: ouroboros up")


def _check_ollama_model() -> Check:
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        data = json.loads(resp.read())
        models = [m.get("name", "") for m in data.get("models", [])]
        has_model = any("qwen2.5-coder" in m for m in models)
        if has_model:
            return Check("qwen2.5-coder:3b", True, "available")
        return Check("qwen2.5-coder:3b", False,
                      f"not found (have: {', '.join(models[:3])})",
                      "Run: ouroboros models pull")
    except Exception:
        return Check("qwen2.5-coder:3b", False, "Ollama not reachable",
                      "Start Ollama: ollama serve")


def _check_sdk_packages() -> Check:
    missing = []
    for pkg in ["langgraph", "langchain", "semgrep", "click", "redis", "psycopg2"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if not missing:
        return Check("Python packages", True, "all installed")
    return Check("Python packages", False, f"missing: {', '.join(missing)}",
                  "Run: pip install -r requirements.txt")
