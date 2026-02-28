"""
ouroboros/init/setup.py — Main init orchestrator.

Coordinates preflight → credentials → docker → models → verify.
"""

import os
import sys
import logging

import click

from ouroboros.config.manager import ConfigManager, get_ouroboros_home

logger = logging.getLogger("ouroboros.init.setup")


def run_init(skip_docker: bool = False, skip_models: bool = False, yes: bool = False) -> bool:
    """
    Run the full ``ouroboros init`` flow.

    Args:
        skip_docker: Skip Docker compose up (for CI/testing).
        skip_models: Skip Ollama model pull.
        yes: Auto-accept all prompts.

    Returns True if setup completed successfully.
    """
    _print_banner()

    # ── 1. Pre-flight checks ──────────────────────────────────────
    click.secho("Step 1/5  Pre-flight checks", fg="white", bold=True)
    from .preflight import run_preflight

    all_ok, results = run_preflight()
    for r in results:
        icon = "✅" if r["ok"] else "❌"
        click.echo(f"   {icon} {r['name']}: {r['detail']}")

    if not all_ok:
        # Check if only Ollama failed — that's recoverable
        critical_fails = [r for r in results if not r["ok"] and r["name"] not in ("Ollama",)]
        if critical_fails:
            click.secho("\n❌ Critical dependencies missing. Fix the above and re-run: ouroboros init", fg="red")
            return False
        click.secho("\n⚠️  Ollama not ready — model pull will be skipped.", fg="yellow")
        skip_models = True

    # ── 2. Credentials ────────────────────────────────────────────
    click.echo()
    click.secho("Step 2/5  Credentials", fg="white", bold=True)

    cfg = ConfigManager()
    existing = cfg.data if cfg.exists() else {}

    if yes and existing.get("github", {}).get("token"):
        # Non-interactive: reuse existing config
        click.echo("   Using existing configuration.")
        config_data = existing
    else:
        from .credentials import collect_credentials
        config_data = collect_credentials(existing)

    # Save config
    cfg._data = config_data
    cfg.save()

    # Generate .env
    env_path = cfg.generate_env(project_dir=_find_project_root())

    # Push to environment for this process
    cfg.apply_to_environment()

    # Also set Docker passwords in env for compose
    os.environ["POSTGRES_PASSWORD"] = config_data.get("docker", {}).get("postgres_password", "changeme")
    os.environ["REDIS_PASSWORD"] = config_data.get("docker", {}).get("redis_password", "changeme")

    click.secho(f"   ✅ Config saved → {cfg.config_path}", fg="green")
    click.secho(f"   ✅ .env saved  → {env_path}", fg="green")

    # ── 3. Docker infrastructure ──────────────────────────────────
    click.echo()
    click.secho("Step 3/5  Docker infrastructure", fg="white", bold=True)

    if skip_docker:
        click.echo("   ⏭️  Skipped (--skip-docker)")
    else:
        from .docker_setup import docker_up, wait_for_services, init_databases

        # Set OPA policies path
        project_root = _find_project_root()
        if project_root:
            opa_dir = project_root / "config" / "opa_policies"
            if opa_dir.exists():
                os.environ["OPA_POLICIES_DIR"] = str(opa_dir)

        ok = docker_up()
        if not ok:
            click.secho("   ❌ Docker setup failed", fg="red")
            return False

        svc_results = wait_for_services(timeout=90)
        all_svc_ok = all(ok for ok, _ in svc_results.values())

        if all_svc_ok:
            init_databases()
        else:
            click.secho("   ⚠️  Some services not ready — continuing anyway", fg="yellow")

    # ── 4. Model provisioning ─────────────────────────────────────
    click.echo()
    click.secho("Step 4/5  LLM model", fg="white", bold=True)

    if skip_models:
        click.echo("   ⏭️  Skipped")
    else:
        from .model_setup import pull_model, verify_model, test_model_inference

        model = config_data.get("ollama", {}).get("model", "qwen2.5-coder:3b")

        if verify_model(model):
            click.echo(f"   ✅ {model} already available")
        else:
            if not pull_model(model):
                click.secho("   ⚠️  Model pull failed — you can retry with: ouroboros models pull", fg="yellow")

        # Quick inference test
        test_model_inference(model)

    # ── 5. Verify ─────────────────────────────────────────────────
    click.echo()
    click.secho("Step 5/5  Verification", fg="white", bold=True)

    from .verify import run_verification
    return run_verification()


def _find_project_root():
    """Try to find the Ouroboros project root directory."""
    from pathlib import Path

    # Check common locations
    candidates = [
        Path.cwd(),
        Path(__file__).resolve().parent.parent.parent,
    ]
    for c in candidates:
        if (c / "docker-compose.sdk.yml").exists() or (c / "docker-compose.yml").exists():
            return c
        if (c / "src" / "api" / "main.py").exists():
            return c
    return Path.cwd()


def _print_banner():
    """Print the Ouroboros init banner."""
    click.echo()
    click.secho("╔══════════════════════════════════════════════════╗", fg="cyan")
    click.secho("║                                                  ║", fg="cyan")
    click.secho("║   🐍 Ouroboros AI — First-Time Setup             ║", fg="cyan")
    click.secho("║                                                  ║", fg="cyan")
    click.secho("║   This will:                                     ║", fg="cyan")
    click.secho("║     1. Check system dependencies                 ║", fg="cyan")
    click.secho("║     2. Collect credentials (GitHub token)        ║", fg="cyan")
    click.secho("║     3. Start Docker services                     ║", fg="cyan")
    click.secho("║     4. Pull the LLM model (~2 GB)                ║", fg="cyan")
    click.secho("║     5. Verify everything works                   ║", fg="cyan")
    click.secho("║                                                  ║", fg="cyan")
    click.secho("╚══════════════════════════════════════════════════╝", fg="cyan")
    click.echo()
