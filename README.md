# Ouroboros AI - Autonomous Security System

**Version:** 1.0.0  
**Status:** In Development

## Overview

Ouroboros AI is an autonomous security system that discovers, fixes, and verifies vulnerabilities using a multi-agent AI architecture. Unlike traditional tools that only detect issues, Ouroboros provides a complete closed-loop system from discovery to verified remediation.

## Key Features

- **🔴 RED Agent (WhiteRabbitNeo-7B)**: Discovers vulnerabilities with <5% false positive rate
- **🔵 BLUE Agent (DeepSeek-R1)**: Generates secure fixes with chain-of-thought reasoning
- **📄 DOCUMENTATION Agent (Phi-3.5)**: Creates live Google Docs reports automatically
- **⚖️ GOVERNANCE Agent (Phi-3.5)**: Policy-based risk evaluation and prioritization
- **📋 AUDIT Agent (Phi-3.5)**: Immutable compliance logging (SOC2, ISO27001, GDPR)
- **✅ Verification Loop**: RED re-attacks BLUE's fixes to prove they work
- **⏱️ Fast**: Repository URL → PR in <2 hours (vs industry 70 days)

## Architecture

```
User → FastAPI → LangGraph Orchestrator
                      ↓
    RED (Scan) → DOC (Report) → GOVERNANCE (Prioritize)
                      ↓
             BLUE (Generate Fixes)
                      ↓
            RED (Verify Fixes) ←─┐
                      ↓           │
            All Verified?         │
                ├─ No ───────────┘
                └─ Yes
                      ↓
           DOC (Final Report) → Create PR
                      ↓
              AUDIT (Log Everything)
```

## Technology Stack

### Backend
- **Orchestration**: LangGraph, LangChain
- **Models**: WhiteRabbitNeo-7B, DeepSeek-R1-7B, Phi-3.5-mini
- **Scanning**: PyRIT, Nuclei, Semgrep, Checkov, CodeQL
- **Documentation**: Google Workspace MCP
- **Governance**: OPA (Open Policy Agent)
- **Audit**: immudb (immutable ledger)
- **API**: FastAPI
- **Database**: PostgreSQL, Redis

### Frontend
- **Framework**: Next.js 16.1.4
- **UI Library**: React 19.2.3
- **Styling**: Lightswind CSS
- **Fonts**: Inter (UI) & JetBrains Mono (code)
- **Language**: TypeScript

## Project Structure

```
ouroboros/
├── config/           # Configuration files
├── src/
│   ├── agents/       # Agent implementations
│   ├── models/       # Model loading
│   ├── orchestration/# LangGraph workflow
│   ├── verification/ # RED-BLUE loop
│   ├── tools/        # Security scanning tools
│   ├── integrations/ # GitHub, Google Workspace
│   ├── security/     # Safety gates
│   ├── api/          # FastAPI interface
│   └── utils/        # Utilities
├── frontend/         # Next.js frontend application
│   ├── app/          # Next.js app router
│   ├── components/   # React components
│   └── public/       # Static assets
├── models/           # GGUF model files (11.9 GB)
├── tests/            # Unit, integration, E2E tests
└── context/          # Complete design documentation
```

## Installation

### Prerequisites

- Python 3.11+
- Node.js 20+
- GPU with 8GB+ VRAM (RTX 4060 Ti or better recommended)
- Docker and Docker Compose
- 32GB RAM recommended

### Backend Setup

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-org/ouroboros.git
   cd ouroboros
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

All required GGUF models (11.9 GB total):

- **WhiteRabbitNeo-7B-v1.5a-Q4_K_M.gguf** (4.08 GB) - RED Agent
- **DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf** (4.68 GB) - BLUE Agent  
- **Phi-3.5-mini-instruct-Q6_K.gguf** (3.14 GB) - Support Agents

## Usage

### Command Line

```bash
# Test model loading
python -m scripts.test_models

# Run full scan
python -m src.main --repo https://github.com/user/repo
```

### API

```bash
# Start API server
uvicorn src.api.main:app --reload --port 8000

# Submit scan
curl -X POST http://localhost:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo"}'
```

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

### V1 (Current - In Development)
- [x] Foundation and project structure
- [/] Core agents (RED, BLUE)
- [ ] Verification loop
- [ ] Support agents (DOC, GOVERNANCE, AUDIT)
- [ ] LangGraph orchestration
- [ ] FastAPI interface
- [ ] GitHub integration
- [ ] Frontend War Room Dashboard

### V2 (Future)
- Auto-merge for low-risk fixes
- Real-time monitoring
- Multi-repository scanning
- Advanced compliance reporting

## Contributing

This is a private/internal project. Contact the security team for contribution guidelines.

## License

Proprietary - Internal use only

## Contact

- **Team**: Ouroboros AI Security Team
- **Documentation**: See `context/` folder
- **Issues**: Internal issue tracker

---

**Built with ❤️ for autonomous security**
