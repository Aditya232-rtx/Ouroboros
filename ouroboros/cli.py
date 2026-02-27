"""
ouroboros/cli.py — Production CLI installed as the ``ouroboros`` command.

Commands:
  ouroboros scan   --repo <url>                  One-shot scan
  ouroboros watch  --repo <url> --interval 300   Continuous monitoring
  ouroboros info                                 Print SDK / env info
"""

import asyncio
import json
import sys

import click


@click.group()
@click.version_option(package_name="ouroboros-sdk")
def cli():
    """🔒 Ouroboros — Production Security Automation SDK"""


# ──────────────────────────────────────────────────────────────────
# ouroboros scan
# ──────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--repo", "-r", required=True, help="GitHub repo URL to scan")
@click.option("--config", "-c", default="config.yaml", help="Path to config.yaml")
@click.option(
    "--profile",
    "-p",
    type=click.Choice(["quick", "standard", "deep"]),
    default="standard",
    help="Scan depth profile",
)
@click.option("--no-pr", is_flag=True, help="Skip PR creation")
@click.option("--json-output", "-j", is_flag=True, help="Output JSON instead of text")
def scan(repo: str, config: str, profile: str, no_pr: bool, json_output: bool):
    """Scan any GitHub repo → generate fixes → open PR → build docs."""
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
        click.echo(f"❌  {exc}")
        sys.exit(1)
    except Exception as exc:
        click.echo(f"❌  Error: {exc}")
        sys.exit(1)

    if json_output:
        click.echo(json.dumps(result, indent=2, default=str))
        return

    click.echo("\n✅  Scan complete!")
    click.echo(f"   Scan ID               : {result.get('scan_id', '?')}")
    click.echo(f"   Vulnerabilities found  : {result['vulnerabilities_found']}")
    click.echo(f"   Critical               : {result['critical_count']}")
    click.echo(f"   Fixes generated        : {result['fixes_generated']}")
    click.echo(f"   Verified               : {result.get('verified_count', '?')}")
    click.echo(f"   Risk reduction         : {result['risk_reduction_pct']}%")
    click.echo(f"   PR URL                 : {result.get('pr_url') or '—'}")
    click.echo(f"   Security docs          : {result.get('docs_path') or '—'}")

    if result.get("errors"):
        click.echo(f"\n   ⚠️  Errors: {len(result['errors'])}")
        for e in result["errors"][:5]:
            click.echo(f"      • {e}")


# ──────────────────────────────────────────────────────────────────
# ouroboros watch
# ──────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--repo", "-r", required=True, help="GitHub repo URL to watch")
@click.option(
    "--interval", "-i", default=300, type=int, help="Seconds between scans"
)
@click.option("--config", "-c", default="config.yaml")
def watch(repo: str, interval: int, config: str):
    """Continuously monitor a repo and raise PRs on new findings."""
    from .core import Ouroboros

    try:
        ouro = Ouroboros(config)
        asyncio.run(ouro.watch(repo, interval))
    except FileNotFoundError as exc:
        click.echo(f"❌  {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n🛑  Watch mode stopped.")


# ──────────────────────────────────────────────────────────────────
# ouroboros info
# ──────────────────────────────────────────────────────────────────
@cli.command()
def info():
    """Print SDK version and environment info."""
    import ouroboros

    click.echo(f"Ouroboros SDK  v{ouroboros.__version__}")
    click.echo(f"Python         {sys.version}")

    try:
        import langgraph
        click.echo(f"LangGraph      {langgraph.__version__}")
    except Exception:
        click.echo("LangGraph      not installed")

    try:
        import semgrep
        click.echo("Semgrep        installed")
    except Exception:
        click.echo("Semgrep        not installed")

    try:
        from github import Github
        click.echo("PyGithub       installed")
    except Exception:
        click.echo("PyGithub       not installed")


if __name__ == "__main__":
    cli()
