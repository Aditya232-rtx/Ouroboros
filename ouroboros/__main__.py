"""
Allow running as ``python -m ouroboros``.

Handles the case where the ``ouroboros`` console-script entry-point
isn't on PATH (e.g. Windows without activation, broken venv, etc.).
"""
from ouroboros.cli import cli

if __name__ == "__main__":
    cli()
