#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# Ouroboros AI — Restart Script (macOS / Linux)
#
# Kills any existing backend/frontend processes, then starts both.
#   Backend:  FastAPI on port 8000
#   Frontend: Next.js on port 3000
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo -e "${CYAN} ================================================================${NC}"
echo -e "${CYAN}  🔄 Ouroboros AI — Restarting Servers${NC}"
echo -e "${CYAN} ================================================================${NC}"
echo ""

# ── Step 1: Kill existing processes ─────────────────────────────
echo -e "${YELLOW}[1/4]${NC} Stopping existing servers..."

# Kill backend (port 8000)
if lsof -ti :8000 &>/dev/null; then
  lsof -ti :8000 | xargs kill -9 2>/dev/null || true
  echo -e "  ${GREEN}✓${NC} Backend stopped (port 8000)"
else
  echo -e "  ${GREEN}✓${NC} Backend not running"
fi

# Kill frontend (port 3000)
if lsof -ti :3000 &>/dev/null; then
  lsof -ti :3000 | xargs kill -9 2>/dev/null || true
  echo -e "  ${GREEN}✓${NC} Frontend stopped (port 3000)"
else
  echo -e "  ${GREEN}✓${NC} Frontend not running"
fi

sleep 1

# ── Step 2: Ensure Docker containers are running ────────────────
echo -e "${YELLOW}[2/4]${NC} Checking Docker containers..."
if [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
  cd "$PROJECT_DIR"
  RUNNING=$(docker compose ps --status running -q 2>/dev/null | wc -l | tr -d ' ')
  if [ "$RUNNING" -lt 3 ]; then
    echo "  Starting Docker containers..."
    docker compose up -d 2>&1 | tail -5
    sleep 3
  fi
  echo -e "  ${GREEN}✓${NC} Docker containers running"
else
  echo -e "  ${YELLOW}⚠${NC} docker-compose.yml not found"
fi

# ── Step 3: Start backend ──────────────────────────────────────
echo -e "${YELLOW}[3/4]${NC} Starting backend (FastAPI on port 8000)..."
cd "$PROJECT_DIR"

# Activate venv
if [ -f "venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
else
  echo -e "  ${RED}✗${NC} venv not found — run ./install.sh first"
  exit 1
fi

# Start backend in background
nohup uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload \
  > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "  ${GREEN}✓${NC} Backend started (PID: $BACKEND_PID)"

# ── Step 4: Start frontend ────────────────────────────────────
echo -e "${YELLOW}[4/4]${NC} Starting frontend (Next.js on port 3000)..."
if [ -d "$PROJECT_DIR/frontend" ]; then
  cd "$PROJECT_DIR/frontend"

  # Install deps if node_modules missing
  if [ ! -d "node_modules" ]; then
    echo "  Installing frontend dependencies..."
    npm install --silent 2>&1 | tail -3
  fi

  nohup npm run dev > "$PROJECT_DIR/logs/frontend.log" 2>&1 &
  FRONTEND_PID=$!
  echo -e "  ${GREEN}✓${NC} Frontend started (PID: $FRONTEND_PID)"
else
  echo -e "  ${YELLOW}⚠${NC} frontend/ directory not found — skipping"
fi

# ── Wait & verify ──────────────────────────────────────────────
echo ""
echo "  Waiting for servers to start..."
sleep 4

# Check backend
if curl -s http://localhost:8000/docs &>/dev/null; then
  echo -e "  ${GREEN}✓${NC} Backend ready  → http://localhost:8000"
else
  echo -e "  ${YELLOW}⚠${NC} Backend still starting — check logs/backend.log"
fi

# Check frontend
if curl -s http://localhost:3000 &>/dev/null; then
  echo -e "  ${GREEN}✓${NC} Frontend ready → http://localhost:3000"
else
  echo -e "  ${YELLOW}⚠${NC} Frontend still starting — check logs/frontend.log"
fi

echo ""
echo -e "${CYAN} ================================================================${NC}"
echo -e "  ${GREEN}✅ Ouroboros AI is running!${NC}"
echo ""
echo "  Backend API:  http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"
echo "  Dashboard:    http://localhost:3000"
echo ""
echo "  Logs:"
echo "    tail -f logs/backend.log"
echo "    tail -f logs/frontend.log"
echo ""
echo "  To stop:  ./stop.sh  (or kill ports 8000 & 3000)"
echo -e "${CYAN} ================================================================${NC}"
echo ""
