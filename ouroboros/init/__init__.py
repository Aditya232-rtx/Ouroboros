"""
ouroboros/init/ — First-time setup orchestrator.

``ouroboros init`` walks the user through:
  1. Pre-flight checks  (Docker, Ollama, Python, Git)
  2. Credential prompts  (GitHub token, auto-gen passwords)
  3. Docker compose up   (Postgres, Redis, immudb, OPA)
  4. Model provisioning  (ollama pull qwen2.5-coder:3b)
  5. Post-setup verify   (all services reachable)
"""

from .setup import run_init

__all__ = ["run_init"]
