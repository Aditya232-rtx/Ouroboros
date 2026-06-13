#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# Ouroboros SDK — macOS / Linux Installer
# Works with any Python 3.11+  (venv, pyenv, system, conda, etc.)
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

echo ""
echo " ================================================================"
echo "  Ouroboros SDK Installer (macOS / Linux)"
echo " ================================================================"
echo ""

# ── Step 1: Find Python 3.11+ ──────────────────────────────────
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
  echo " [ERROR] Python 3.11+ not found."
  echo ""
  echo " Install options:"
  echo "   macOS:  brew install python@3.12"
  echo "   Ubuntu: sudo apt install python3.12 python3.12-venv"
  echo "   pyenv:  pyenv install 3.12.0 && pyenv local 3.12.0"
  exit 1
fi

PY_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo " [OK] Found Python: $PYTHON (version $PY_VER)"

# ── Step 2: Create virtual environment ──────────────────────────
echo " [2/5] Creating virtual environment..."
if [ -d "venv" ]; then
  echo " [OK] Virtual environment already exists."
else
  "$PYTHON" -m venv venv
  echo " [OK] Created venv/"
fi

# ── Step 3: Activate and upgrade pip ────────────────────────────
echo " [3/5] Upgrading pip..."
# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel --quiet
echo " [OK] pip upgraded."

# ── Step 4: Install the SDK ─────────────────────────────────────
echo " [4/5] Installing Ouroboros SDK..."

WHEEL=$(find dist -name "ouroboros_sdk-*.whl" 2>/dev/null | head -1 || true)

if [ -n "$WHEEL" ]; then
  echo " [OK] Installing from wheel: $WHEEL"
  pip install "$WHEEL"
else
  echo " [OK] Installing from source (pip install .)"
  pip install .
fi

# ── Step 5: Verify ──────────────────────────────────────────────
echo " [5/5] Verifying installation..."
ouroboros info || python -m ouroboros.cli info

echo ""
echo " ================================================================"
echo "  SUCCESS! Ouroboros SDK installed."
echo " ================================================================"
echo ""
echo " Quick start:"
echo "   source venv/bin/activate"
echo "   cp config.example.yaml config.yaml"
echo "   # Edit config.yaml with your GitHub token"
echo "   ouroboros scan --repo https://github.com/owner/repo"
echo ""
