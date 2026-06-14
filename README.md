# 🔒 Ouroboros AI — Autonomous Security System & SDK

[![Version](https://img.shields.io/badge/version-1.1.0-blue)](https://github.com/Aditya232-rtx/Ouroboros/releases)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-yellow)](https://python.org)
[![Status](https://img.shields.io/badge/status-production-brightgreen)]()

> **Any GitHub repo → vulnerability scan → automated fixes → GitHub PR → PDF report**
> Setup time: under 3 minutes.

---

## 🚀 SDK Quick Start

### One-command install (recommended)

```bash
# 1. Clone the repo
git clone https://github.com/Aditya232-rtx/Ouroboros.git
cd Ouroboros

# 2. Run the installer:
#    Windows  →  install.bat
#    macOS/Linux  →  ./install.sh
```

### Manual install

```bash
# Create a venv and install (works on any OS)
python -m venv venv

# Activate:
#   Windows:    venv\Scripts\activate
#   macOS/Linux: source venv/bin/activate

pip install .            # installs SDK + all dependencies from source
ouroboros info           # verify it works
```

> **Windows users:** If `python` opens the Microsoft Store instead of Python,
> use `py -3` instead, or run `install.bat` which auto-detects the correct path.

### Build wheel (optional — for distributing to other machines)

```bash
pip install poetry && poetry build
# Then copy dist/ouroboros_sdk-1.1.0-py3-none-any.whl to the target machine:
pip install ouroboros_sdk-1.1.0-py3-none-any.whl
```

### Configure & run

```bash
# 1. Configure (add your GitHub token)
cp config.example.yaml config.yaml
nano config.yaml          # paste token on line 8

# 2. Scan any repo
ouroboros scan --repo https://github.com/your-org/your-app

# Alternative: run via python -m (if ouroboros isn't on PATH)
python -m ouroboros scan --repo https://github.com/your-org/your-app
```

**That's it.** Ouroboros will:
- Clone the target repo
- Detect security vulnerabilities (Semgrep + Checkov + Trivy + LLM SAST)
- Generate production-safe patches (BLUE Agent + Safety Gates)
- Verify fixes via RED re-attack loop
- Open a GitHub PR with the fixes
- Save a PDF security report locally

### Python API

```python
import asyncio
from ouroboros import Ouroboros

async def main():
    ouro   = Ouroboros("config.yaml")
    result = await ouro.scan("https://github.com/your-org/your-app")
    print(f"PR: {result['pr_url']}")
    print(f"Vulns: {result['vulnerabilities_found']}")
    print(f"Fixes: {result['fixes_generated']}")

asyncio.run(main())
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `ouroboros scan -r <url>` | One-shot scan → fixes → PR → docs |
| `ouroboros scan -r <url> -p deep` | Deep scan with privesc + lateral movement |
| `ouroboros scan -r <url> --no-pr` | Scan only, no PR creation |
| `ouroboros watch -r <url> -i 300` | Continuous monitoring every 5 min |
| `ouroboros info` | Print SDK and environment info |

---

## Overview

Ouroboros AI is an autonomous security system that discovers, fixes, and verifies vulnerabilities using a multi-agent AI architecture. Unlike traditional tools that only detect issues, Ouroboros provides a complete closed-loop system from discovery to verified remediation.

## Key Features

- **🔴 RED Agent**: Discovers vulnerabilities with advanced scanning (Semgrep + Checkov + Trivy + LLM SAST)
- **🔵 BLUE Agent**: Generates secure fixes with chain-of-thought reasoning & fix-prompt PR comments
- **📄 DOCUMENTATION Agent**: Creates live Google Docs reports & PDF exports automatically
- **⚖️ GOVERNANCE Agent**: Policy-based risk evaluation and prioritization (OPA)
- **📋 AUDIT Agent**: Immutable compliance logging (SOC2, ISO27001, GDPR) via immudb
- **✅ Verification Loop**: RED re-attacks BLUE's fixes to prove they work
- **🔁 Fix Prompts**: Each PR includes per-vulnerability developer guidance comments
- **📦 SDK & CLI**: `pip install .` → `ouroboros scan --repo <url>` — scan any repo in one command
- **⏱️ Fast**: Repository URL → verified PR in minutes (vs industry avg 70 days)

## Architecture

```
User → FastAPI / CLI → LangGraph Orchestrator
                            ↓
      RED (Scan) → DOC (Initial Report) → GOVERNANCE (Prioritize)
                            ↓
                   BLUE (Generate Fixes + Fix Prompts)
                            ↓
                  RED (Verify Fixes) ←─┐
                            ↓           │
                  All Verified?         │
                      ├─ No ───────────┘
                      └─ Yes
                            ↓
             DOC (Final Report) → Create PR (+ fix-prompt comments)
                            ↓
                    AUDIT (Log Everything)
```

## Technology Stack

### Backend
- **Orchestration**: LangGraph StateGraph, LangChain
- **LLM Runtime**: Ollama (local inference — qwen2.5-coder, deepseek, phi3)
- **Models**: WhiteRabbitNeo-7B, DeepSeek-R1-7B, Phi-3.5-mini (GGUF / Ollama)
- **Scanning**: Semgrep, Checkov, Trivy, LLM-based SAST
- **Documentation**: Google Workspace MCP, PDF report generation
- **Governance**: OPA (Open Policy Agent)
- **Audit**: immudb (immutable ledger)
- **API**: FastAPI (port 8000)
- **Database**: PostgreSQL, Redis, ChromaDB (vector store)

### Frontend
- **Framework**: Next.js 16.1.4
- **UI Library**: React 19.2.3
- **Styling**: Tailwind CSS
- **Fonts**: Inter (UI) & JetBrains Mono (code)
- **Language**: TypeScript

### SDK & CLI
- **Package**: `ouroboros-sdk` (pip-installable)
- **CLI**: `ouroboros scan` / `ouroboros watch` / `ouroboros info`
- **Build**: Poetry 2.3+ / PEP 621 (`pip install .`)
- **Platforms**: Windows, macOS, Linux

## Project Structure

```
Ouroboros/
├── ouroboros/         # SDK package (pip install .)
│   ├── __init__.py    # Version & public API
│   ├── __main__.py    # python -m ouroboros support
│   ├── cli.py         # CLI entry-point (ouroboros scan/watch/info)
│   └── core.py        # Ouroboros class — Python API
├── config/            # Configuration files
├── src/
│   ├── agents/        # Agent implementations (RED, BLUE, DOC, GOV, AUDIT)
│   ├── models/        # Model loading & Ollama integration
│   ├── orchestration/ # LangGraph StateGraph workflow & nodes
│   ├── verification/  # RED-BLUE verification loop
│   ├── tools/         # Security scanning tools (Semgrep, Checkov, Trivy)
│   ├── integrations/  # GitHub API, Google Workspace MCP
│   ├── security/      # Safety gates & sandbox enforcement
│   ├── api/           # FastAPI interface
│   └── utils/         # Shared utilities
├── frontend/          # Next.js 16 War Room Dashboard
│   ├── app/           # Next.js app router
│   ├── components/    # React components
│   └── public/        # Static assets
├── neurosploit/       # NeuroSploit attack simulation framework
├── models/            # Local GGUF model files (optional)
├── tests/             # Unit, integration, E2E, SDK tests
├── scripts/           # Utility & benchmark scripts
├── monitoring/        # Prometheus + Grafana config
├── infra/             # Kubernetes & Terraform deployment
├── context/           # Complete design documentation
├── pyproject.toml     # SDK package config (Poetry / PEP 621)
├── setup.py           # Fallback installer (pip install .)
├── install.bat        # Windows one-click installer
└── install.sh         # macOS / Linux one-click installer
```

## Installation

### Prerequisites

- Python 3.11+
- Node.js 20+ (for frontend)
- [Ollama](https://ollama.com) (recommended) or GPU with 8GB+ VRAM for local GGUF models
- Docker and Docker Compose
- 16GB RAM minimum (32GB recommended)

### Backend Setup

1. **Clone Repository**
   ```bash
   git clone https://github.com/Aditya232-rtx/Ouroboros.git
   cd Ouroboros
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start Services**
   ```bash
   docker-compose up -d  # PostgreSQL, Redis, immudb, OPA
   ```

### Frontend Setup

1. **Navigate to frontend**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Run development server**
   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000)

## Models

Ouroboros supports two model backends:

### Ollama (recommended — zero setup)

```bash
# Install Ollama: https://ollama.com
ollama pull qwen2.5-coder:1.5b   # lightweight, fast
ollama pull deepseek-r1:7b        # chain-of-thought reasoning
ollama pull phi3:mini              # support agents
```

See [docs/OLLAMA_SETUP.md](docs/OLLAMA_SETUP.md) for advanced configuration.

### Local GGUF (optional — full offline)

Download the GGUF files (~11.9 GB total) into the `models/` directory:

| Model | Size | Agent |
|-------|------|-------|
| WhiteRabbitNeo-7B-v1.5a-Q4_K_M.gguf | 4.08 GB | RED |
| DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf | 4.68 GB | BLUE |
| Phi-3.5-mini-instruct-Q6_K.gguf | 3.14 GB | DOC / GOV / AUDIT |

## Usage

### CLI (recommended)

```bash
# Scan a repo → fixes → PR → report
ouroboros scan --repo https://github.com/user/repo

# Deep scan with privilege escalation checks
ouroboros scan --repo https://github.com/user/repo --profile deep

# Scan only (no PR)
ouroboros scan --repo https://github.com/user/repo --no-pr

# Continuous monitoring (every 5 min)
ouroboros watch --repo https://github.com/user/repo --interval 300

# Environment info
ouroboros info
```

### API Server

```bash
# Start backend
uvicorn src.api.main:app --reload --port 8000

# Start frontend (in another terminal)
cd frontend && npm run dev

# Submit a scan via API
curl -X POST http://localhost:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo"}'
```

Open [http://localhost:3000](http://localhost:3000) for the War Room Dashboard.

## Development

### Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/

# Coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/
```

## Safety & Security

> **⚠️ CRITICAL: V1 Constraints**
> - NO auto-merge to production
> - All fixes require human PR review (minimum 2x)
> - All generated code runs in Docker sandbox
> - No `eval()`, `exec()`, or `shell=True`
> - All secrets managed via environment variables / AWS Secrets Manager

## Documentation

- **`context/Project_Context.md`**: Complete technical architecture
- **`context/02_AGENT_SPECIFICATIONS_V1_UPDATED.md`**: Agent specifications
- **`context/03_CRITICAL_DO_NOT_FILE_V1_UPDATED.md`**: Critical constraints
- **`context/04_CYBERATTACK_PROOF_V1_UPDATED.md`**: Security patterns
- **`context/ORCHESTRATOR_CONFIG.md`**: LangGraph workflow details

## Roadmap

### V1 (Current — Complete ✅)
- [x] Foundation and project structure
- [x] Core agents (RED, BLUE)
- [x] RED → BLUE verification loop
- [x] Support agents (DOC, GOVERNANCE, AUDIT)
- [x] LangGraph orchestration (full StateGraph pipeline)
- [x] FastAPI interface + frontend proxy
- [x] GitHub integration (PR creation, fix-prompt comments)
- [x] Frontend War Room Dashboard (Next.js 16)
- [x] Ouroboros SDK (`pip install .` + CLI)
- [x] Safety gates & sandbox enforcement
- [x] Immutable audit logging (immudb)
- [x] PDF security report generation

### V2 (Planned)
- Auto-merge for low-risk fixes (configurable risk threshold)
- Real-time monitoring & continuous watch mode
- Multi-repository batch scanning
- Advanced compliance reporting (SOC2 / ISO27001 / GDPR export)
- NeuroSploit advanced attack simulation integration
- Model fine-tuning pipeline for domain-specific scanning

## Contributing

Contributions are welcome! Ouroboros is licensed under **Apache-2.0**.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'feat: add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

Please ensure:
- All existing tests pass (`pytest tests/`)
- New features include tests
- Code follows the existing style (`black`, `flake8`, `mypy`)

## License

Apache-2.0 — See [LICENSE](LICENSE) for details.

## Contact

- **Repository**: [github.com/Aditya232-rtx/Ouroboros](https://github.com/Aditya232-rtx/Ouroboros)
- **Issues**: [GitHub Issues](https://github.com/Aditya232-rtx/Ouroboros/issues)
- **Documentation**: See `context/` and `docs/` folders

---

**Built with ❤️ for autonomous security**
