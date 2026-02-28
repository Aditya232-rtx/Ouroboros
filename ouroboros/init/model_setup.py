"""
ouroboros/init/model_setup.py — Ollama model provisioning.

Pulls the single qwen2.5-coder:3b model used by ALL agents and
verifies it's available via the Ollama API.
"""

import subprocess
import logging
import time

import click

logger = logging.getLogger("ouroboros.init.model_setup")

# Single model for all agents
MODEL_NAME = "qwen2.5-coder:3b"


def pull_model(model: str = MODEL_NAME) -> bool:
    """
    Pull the Ollama model.  Shows real-time progress.
    Returns True if successful.
    """
    click.echo()
    click.secho("🧠 Pulling LLM model …", fg="cyan", bold=True)
    click.echo(f"   Model: {model}  (~2 GB download on first run)")
    click.echo()

    try:
        proc = subprocess.run(
            ["ollama", "pull", model],
            check=True,
            # Let output stream to terminal so user sees download progress
        )
        click.echo()
        click.secho(f"   ✅ {model} ready", fg="green")
        return True
    except subprocess.CalledProcessError as e:
        click.secho(f"   ❌ Failed to pull {model}: exit code {e.returncode}", fg="red")
        return False
    except FileNotFoundError:
        click.secho("   ❌ ollama command not found", fg="red")
        return False


def verify_model(model: str = MODEL_NAME) -> bool:
    """Check that the model is available in Ollama."""
    try:
        out = subprocess.check_output(
            ["ollama", "list"], text=True, stderr=subprocess.DEVNULL,
        )
        # ollama list output has model names in first column
        for line in out.strip().splitlines():
            if model.split(":")[0] in line:
                return True
        return False
    except Exception:
        return False


def test_model_inference(model: str = MODEL_NAME) -> bool:
    """
    Run a quick inference test to verify the model responds.
    Returns True if model generates a response.
    """
    click.echo("   Testing model inference …")
    try:
        proc = subprocess.run(
            ["ollama", "run", model, "Say hello in one word."],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            click.secho(f"   ✅ Model responds: \"{proc.stdout.strip()[:50]}\"", fg="green")
            return True
        else:
            click.secho("   ⚠️  Model returned empty response", fg="yellow")
            return False
    except subprocess.TimeoutExpired:
        click.secho("   ⚠️  Model inference timed out (60s) — may still be loading", fg="yellow")
        return False
    except Exception as e:
        click.secho(f"   ⚠️  Inference test failed: {e}", fg="yellow")
        return False


def list_models() -> list:
    """Return a list of installed Ollama models."""
    try:
        out = subprocess.check_output(
            ["ollama", "list"], text=True, stderr=subprocess.DEVNULL,
        )
        models = []
        for line in out.strip().splitlines()[1:]:  # skip header
            parts = line.split()
            if parts:
                models.append({
                    "name": parts[0],
                    "size": parts[2] if len(parts) > 2 else "?",
                    "modified": " ".join(parts[3:]) if len(parts) > 3 else "",
                })
        return models
    except Exception:
        return []
