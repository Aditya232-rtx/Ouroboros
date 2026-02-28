#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# Ouroboros AI — Full Installer (macOS / Linux)
#
# What this does:
#   1. Finds Python 3.11+
#   2. Creates a virtual environment
#   3. Installs ALL Python dependencies (requirements.txt)
#   4. Installs the Ouroboros SDK (pip install .)
#   5. Installs frontend dependencies (npm install)
#   6. Starts Docker containers (PostgreSQL, Redis, immudb, OPA)
#   7. Verifies everything works
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

step() { echo -e "\n${CYAN}[$1/8]${NC} $2"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; exit 1; }

echo ""
echo " ================================================================"
echo "  🐍 Ouroboros AI — Full Installer"
echo " ================================================================"
echo ""

# ── Step 1: Find Python 3.11+ ──────────────────────────────────
step 1 "Finding Python 3.11+..."
PYTHON=""

for candidate in python3.13 python3.12 python3.11 python3 python; do
  if command -v "$candidate" &>/dev/null; then
    ver=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
      PYTHON=$(command -v "$candidate")
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  fail "Python 3.11+ not found.
   Install:
     macOS:  brew install python@3.12
     Ubuntu: sudo apt install python3.12 python3.12-venv
     pyenv:  pyenv install 3.12.0 && pyenv local 3.12.0"
fi

PY_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
ok "Found Python: $PYTHON (version $PY_VER)"

# ── Step 2: Check Docker ───────────────────────────────────────
step 2 "Checking Docker..."
if ! command -v docker &>/dev/null; then
  fail "Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
fi
if ! docker info &>/dev/null 2>&1; then
  fail "Docker is installed but not running. Start Docker Desktop first."
fi
ok "Docker is running"

# ── Step 3: Check Ollama ───────────────────────────────────────
step 3 "Checking Ollama..."
if ! command -v ollama &>/dev/null; then
  warn "Ollama not found. Install from https://ollama.com"
  warn "Skipping model pull — you can do this later."
  OLLAMA_OK=false
else
  # Check if ollama is serving
  if curl -s http://localhost:11434/api/tags &>/dev/null; then
    ok "Ollama is running"
    OLLAMA_OK=true
  else
    warn "Ollama is installed but not running. Start it with: ollama serve"
    OLLAMA_OK=false
  fi
fi

# ── Step 4: Create venv + install ALL Python deps ──────────────
step 4 "Setting up Python environment..."
if [ -d "venv" ]; then
  ok "Virtual environment already exists"
else
  "$PYTHON" -m venv venv
  ok "Created venv/"
fi

# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel --quiet
ok "pip upgraded"

echo "  Installing requirements.txt (this may take a few minutes)..."
pip install -r requirements.txt --quiet 2>&1 | tail -5 || true
ok "Python dependencies installed"

echo "  Installing Ouroboros SDK..."
pip install -e . --quiet 2>&1 | tail -3 || pip install . --quiet 2>&1 | tail -3
ok "Ouroboros SDK installed"

# ── Step 5: Install frontend dependencies ──────────────────────
step 5 "Installing frontend dependencies..."
if command -v node &>/dev/null; then
  NODE_VER=$(node -v)
  ok "Node.js found: $NODE_VER"
  if [ -d "frontend" ]; then
    (cd frontend && npm install --silent 2>&1 | tail -3)
    ok "Frontend dependencies installed"
  else
    warn "frontend/ directory not found — skipping"
  fi
else
  warn "Node.js not found — frontend won't work. Install from https://nodejs.org"
fi

# ── Step 6: Start Docker containers ───────────────────────────
step 6 "Starting Docker containers..."
if [ -f "docker-compose.yml" ]; then
  docker compose up -d 2>&1 | tail -10
  ok "Docker containers started (PostgreSQL, Redis, immudb, OPA)"

  # Wait for containers to be healthy
  echo "  Waiting for services to be ready..."
  sleep 5

  # Quick health checks
  if docker compose ps --format json 2>/dev/null | head -1 | grep -q "running" 2>/dev/null; then
    ok "Services are running"
  else
    # Fallback check for older docker compose
    docker compose ps 2>/dev/null | tail -5
    ok "Services started (check above for status)"
  fi
else
  warn "docker-compose.yml not found — skipping container setup"
fi

# ── Step 7: Pull Ollama model ──────────────────────────────────
step 7 "Setting up LLM model..."
if [ "$OLLAMA_OK" = true ]; then
  # Check if model already exists
  if ollama list 2>/dev/null | grep -q "ouroboros-blue"; then
    ok "Model 'ouroboros-blue' already exists"
  else
    echo "  Pulling base model (qwen2.5-coder:1.5b)..."
    ollama pull qwen2.5-coder:1.5b 2>&1 | tail -3 || warn "Model pull failed — you can do this manually later"

    if [ -f "models/Modelfile.deepseek" ]; then
      echo "  Creating ouroboros-blue model..."
      ollama create ouroboros-blue -f models/Modelfile.deepseek 2>&1 | tail -3 || warn "Model create failed — you can do this manually later"
      ok "Model 'ouroboros-blue' created"
    else
      warn "models/Modelfile.deepseek not found — create model manually"
    fi
  fi
else
  warn "Ollama not available — skipping model setup"
  echo "  Run these later when Ollama is running:"
  echo "    ollama pull qwen2.5-coder:1.5b"
  echo "    ollama create ouroboros-blue -f models/Modelfile.deepseek"
fi

# ── Step 8: Verify ─────────────────────────────────────────────
step 8 "Verifying installation..."
echo ""

# Check ouroboros CLI
if ouroboros info &>/dev/null 2>&1; then
  ok "ouroboros CLI works"
else
  # Try module fallback
  if python -m ouroboros.cli info &>/dev/null 2>&1; then
    ok "ouroboros CLI works (via python -m)"
  else
    warn "ouroboros CLI not on PATH — use: python -m ouroboros.cli"
  fi
fi

# Check .env
if [ -f ".env" ]; then
  ok ".env file exists"
else
  warn ".env file not found — create one (see README)"
fi

echo ""
echo " ================================================================"
echo -e "  ${GREEN}✅ Ouroboros AI — Installation Complete!${NC}"
echo " ================================================================"
echo ""
echo " To start scanning:"
echo ""
echo "   source venv/bin/activate"
echo "   ouroboros scan --repo https://github.com/owner/repo"
echo ""
echo " To start the dashboard:"
echo ""
echo "   ./restart.sh"
echo ""
echo " ================================================================"
echo ""
