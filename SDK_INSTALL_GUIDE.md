# 🐍 Ouroboros SDK — Installation & Setup Guide

> **Version:** 2.0.0  
> **Last updated:** 28 Feb 2026  
> **Target audience:** Developers setting up Ouroboros on a fresh machine

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Install the SDK](#2-install-the-sdk)
3. [First-Time Setup](#3-first-time-setup)
4. [Verify Installation](#4-verify-installation)
5. [Run Your First Scan](#5-run-your-first-scan)
6. [Command Reference](#6-command-reference)
7. [Configuration](#7-configuration)
8. [Docker Image (Alternative)](#8-docker-image-alternative)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites

Make sure the following are installed on the target machine **before** starting:

| Dependency | Minimum Version | Install Command |
|---|---|---|
| **Python** | 3.11+ | [python.org](https://www.python.org/downloads/) |
| **Git** | 2.x | `brew install git` / `apt install git` |
| **Docker** | 20.x+ | [docs.docker.com](https://docs.docker.com/get-docker/) |
| **Docker Compose** | v2+ | Bundled with Docker Desktop |
| **Ollama** | 0.1+ | [ollama.com/download](https://ollama.com/download) |

### Quick check

```bash
python3 --version          # ≥ 3.11
git --version              # ≥ 2.x
docker --version           # ≥ 20.x
docker compose version     # ≥ 2.x
ollama --version           # any recent version
```

> **Note:** Docker Desktop must be **running** (not just installed). On Linux, make sure the Docker daemon is started: `sudo systemctl start docker`.

---

## 2. Install the SDK

### Option A — From GitHub (recommended)

```bash
# Clone the repository
git clone https://github.com/Aditya232-rtx/Ouroboros.git
cd Ouroboros

# Switch to the latest branch
git checkout v1.1

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate      # macOS / Linux
# venv\Scripts\activate       # Windows PowerShell

# Install the SDK in editable mode
pip install -e .
```

### Option B — Direct pip install

```bash
pip install git+https://github.com/Aditya232-rtx/Ouroboros.git@v1.1
```

### Verify the install

```bash
ouroboros version
```

Expected output:

```
Ouroboros SDK  v2.0.0
Python        3.11.x
langgraph     installed
langchain     1.x.x
semgrep       installed
PyGithub      installed
redis         x.x.x
psycopg2      x.x.x
FastAPI       x.x.x
click         x.x.x
docker        x.x.x
```

---

## 3. First-Time Setup

Run the interactive setup wizard — it handles **everything**:

```bash
ouroboros init
```

This walks you through 5 steps:

| Step | What it does |
|---|---|
| **1. Preflight** | Checks Python ≥ 3.11, Git, Docker (running), Docker Compose, Ollama |
| **2. Credentials** | Prompts for your GitHub token, auto-generates Postgres/Redis/secret passwords |
| **3. Docker** | Pulls & starts 4 infrastructure containers (Postgres, Redis, immudb, OPA) |
| **4. LLM Model** | Pulls `qwen2.5-coder:3b` (~1.9 GB) via Ollama and runs an inference test |
| **5. Verify** | Checks all containers are healthy, databases are reachable, model responds |

### What you'll need ready

- **GitHub Personal Access Token** — with `repo` scope  
  → Create one at: [github.com/settings/tokens](https://github.com/settings/tokens)

### What gets created

```
~/.ouroboros/
├── config.yaml     # All SDK configuration
└── .env            # Environment variables for Docker services
```

> **Tip:** If any step fails, run `ouroboros doctor` to see exactly what's wrong and how to fix it.

---

## 4. Verify Installation

After `ouroboros init` completes, run the health check:

```bash
ouroboros doctor
```

A healthy setup shows **12/12 checks passed**:

```
🩺  Ouroboros Doctor — Health Check

System
  ✅ Python version        3.11.x
  ✅ Docker daemon          running
  ✅ Docker Compose          v2.x.x

Config
  ✅ Config file             ~/.ouroboros/config.yaml
  ✅ GitHub token              configured

Infrastructure
  ✅ PostgreSQL               localhost:5432 — responding
  ✅ Redis                    localhost:6379 — responding
  ✅ immudb                   localhost:3322 — responding
  ✅ OPA                      localhost:8181 — responding

LLM
  ✅ Ollama server             running
  ✅ qwen2.5-coder:3b          installed

SDK
  ✅ ouroboros-sdk              v2.0.0
```

---

## 5. Run Your First Scan

### Full scan (finds vulns → generates fixes → opens a PR)

```bash
ouroboros scan --repo https://github.com/<owner>/<repo>
```

or with the short flag:

```bash
ouroboros scan -r https://github.com/<owner>/<repo>
```

### Quick profile (scan only, no PR)

```bash
ouroboros profile --repo https://github.com/<owner>/<repo>
```

### Continuous monitoring (re-scans on an interval)

```bash
ouroboros watch --repo https://github.com/<owner>/<repo> --interval 300
```

> `--interval` is in seconds (default: 300 = 5 minutes).

### Example — end to end

```bash
# 1. Scan a test repository
ouroboros scan -r https://github.com/juice-shop/juice-shop

# 2. View JSON results
ouroboros profile -r https://github.com/juice-shop/juice-shop -o results.json
```

---

## 6. Command Reference

| Command | Description |
|---|---|
| `ouroboros init` | Interactive first-time setup (Docker, creds, model) |
| `ouroboros scan -r <url>` | Full pipeline: scan → fix → PR |
| `ouroboros profile -r <url>` | Quick vulnerability scan (JSON output, no PR) |
| `ouroboros watch -r <url>` | Continuous monitoring loop |
| `ouroboros doctor` | Health-check all services (12 checks) |
| `ouroboros up` | Start Docker infrastructure |
| `ouroboros down` | Stop Docker infrastructure |
| `ouroboros dashboard` | Launch API server on port 8000 |
| `ouroboros models list` | Show installed Ollama models |
| `ouroboros models pull` | Pull/update `qwen2.5-coder:3b` |
| `ouroboros models test` | Run quick inference test |
| `ouroboros config show` | Print current configuration |
| `ouroboros config set <key> <val>` | Update a config value |
| `ouroboros config path` | Show config file locations |
| `ouroboros version` | Print SDK version + dependency info |
| `ouroboros --help` | Show all commands |

---

## 7. Configuration

### Config file location

```
~/.ouroboros/config.yaml
```

### View current config

```bash
ouroboros config show
```

### Set a value

```bash
ouroboros config set github.token ghp_xxxxxxxxxxxx
ouroboros config set llm.model qwen2.5-coder:3b
ouroboros config set services.postgres.port 5432
```

### Config structure

```yaml
github:
  token: "ghp_..."

llm:
  model: "qwen2.5-coder:3b"
  base_url: "http://localhost:11434"

services:
  postgres:
    host: "localhost"
    port: 5432
    database: "ouroboros"
    user: "ouroboros_user"
    password: "<auto-generated>"
  redis:
    host: "localhost"
    port: 6379
    password: "<auto-generated>"
  immudb:
    host: "localhost"
    port: 3322
  opa:
    host: "localhost"
    port: 8181

security:
  secret_key: "<auto-generated>"
```

### Environment file

Docker service passwords and the GitHub token are also written to:

```
~/.ouroboros/.env
```

---

## 8. Docker Image (Alternative)

If you prefer running the SDK entirely inside a container (no local Python install needed):

### Pull / Build the image

```bash
# Build from source
git clone https://github.com/Aditya232-rtx/Ouroboros.git
cd Ouroboros
docker build -f docker/sdk.Dockerfile -t ouroboros-sdk:2.0.0 .
```

### Run commands inside the container

```bash
# Check version
docker run --rm ouroboros-sdk:2.0.0 ouroboros version

# Show help
docker run --rm ouroboros-sdk:2.0.0 ouroboros --help

# Run a scan (mount your config)
docker run --rm \
  -v ~/.ouroboros:/home/ouroboros/.ouroboros:ro \
  --network host \
  ouroboros-sdk:2.0.0 \
  ouroboros scan -r https://github.com/<owner>/<repo>
```

### Start full infrastructure + SDK

```bash
# Start infrastructure services
docker compose -f docker-compose.sdk.yml up -d

# Then run SDK commands as above
```

### Image contents

| Tool | Version |
|---|---|
| Python | 3.11 |
| Trivy | 0.69.x |
| Gitleaks | 8.18.x |
| Semgrep | bundled via pip |
| Ouroboros SDK | 2.0.0 |

---

## 9. Troubleshooting

### `ouroboros: command not found`

Your virtual environment isn't activated, or the install didn't register the entry point.

```bash
# Activate venv
source venv/bin/activate

# Reinstall
pip install -e .

# Verify
which ouroboros
```

### Docker containers won't start

```bash
# Make sure Docker Desktop is running, then:
ouroboros down
ouroboros up

# Check container status
docker ps -a --filter "name=ouroboros"
```

### Ollama model not found

```bash
# Make sure Ollama is running
ollama serve &

# Pull the model
ouroboros models pull

# Verify
ouroboros models list
```

### `ouroboros doctor` shows failures

Run doctor and follow the fix suggestions printed next to each `❌`:

```bash
ouroboros doctor
```

Common fixes:

| Issue | Fix |
|---|---|
| Docker daemon not running | Start Docker Desktop or `sudo systemctl start docker` |
| PostgreSQL not responding | `ouroboros up` to start containers |
| Redis auth failed | Delete `~/.ouroboros/.env` and re-run `ouroboros init` |
| Config not found | Run `ouroboros init` to generate config |
| Model not installed | `ouroboros models pull` |
| Ollama not reachable | Start Ollama: `ollama serve` |

### Port conflicts

If ports 5432, 6379, 3322, or 8181 are already in use:

```bash
# Find what's using a port
lsof -i :5432

# Kill it
lsof -ti :5432 | xargs kill -9

# Or change the port in config
ouroboros config set services.postgres.port 5433
```

### Reset everything

```bash
# Stop and remove all containers + volumes
ouroboros down
docker compose -f docker-compose.sdk.yml down -v

# Remove config
rm -rf ~/.ouroboros

# Start fresh
ouroboros init
```

---

## Quick Reference Card

```
┌──────────────────────────────────────────────────┐
│           🐍  Ouroboros SDK v2.0.0               │
├──────────────────────────────────────────────────┤
│                                                  │
│  INSTALL                                         │
│  git clone https://github.com/                   │
│       Aditya232-rtx/Ouroboros.git                │
│  cd Ouroboros && git checkout v1.1               │
│  python3 -m venv venv && source venv/bin/activate│
│  pip install -e .                                │
│                                                  │
│  SETUP                                           │
│  ouroboros init         ← one-time wizard        │
│                                                  │
│  USE                                             │
│  ouroboros scan -r <url>   ← full pipeline       │
│  ouroboros profile -r <url>← quick scan          │
│  ouroboros doctor          ← health check        │
│                                                  │
│  MANAGE                                          │
│  ouroboros up / down       ← infra services      │
│  ouroboros models pull     ← update LLM          │
│  ouroboros config show     ← view settings       │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

**Need help?** Open an issue at [github.com/Aditya232-rtx/Ouroboros/issues](https://github.com/Aditya232-rtx/Ouroboros/issues)
