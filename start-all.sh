#!/usr/bin/env bash
# Ouroboros — start everything for demo
# Usage: ./start-all.sh [--tunnel]
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${GREEN}⊗ Ouroboros — Starting all services${NC}"
echo ""

# ─── Check STRIX_LLM ──────────────────────────────────────────────────────────
HERMES_ENV="$HOME/.hermes/.env"
if [ -f "$HERMES_ENV" ]; then
  set -o allexport
  source "$HERMES_ENV"
  set +o allexport
fi

if [ -z "$STRIX_LLM" ]; then
  if [ -n "$OPENROUTER_API_KEY" ]; then
    export STRIX_LLM="openrouter/anthropic/claude-sonnet-4-6"
    export LLM_API_KEY="$OPENROUTER_API_KEY"
    echo -e "${CYAN}→ Using OpenRouter for Strix scans${NC}"
  else
    echo -e "${YELLOW}⚠ STRIX_LLM not set. Set it in orchestrator/.env or export it.${NC}"
    echo "  Example: export STRIX_LLM=anthropic/claude-sonnet-4-6"
    echo "           export LLM_API_KEY=your_key"
  fi
fi

# ─── Docker check ─────────────────────────────────────────────────────────────
if ! docker info &>/dev/null; then
  echo -e "${YELLOW}⚠ Docker not running. Starting Docker Desktop...${NC}"
  open -a Docker
  echo "  Waiting for Docker..."
  for i in {1..20}; do
    sleep 3
    if docker info &>/dev/null; then
      echo -e "${GREEN}  ✓ Docker ready${NC}"
      break
    fi
  done
fi

# ─── Kill existing processes ──────────────────────────────────────────────────
kill $(lsof -ti:7891) 2>/dev/null || true
kill $(lsof -ti:3000) 2>/dev/null || true
sleep 1

# ─── Start orchestrator ───────────────────────────────────────────────────────
echo -e "${CYAN}→ Starting orchestrator on :7891${NC}"
cd "$SCRIPT_DIR/orchestrator"
source venv/bin/activate
STRIX_LLM="$STRIX_LLM" LLM_API_KEY="$LLM_API_KEY" \
  uvicorn main:app --host 0.0.0.0 --port 7891 > /tmp/ouro-orchestrator.log 2>&1 &
ORCH_PID=$!

sleep 2
if curl -sf http://localhost:7891/health > /dev/null; then
  echo -e "${GREEN}  ✓ Orchestrator running (PID $ORCH_PID)${NC}"
else
  echo -e "${YELLOW}  ⚠ Orchestrator may not be ready yet, check /tmp/ouro-orchestrator.log${NC}"
fi

# ─── Start frontend ───────────────────────────────────────────────────────────
echo -e "${CYAN}→ Starting frontend on :3000${NC}"
cd "$SCRIPT_DIR/frontend"
npm run dev > /tmp/ouro-frontend.log 2>&1 &
FE_PID=$!
sleep 3
echo -e "${GREEN}  ✓ Frontend running (PID $FE_PID)${NC}"

# ─── Optional cloudflared tunnel ─────────────────────────────────────────────
if [[ "$1" == "--tunnel" ]]; then
  if command -v cloudflared &>/dev/null; then
    echo -e "${CYAN}→ Starting cloudflared tunnel for orchestrator${NC}"
    cloudflared tunnel --url http://localhost:7891 > /tmp/ouro-tunnel.log 2>&1 &
    sleep 3
    TUNNEL_URL=$(grep -o 'https://.*trycloudflare.com' /tmp/ouro-tunnel.log | head -1)
    if [ -n "$TUNNEL_URL" ]; then
      echo -e "${GREEN}  ✓ Tunnel: $TUNNEL_URL${NC}"
      echo ""
      echo -e "${YELLOW}  Update NEXT_PUBLIC_ORCHESTRATOR_URL in frontend/.env.local:${NC}"
      echo "  NEXT_PUBLIC_ORCHESTRATOR_URL=$TUNNEL_URL"
    fi
  else
    echo -e "${YELLOW}  ⚠ cloudflared not installed. Run: brew install cloudflared${NC}"
  fi
fi

echo ""
echo -e "${GREEN}⊗ Ouroboros ready!${NC}"
echo "  Frontend:      http://localhost:3000"
echo "  Orchestrator:  http://localhost:7891"
echo "  Logs:          /tmp/ouro-*.log"
echo ""
echo "  To stop: kill $ORCH_PID $FE_PID"
