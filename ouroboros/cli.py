"""
ouroboros/cli.py — Production CLI installed as the ``ouroboros`` command.

Full command surface:
  ouroboros init                                First-time setup
  ouroboros scan   --repo <url>                 One-shot full pipeline
  ouroboros profile --repo <url>                Quick scan, no PR
  ouroboros watch  --repo <url> --interval 300  Continuous monitoring
  ouroboros doctor                              Health-check all services
  ouroboros up                                  Start Docker infrastructure
  ouroboros down                                Stop Docker infrastructure
  ouroboros dashboard                           Start API + web UI
  ouroboros models list                         List installed LLM models
  ouroboros models pull                         Pull/update the LLM model
  ouroboros config show                         Print current config
  ouroboros config set <key> <value>            Update a config value
  ouroboros version                             Version + deps info
"""

import asyncio
import json
import os
import sys

import click


# ══════════════════════════════════════════════════════════════════
# Root group
# ══════════════════════════════════════════════════════════════════
@click.group()
@click.version_option(package_name="ouroboros-sdk")
def cli():
    """🐍 Ouroboros — Production Security Automation SDK

    \b
    Quick start:
      ouroboros init              # first-time setup
      ouroboros scan -r <url>     # scan a repo
      ouroboros doctor            # check health
    """


# ══════════════════════════════════════════════════════════════════
# ouroboros init
# ══════════════════════════════════════════════════════════════════
@cli.command()
@click.option("--skip-docker", is_flag=True, help="Skip Docker compose up")
@click.option("--skip-models", is_flag=True, help="Skip Ollama model pull")
@click.option("-y", "--yes", is_flag=True, help="Non-interactive mode")
def init(skip_docker: bool, skip_models: bool, yes: bool):
    """First-time setup: Docker, credentials, LLM model."""
    from .init import run_init

    success = run_init(skip_docker=skip_docker, skip_models=skip_models, yes=yes)
    sys.exit(0 if success else 1)


# ══════════════════════════════════════════════════════════════════
# ouroboros scan
# ══════════════════════════════════════════════════════════════════
@cli.command()
@click.option("--repo", "-r", required=True, help="GitHub repo URL to scan")
@click.option("--config", "-c", default=None, help="Path to config.yaml (default: ~/.ouroboros/config.yaml)")
@click.option(
    "--profile", "-p",
    type=click.Choice(["quick", "standard", "deep"]),
    default="standard",
    help="Scan depth profile",
)
@click.option("--no-pr", is_flag=True, help="Skip PR creation")
@click.option("--json-output", "-j", is_flag=True, help="Output JSON instead of text")
def scan(repo: str, config: str, profile: str, no_pr: bool, json_output: bool):
    """Scan a GitHub repo → find vulns → generate fixes → open PR."""
    from .core import Ouroboros

    try:
        ouro = Ouroboros(config)
        result = asyncio.run(
            ouro.scan(
                repo,
                scan_profile=profile,
                create_pr=not no_pr,
            )
        )
    except FileNotFoundError as exc:
        click.secho(f"❌  {exc}", fg="red")
        sys.exit(1)
    except Exception as exc:
        click.secho(f"❌  Error: {exc}", fg="red")
        sys.exit(1)

    if json_output:
        click.echo(json.dumps(result, indent=2, default=str))
        return

    _print_scan_result(result)


@cli.command()
@click.option("--repo", "-r", required=True, help="GitHub repo URL to profile")
@click.option("--config", "-c", default=None)
@click.option("--json-output", "-j", is_flag=True)
def profile(repo: str, config: str, json_output: bool):
    """Quick vulnerability scan — no PR, JSON output."""
    from .core import Ouroboros

    try:
        ouro = Ouroboros(config)
        result = asyncio.run(ouro.scan_quick(repo))
    except Exception as exc:
        click.secho(f"❌  Error: {exc}", fg="red")
        sys.exit(1)

    if json_output:
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        _print_scan_result(result)


# ══════════════════════════════════════════════════════════════════
# ouroboros watch
# ══════════════════════════════════════════════════════════════════
@cli.command()
@click.option("--repo", "-r", required=True, help="GitHub repo URL to watch")
@click.option("--interval", "-i", default=300, type=int, help="Seconds between scans")
@click.option("--config", "-c", default=None)
def watch(repo: str, interval: int, config: str):
    """Continuously monitor a repo and raise PRs on new findings."""
    from .core import Ouroboros

    try:
        ouro = Ouroboros(config)
        asyncio.run(ouro.watch(repo, interval))
    except FileNotFoundError as exc:
        click.secho(f"❌  {exc}", fg="red")
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n🛑  Watch mode stopped.")


# ══════════════════════════════════════════════════════════════════
# ouroboros doctor
# ══════════════════════════════════════════════════════════════════
@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Show extra detail")
def doctor(verbose: bool):
    """Run comprehensive health checks on all services."""
    from .doctor import run_doctor

    ok = run_doctor(verbose=verbose)
    sys.exit(0 if ok else 1)


# ══════════════════════════════════════════════════════════════════
# ouroboros up / down
# ══════════════════════════════════════════════════════════════════
@cli.command()
def up():
    """Start Docker infrastructure (Postgres, Redis, immudb, OPA)."""
    from .init.docker_setup import docker_up, wait_for_services
    from .config import get_config

    cfg = get_config()
    cfg.apply_to_environment()

    # Set passwords from config
    os.environ.setdefault("POSTGRES_PASSWORD", cfg.get("docker", "postgres_password", default="changeme"))
    os.environ.setdefault("REDIS_PASSWORD", cfg.get("docker", "redis_password", default="changeme"))

    ok = docker_up()
    if ok:
        wait_for_services(timeout=60)
        click.secho("\n✅ Infrastructure is up", fg="green")
    else:
        click.secho("\n❌ Failed to start infrastructure", fg="red")
        sys.exit(1)


@cli.command()
def down():
    """Stop Docker infrastructure."""
    from .init.docker_setup import docker_down

    if docker_down():
        click.secho("✅ Infrastructure stopped", fg="green")
    else:
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════
# ouroboros dashboard
# ══════════════════════════════════════════════════════════════════
@cli.command()
@click.option("--host", default="0.0.0.0", help="API bind host")
@click.option("--port", default=8000, type=int, help="API bind port")
def dashboard(host: str, port: int):
    """Start the Ouroboros API server (web dashboard)."""
    from .config import get_config

    cfg = get_config()
    cfg.apply_to_environment()

    click.secho(f"🚀 Starting Ouroboros API on {host}:{port}", fg="cyan")
    click.echo("   Dashboard: http://localhost:3000  (run frontend separately)")
    click.echo("   API docs:  http://localhost:8000/docs")
    click.echo("   Press Ctrl-C to stop\n")

    try:
        import uvicorn
        uvicorn.run(
            "src.api.main:app",
            host=host,
            port=port,
            reload=True,
        )
    except ImportError:
        click.secho("❌ uvicorn not installed. Run: pip install uvicorn", fg="red")
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n🛑 Dashboard stopped.")


# ══════════════════════════════════════════════════════════════════
# ouroboros models (subgroup)
# ══════════════════════════════════════════════════════════════════
@cli.group()
def models():
    """Manage LLM models (list, pull, test)."""


@models.command("list")
def models_list():
    """List installed Ollama models."""
    from .init.model_setup import list_models

    installed = list_models()
    if not installed:
        click.echo("No models found. Is Ollama running?")
        click.echo("  Start:  ollama serve")
        click.echo("  Pull:   ouroboros models pull")
        return

    click.secho("Installed Ollama models:\n", fg="cyan")
    for m in installed:
        name = m["name"]
        size = m.get("size", "?")
        marker = " ← active" if "qwen2.5-coder" in name else ""
        click.echo(f"  {name:<35} {size:>8}{marker}")
    click.echo()


@models.command("pull")
@click.option("--model", "-m", default="qwen2.5-coder:3b", help="Model to pull")
def models_pull(model: str):
    """Pull or update the LLM model."""
    from .init.model_setup import pull_model, test_model_inference

    if pull_model(model):
        test_model_inference(model)


@models.command("test")
@click.option("--model", "-m", default="qwen2.5-coder:3b")
def models_test(model: str):
    """Run a quick inference test on the model."""
    from .init.model_setup import test_model_inference

    ok = test_model_inference(model)
    sys.exit(0 if ok else 1)


# ══════════════════════════════════════════════════════════════════
# ouroboros config (subgroup)
# ══════════════════════════════════════════════════════════════════
@cli.group("config")
def config_group():
    """View and modify configuration."""


@config_group.command("show")
def config_show():
    """Print the current configuration."""
    import yaml
    from .config import get_config

    cfg = get_config()
    if not cfg.exists():
        click.secho("No config found. Run: ouroboros init", fg="yellow")
        return

    data = dict(cfg.data)
    # Mask secrets
    if data.get("github", {}).get("token"):
        t = data["github"]["token"]
        data["github"]["token"] = t[:4] + "…" + t[-4:] if len(t) > 8 else "****"
    if data.get("security", {}).get("secret_key"):
        data["security"]["secret_key"] = "****"

    click.secho(f"Config: {cfg.config_path}\n", fg="cyan")
    click.echo(yaml.dump(data, default_flow_style=False, sort_keys=False))


@config_group.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a config value. Use dot notation: github.token, ollama.model, etc."""
    from .config import get_config

    cfg = get_config()
    keys = key.split(".")
    cfg.set(*keys, value)
    cfg.save()

    # Regenerate .env
    cfg.generate_env()

    click.secho(f"✅ Set {key} = {value[:20]}{'…' if len(value) > 20 else ''}", fg="green")


@config_group.command("path")
def config_path():
    """Print config file locations."""
    from .config.manager import get_ouroboros_home

    home = get_ouroboros_home()
    click.echo(f"Home:   {home}")
    click.echo(f"Config: {home / 'config.yaml'}")
    click.echo(f".env:   {home / '.env'}")


# ══════════════════════════════════════════════════════════════════
# ouroboros version (detailed)
# ══════════════════════════════════════════════════════════════════
@cli.command("version")
def version_cmd():
    """Print SDK version and dependency info."""
    import ouroboros

    click.secho(f"Ouroboros SDK  v{ouroboros.__version__}", fg="cyan", bold=True)
    click.echo(f"Python        {sys.version.split()[0]}")

    deps = [
        ("langgraph", "langgraph"),
        ("langchain", "langchain"),
        ("semgrep", "semgrep"),
        ("PyGithub", "github"),
        ("redis", "redis"),
        ("psycopg2", "psycopg2"),
        ("FastAPI", "fastapi"),
        ("click", "click"),
        ("docker", "docker"),
    ]
    for display, mod in deps:
        try:
            m = __import__(mod)
            v = getattr(m, "__version__", "installed")
            click.echo(f"{display:<14}{v}")
        except ImportError:
            click.secho(f"{display:<14}not installed", fg="yellow")


# ══════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════
def _print_scan_result(result: dict):
    """Pretty-print a scan result dict."""
    click.echo()
    success = result.get("success", False)
    if success:
        click.secho("✅  Scan complete!", fg="green", bold=True)
    else:
        click.secho("⚠️  Scan finished with issues", fg="yellow", bold=True)

    click.echo(f"   Scan ID               : {result.get('scan_id', '?')}")
    click.echo(f"   Vulnerabilities found  : {result.get('vulnerabilities_found', 0)}")
    click.echo(f"   Critical               : {result.get('critical_count', 0)}")
    click.echo(f"   Fixes generated        : {result.get('fixes_generated', 0)}")
    click.echo(f"   Verified               : {result.get('verified_count', '?')}")
    click.echo(f"   Risk reduction         : {result.get('risk_reduction_pct', 0)}%")
    click.echo(f"   PR URL                 : {result.get('pr_url') or '—'}")
    click.echo(f"   Security docs          : {result.get('docs_path') or '—'}")

    if result.get("errors"):
        click.echo(f"\n   ⚠️  Errors: {len(result['errors'])}")
        for e in result["errors"][:5]:
            click.echo(f"      • {e}")
    click.echo()


if __name__ == "__main__":
    cli()
