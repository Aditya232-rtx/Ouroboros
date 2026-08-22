#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if present
if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
fi

# Bedrock bearer-token setup (primary path)
# AWS_BEARER_TOKEN_BEDROCK should be exported in the calling shell.
# If it's set, wire it as LLM_API_KEY so Strix's key-presence check passes.
if [ -n "$AWS_BEARER_TOKEN_BEDROCK" ]; then
  export STRIX_LLM="${STRIX_LLM:-bedrock/qwen.qwen3-coder-30b-a3b-v1:0}"
  export LLM_API_KEY="${LLM_API_KEY:-$AWS_BEARER_TOKEN_BEDROCK}"
  export AWS_REGION_NAME="${AWS_REGION_NAME:-us-east-1}"
fi

# Fallback: try hermes .env for OpenRouter key, but only when no provider is
# configured at all (STRIX_LLM unset) — otherwise this clobbers LLM_API_KEY
# for an already-configured route (e.g. openai/ via OpenCode Zen), causing
# strix to auth with the wrong key.
HERMES_ENV="$HOME/.hermes/.env"
if [ -f "$HERMES_ENV" ] && [ -z "$LLM_API_KEY" ] && [ -z "$STRIX_LLM" ]; then
  set -o allexport
  source "$HERMES_ENV"
  set +o allexport
  if [ -n "$OPENROUTER_API_KEY" ] && [ -z "$LLM_API_KEY" ]; then
    export LLM_API_KEY="$OPENROUTER_API_KEY"
    export STRIX_LLM="${STRIX_LLM:-openrouter/anthropic/claude-sonnet-4-6}"
  fi
fi

PORT="${PORT:-7891}"

source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port "$PORT" --reload
