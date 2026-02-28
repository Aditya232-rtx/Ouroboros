"""
ouroboros/init/preflight.py — Pre-flight system checks.

Validates that all required system dependencies are present before
proceeding with ``ouroboros init``.
"""

import shutil
import subprocess
import sys
import logging
from typing import List, Tuple

logger = logging.getLogger("ouroboros.init.preflight")


def check_python() -> Tuple[bool, str]:
    """Verify Python ≥ 3.11."""
    v = sys.version_info
    ok = v >= (3, 11)
    msg = f"Python {v.major}.{v.minor}.{v.micro}"
    return ok, msg


def check_git() -> Tuple[bool, str]:
    """Verify git is installed."""
    path = shutil.which("git")
    if path:
        try:
            out = subprocess.check_output(["git", "--version"], text=True).strip()
            return True, out
        except Exception:
            return True, f"git found at {path}"
    return False, "git not found — install from https://git-scm.com"


def check_docker() -> Tuple[bool, str]:
    """Verify Docker Desktop is running."""
    path = shutil.which("docker")
    if not path:
        return False, "Docker not found — install Docker Desktop: https://docker.com/get-started"

    try:
        out = subprocess.check_output(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return True, f"Docker {out}"
    except subprocess.CalledProcessError:
        return False, "Docker installed but daemon not running — start Docker Desktop"
    except Exception as e:
        return False, f"Docker check failed: {e}"


def check_docker_compose() -> Tuple[bool, str]:
    """Verify docker compose (v2 plugin) is available."""
    try:
        out = subprocess.check_output(
            ["docker", "compose", "version", "--short"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return True, f"Docker Compose {out}"
    except Exception:
        # Fallback: docker-compose (standalone)
        path = shutil.which("docker-compose")
        if path:
            return True, "docker-compose (standalone)"
        return False, "Docker Compose not found — comes with Docker Desktop"


def check_ollama() -> Tuple[bool, str]:
    """Verify Ollama is installed and running."""
    path = shutil.which("ollama")
    if not path:
        return False, (
            "Ollama not found.\n"
            "   Install:  curl -fsSL https://ollama.com/install.sh | sh\n"
            "   macOS:    brew install ollama"
        )

    try:
        out = subprocess.check_output(
            ["ollama", "--version"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        out = "installed"

    # Check if server is reachable
    try:
        import urllib.request
        req = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        return True, f"Ollama {out} (server running)"
    except Exception:
        return False, (
            f"Ollama {out} but server not running.\n"
            "   Start it:  ollama serve"
        )


def run_preflight() -> Tuple[bool, List[dict]]:
    """
    Run all pre-flight checks.

    Returns ``(all_passed, results)`` where each result is::

        {"name": "Docker", "ok": True, "detail": "Docker 24.0.7"}
    """
    checks = [
        ("Python 3.11+", check_python),
        ("Git", check_git),
        ("Docker", check_docker),
        ("Docker Compose", check_docker_compose),
        ("Ollama", check_ollama),
    ]

    results = []
    all_ok = True
    for name, fn in checks:
        ok, detail = fn()
        results.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            all_ok = False

    return all_ok, results
