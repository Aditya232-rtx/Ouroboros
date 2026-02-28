"""
ouroboros/data/ — Bundled data files shipped inside the package.

Contains:
  docker-compose.sdk.yml   — Infrastructure compose for Postgres, Redis, immudb, OPA
  opa_policies/            — Default OPA policies (risk_calculation.rego)

These files are extracted to ``~/.ouroboros/`` during ``ouroboros init``
so Docker Compose and OPA can reference them on disk.
"""

from pathlib import Path

# Absolute path to this directory — works in pip-installed and editable modes
DATA_DIR = Path(__file__).resolve().parent

COMPOSE_FILE = DATA_DIR / "docker-compose.sdk.yml"
OPA_POLICIES_DIR = DATA_DIR / "opa_policies"
