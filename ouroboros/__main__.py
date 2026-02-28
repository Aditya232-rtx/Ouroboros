"""
Allow running as ``python -m ouroboros``.

Handles the case where the ``ouroboros`` console-script entry-point
isn't on PATH (e.g. Windows without activation, broken venv, etc.).

Usage:
    python -m ouroboros init
    python -m ouroboros scan --repo <url>
    python -m ouroboros doctor
"""
from ouroboros.cli import cli

if __name__ == "__main__":
    cli()
