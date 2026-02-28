# 🐍 Ouroboros AI

**Autonomous security scanner — point it at any GitHub repo and get back a vulnerability report, auto-generated fixes, and a pull request.**

```
repo URL  →  RED Agent (scan)  →  BLUE Agent (fix)  →  RED re-attack (verify)  →  GitHub PR + PDF report
```

[![Version](https://img.shields.io/badge/version-1.1.0-blue)](https://github.com/Aditya232-rtx/Ouroboros/releases)
[![Python](https://img.shields.io/badge/python-3.11+-yellow)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

---

## Prerequisites

Before you start, make sure you have these four things installed and running:

| Requirement | Why | Install |
|---|---|---|
| **Python 3.11+** | Backend, agents, SDK | [python.org](https://python.org) or `brew install python@3.12` |
| **Node.js 20+** | Frontend dashboard | [nodejs.org](https://nodejs.org) |
| **Docker Desktop** | PostgreSQL, Redis, immudb, OPA containers | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| **Ollama** | Local LLM inference (no cloud API keys needed) | [ollama.com](https://ollama.com) |

> **Check:** Docker Desktop must be **running** (green whale icon in taskbar). Ollama must be **running** (`ollama serve` or the desktop app).

---

## Setup (one time)

### Step 1 — Clone

```bash
git clone https://github.com/Aditya232-rtx/Ouroboros.git
cd Ouroboros
```

### Step 2 — Pull the LLM model

Ouroboros uses a single local model for all five agents — no cloud API keys required:

```bash
ollama pull qwen2.5-coder:1.5b
```

Then create the Ouroboros-tuned variant:

```bash
ollama create ouroboros-blue -f models/Modelfile.deepseek
```

> Takes ~2 minutes. The model is ~1.5 GB. All inference runs locally on your machine.

### Step 3 — Create the `.env` file

Create a file called `.env` in the project root:

```env
# ── Required ──
GITHUB_TOKEN=ghp_PASTE_YOUR_GITHUB_TOKEN_HERE

# ── Database (matches docker-compose defaults — change in production) ──
POSTGRES_PASSWORD=changeme
REDIS_PASSWORD=changeme
DATABASE_URL=postgresql://ouroboros_user:changeme@localhost:5432/ouroboros
REDIS_URL=redis://:changeme@localhost:6379/0

# ── immudb (immutable audit log) ──
IMMUDB_PASSWORD=immudb

# ── Security ──
SECRET_KEY=change-me-to-a-random-string

# ── Optional (leave blank if not using) ──
GOOGLE_SERVICE_ACCOUNT_FILE=
GOOGLE_DOCS_FOLDER_ID=
```

> **GitHub token:** Generate at [github.com/settings/tokens](https://github.com/settings/tokens) → Classic → scopes: `repo`, `workflow`, `read:org`.

### Step 4 — Install everything

This single command creates the venv, installs all dependencies, and verifies the setup:

**macOS / Linux:**

```bash
./install.sh
```

**Windows:**

```cmd
install.bat
```

**Or do it manually (3 commands):**

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 5 — Verify the infrastructure containers

The install script already started four Docker services. Verify they're healthy:

```bash
docker compose ps
```

| Service | Port | Purpose |
|---|---|---|
| **PostgreSQL** | 5432 | Primary database |
| **Redis** | 6379 | Cache & job queue |
| **immudb** | 3322 | Immutable audit log |
| **OPA** | 8181 | Governance policy engine |

All four should show `running` (or `healthy`). Setup is done. ✅

---

## Scan a repo

### Option A — CLI (simplest)

```bash
source venv/bin/activate
ouroboros scan --repo https://github.com/owner/repo
```

Done. Ouroboros handles everything:

1. Clones the repo to a sandbox
2. **RED Agent** scans for vulnerabilities (Semgrep + Checkov + Trivy + LLM code review)
3. Auto-generates a Dockerfile if the repo doesn't have one, spins up the app in Docker, runs DAST (Nuclei, Nmap)
4. **GOVERNANCE Agent** prioritizes findings by risk
5. **BLUE Agent** generates secure code fixes
6. **RED Agent** re-attacks the fixes to verify they work
7. Opens a **GitHub Pull Request** with all fixes + per-file developer guidance comments
8. Generates a **PDF security report**
9. **AUDIT Agent** logs everything to the immutable ledger

### Option B — API + Dashboard

Start both servers with one command:

**macOS / Linux:**

```bash
./restart.sh
```

**Windows:**

```cmd
restart.bat
```

This starts:

| Server | URL | Purpose |
|---|---|---|
| **Backend** | http://localhost:8000 | FastAPI + all agents |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger UI |
| **Dashboard** | http://localhost:3000 | War Room frontend |

Logs are written to `logs/backend.log` and `logs/frontend.log`.

**Trigger a scan:**

```bash
curl -X POST http://localhost:8000/scan/ \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/owner/repo"}'
```

Open [http://localhost:3000](http://localhost:3000) for the War Room Dashboard.

> **Tip:** Run `./restart.sh` anytime to kill & restart both servers cleanly.

### CLI reference

| Command | What it does |
|---|---|
| `ouroboros scan --repo <url>` | Full scan → fixes → PR → report |
| `ouroboros scan --repo <url> --profile deep` | Deep scan with privesc checks |
| `ouroboros scan --repo <url> --no-pr` | Scan only, don't create a PR |
| `ouroboros watch --repo <url> --interval 300` | Re-scan every 5 minutes |
| `ouroboros info` | Print version & environment info |

### Python API

```python
import asyncio
from ouroboros import Ouroboros

async def main():
    ouro = Ouroboros("config.yaml")
    result = await ouro.scan("https://github.com/owner/repo")

    print(f"PR:    {result['pr_url']}")
    print(f"Vulns: {result['vulnerabilities_found']}")
    print(f"Fixes: {result['fixes_generated']}")

asyncio.run(main())
```

---

## Architecture

```
                         ┌──────────────────┐
                         │   User / CLI /   │
                         │   API Request    │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │    LangGraph     │
                         │   Orchestrator   │
                         └────────┬─────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
     ┌────────▼──────┐  ┌────────▼──────┐  ┌────────▼──────┐
     │  🔴 RED Agent │  │ 📄 DOC Agent  │  │ ⚖️ GOV Agent  │
     │  (Discover)   │  │  (Report)     │  │ (Prioritize)  │
     └────────┬──────┘  └───────────────┘  └───────────────┘
              │
     ┌────────▼──────┐
     │  🔵 BLUE Agent│◄──── Verification Loop
     │  (Fix + Patch)│          │
     └────────┬──────┘          │
              │            ┌────┴────┐
              └───────────►│RED Agent│ (re-attack)
                           └────┬────┘
                                │
                         ┌──────▼──────┐
                         │  GitHub PR  │
                         │  PDF Report │
                         │ 📋 AUDIT Log│
                         └─────────────┘
```

### Agents

| Agent | Role |
|---|---|
| 🔴 **RED** | Vulnerability discovery — SAST, LLM code review, DAST |
| 🔵 **BLUE** | Secure fix generation — chain-of-thought patching with safety gates |
| 📄 **DOC** | Report generation — Google Docs + PDF export |
| ⚖️ **GOV** | Risk prioritization via OPA policy evaluation |
| 📋 **AUDIT** | Immutable compliance logging (SOC2, ISO27001, GDPR) |

### Tech stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph StateGraph, LangChain |
| LLM | Ollama (local inference — no cloud keys) |
| Scanners | Semgrep, Checkov, Trivy, Nuclei, Nmap |
| Backend | FastAPI (port 8000) |
| Frontend | Next.js 16, React 19, Tailwind CSS (port 3000) |
| Database | PostgreSQL, Redis, ChromaDB |
| Governance | Open Policy Agent (OPA) |
| Audit | immudb (immutable ledger) |

---

## Project structure

```
Ouroboros/
├── ouroboros/              # SDK package (pip install .)
│   ├── cli.py             # CLI: ouroboros scan / watch / info
│   └── core.py            # Python API: Ouroboros class
├── src/
│   ├── agents/            # RED, BLUE, DOC, GOV, AUDIT agents
│   ├── api/               # FastAPI routes & middleware
│   ├── models/            # Ollama model loader (singleton)
│   ├── orchestration/     # LangGraph workflow & state nodes
│   ├── security/          # Safety gates, sandbox, SAST/DAST tools
│   ├── integrations/      # GitHub API, Google Workspace
│   └── database/          # PostgreSQL session management
├── frontend/              # Next.js 16 War Room Dashboard
├── config/                # Settings, model configs, OPA policies
├── models/                # Ollama Modelfiles
├── docker-compose.yml     # PostgreSQL + Redis + immudb + OPA
├── requirements.txt       # Python dependencies
├── install.sh             # macOS / Linux installer
├── install.bat            # Windows installer
└── tests/                 # Test suites
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ollama: command not found` | Install from [ollama.com](https://ollama.com) and make sure it's running |
| `docker: command not found` | Install Docker Desktop and make sure it's running |
| Port 8000 in use | `lsof -ti :8000 \| xargs kill -9` then restart |
| Port 3000 in use | `lsof -ti :3000 \| xargs kill -9` then restart |
| `GITHUB_TOKEN` errors | Check `.env` — token needs `repo` + `workflow` scopes |
| PostgreSQL connection refused | Run `docker compose ps` — make sure postgres is `healthy` |
| `Model not found` | Run `ollama create ouroboros-blue -f models/Modelfile.deepseek` |
| Semgrep / Trivy not found | `pip install semgrep` and `brew install trivy` |
| ChromaDB `KeyError` | Delete stale data: `rm -rf chroma_db/` and restart |

---

## Safety

- ❌ No auto-merge — all fixes require human PR review
- 🐳 All scanned code runs inside Docker sandboxes
- 🚫 No `eval()`, `exec()`, or `shell=True` in generated fixes
- 🔒 Secrets via environment variables only
- 📋 Every action logged to immutable audit ledger

---

## License

Apache-2.0 — see [LICENSE](LICENSE).

**Repository:** [github.com/Aditya232-rtx/Ouroboros](https://github.com/Aditya232-rtx/Ouroboros) · **Issues:** [GitHub Issues](https://github.com/Aditya232-rtx/Ouroboros/issues)
