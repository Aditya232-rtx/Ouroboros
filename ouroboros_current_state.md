# Ouroboros — Current State Snapshot
> **Branch:** `integrating` | **Repo:** https://github.com/Aditya232-rtx/Ouroboros  
> **Compiled:** 2026-02-27

---

## 1. Top-Level Directory Structure

```
d:\inceptrix\
├── .env.example
├── .gitignore
├── blue_agent_system_prompt.md
├── debug_meta.py
├── docker-compose.yml
├── Dockerfile
├── LICENSE
├── QUICKSTART.md
├── README.md
├── requirements.txt
│
├── config/
│   ├── __init__.py
│   ├── agent_configs.py
│   ├── model_configs.py
│   ├── security_configs.py
│   ├── settings.py
│   └── opa_policies/
│
├── context/             # Prompt context and recon data
├── docs/                # Architecture & design docs
├── frontend/            # React/Next.js dashboard (58 files)
├── infra/               # Infrastructure configs (8 files)
├── models/              # Local LLM model weights directory
├── monitoring/          # Prometheus/Grafana configs
├── research_findings/   # Scheduled research output
├── scripts/             # Utility & test scripts (38+ files)
│
├── src/                 # Core application source
│   ├── agents/          # AI agent implementations (8 files)
│   ├── api/             # FastAPI app (routes, schemas, middleware)
│   ├── database/        # SQLAlchemy sessions & models
│   ├── integrations/    # GitHub, Google, external APIs
│   ├── orchestration/   # LangGraph workflow & state machine
│   ├── resources/       # Agent prompts, templates
│   ├── security/        # Safety gates, tools, memory, reporting
│   ├── tools/           # Security tool wrappers
│   ├── utils/           # Shared utilities
│   └── verification/    # Fix verification logic
│
└── tests/               # Pytest test suite (13 items)
```

---

## 2. Python Dependencies (`requirements.txt`)

### Core Framework
| Package | Version |
|---------|---------|
| `langchain` | 1.2.7 |
| `langgraph` | 1.0.7 |
| `langchain-community` | 0.4.1 |
| `langchain-core` | 1.2.7 |
| `ollama` | 0.6.1 |

### Agent Tools (Security)
| Package | Version | Purpose |
|---------|---------|---------|
| `pyrit` | 0.10.0 | AI red-team orchestration |
| `semgrep` | 1.149.0 | SAST scanning |
| `checkov` | 3.2.0 | IaC security checks |
| `playwright` | 1.57.0 | Browser-based DAST |

### LLM / AI
| Package | Version |
|---------|---------|
| `anthropic` | 0.76.0 |
| `openai` | 2.15.0 |
| `transformers` | 4.57.6 |
| `huggingface-hub` | 0.36.0 |
| `torch` | 2.6.0 |

### Web Framework
| Package | Version |
|---------|---------|
| `fastapi` | 0.128.0 |
| `uvicorn` | 0.40.0 |
| `pydantic` | 2.12.5 |
| `pydantic-settings` | 2.12.0 |

### Integrations
| Package | Version | Purpose |
|---------|---------|---------|
| `requests` | 2.32.5 | HTTP client |
| `PyGithub` | 2.8.1 | GitHub API |
| `google-api-python-client` | 2.188.0 | Google APIs |
| `langchain-google-community` | 3.0.5 | Google LangChain |
| `mcp` | 1.23.3 | Model Context Protocol |

### Database & Storage
| Package | Version | Purpose |
|---------|---------|---------|
| `psycopg2-binary` | 2.9.11 | PostgreSQL driver |
| `redis` | 7.1.0 | Cache layer |
| `immudb-py` | 1.5.0 | Immutable audit log |
| `SQLAlchemy` | 2.0.46 | ORM |

### Security & Validation
| Package | Version |
|---------|---------|
| `cryptography` | 46.0.3 |
| `python-jose` | 3.5.0 |
| `passlib` | 1.7.4 |
| `argon2-cffi` | 25.1.0 |
| `python-dotenv` | 1.2.1 |
| `boto3` | 1.42.34 |

### Monitoring & Utilities
`prometheus-client==0.24.1` · `docker==7.1.0` · `pyyaml==6.0.3` · `jinja2==3.1.6` · `tenacity==9.1.2` · `rich==13.5.3`

### PDF Generation
`markdown==3.7.0` · `weasyprint==68.0`

### Testing & Code Quality
`pytest==9.0.2` · `pytest-asyncio==1.3.0` · `pytest-cov==7.0.0` · `httpx==0.28.1` · `black==26.1.0` · `flake8==7.3.0` · `mypy==1.19.1`

---

## 3. Docker Infrastructure (`docker-compose.yml`)

> The `docker-compose.yml` only provisions **infrastructure services**. The Ouroboros application itself is run separately (locally or via `Dockerfile`).

### Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `ouroboros-postgres` | `postgres:15-alpine` | `5432` | Primary relational database |
| `ouroboros-redis` | `redis:7-alpine` | `6379` | Caching layer |
| `ouroboros-immudb` | `codenotary/immudb:latest` | `3322` | Immutable audit log |
| `ouroboros-opa` | `openpolicyagent/opa:latest` | `8181` | Policy engine (reads `./config/opa_policies`) |

All services share the `ouroboros_network` bridge network and use named volumes for persistence.

### Environment Variable Defaults
```yaml
POSTGRES_DB: ouroboros
POSTGRES_USER: ouroboros_user
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
REDIS_PASSWORD: ${REDIS_PASSWORD:-changeme}
IMMUDB_ADMIN_PASSWORD: ${IMMUDB_PASSWORD:-immudb}
IMMUDB_DATABASE: ouroboros_audit
```

---

## 4. Application Dockerfile

**Base:** `python:3.11-slim`

### System Tools Installed
- `nmap`, `git`, `curl`, `build-essential`, `libpq-dev`, `wget`, `gnupg`
- **Docker CLI** (Docker-in-Docker control)
- **Node.js 20.x** (for MCP Servers)
- **Trivy** (container/IaC vulnerability scanner)
- **Gitleaks v8.18.2** (secrets detection)
- **Nuclei v3.2.0** (template-based DAST scanner)

### Entrypoint
```dockerfile
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s CMD curl -f http://localhost:8000/health || exit 1
```

---

## 5. Environment Variables (`.env.example`)

```ini
# Application
APP_ENV=development
DEBUG=true

# Database
DATABASE_URL=postgresql://ouroboros_user:changeme@localhost:5432/ouroboros
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://:changeme@localhost:6379/0
REDIS_CACHE_TTL=3600

# immudb
IMMUDB_HOST=localhost
IMMUDB_PORT=3322
IMMUDB_USERNAME=immudb
IMMUDB_PASSWORD=immudb
IMMUDB_DATABASE=ouroboros_audit

# OPA Policy Engine
OPA_URL=http://localhost:8181

# GitHub
GITHUB_TOKEN=your_github_token_here
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# Google Workspace
GOOGLE_SERVICE_ACCOUNT_FILE=./secrets/google-credentials.json
GOOGLE_DOCS_FOLDER_ID=your_folder_id_here

# Ollama (local LLM inference)
OLLAMA_BASE_URL=http://localhost:11434

# JWT Auth
SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# AWS (optional - Secrets Manager)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Local LLM Model Config
MODELS_DIR=./models
GPU_LAYERS=25
N_CTX=4096
N_THREADS=8

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
```

---

## 6. API Layer (`src/api/`)

### Application Entry Point (`src/api/main.py`)
**FastAPI** app with the following router structure:

| Router | Prefix | Description |
|--------|--------|-------------|
| `auth_router` | `/auth` | Registration, login, JWT tokens |
| `health_router` | `/health` | Health & readiness checks |
| `scan_router` | `/api/scan` | Initiate vulnerability scans |
| `status_router` | `/api/scan/{id}` | Scan status & progress |
| `reports_router` | `/api/reports` | Report generation & export |
| `research_router` | `/api/research` | Scheduled research scheduler |

**Middleware Stack** (LIFO): `LoggingMiddleware` → `RateLimitMiddleware` → `CORSMiddleware`

CORS allowed origins: `http://localhost:3000`, `http://127.0.0.1:3000`

---

## 7. API Payload Definitions (`src/api/schemas/__init__.py`)

### Enums

```python
class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```

### Scan Request / Response

```python
class ScanRequest(BaseModel):
    repo_url: str                       # GitHub URL to scan
    branch: str = "main"
    commit_sha: Optional[str] = None    # Specific commit (optional)
    scan_profile: str = "standard"      # quick | standard | deep
    timeout_seconds: int = 300          # 60–3600s
    auto_fix: bool = False
    create_pr: bool = False             # Requires auto_fix=True

# Example payload:
# {"repo_url": "https://github.com/example/app", "scan_profile": "standard", "auto_fix": true, "create_pr": true}

class ScanResponse(BaseModel):
    scan_id: str
    status: ScanStatus
    message: str
    created_at: datetime
```

### Vulnerability Summary

```python
class VulnerabilitySummary(BaseModel):
    id: str
    type: str
    severity: SeverityLevel
    file: str
    line: int
    description: str
    confidence: float
    cvss: float = 0.0
    # Governance fields
    risk_score: float = 0.0
    priority: int = 0
    governance_status: str = "pending"
    policy_rule: Optional[str] = None
    impact: Optional[str] = None
```

### Fix Summary

```python
class FixSummary(BaseModel):
    vulnerability_id: str
    status: str     # applied | pending | rejected
    file: str
    lines_changed: int
```

### Scan Status Response

```python
class ScanStatusResponse(BaseModel):
    scan_id: str
    repo_url: Optional[str]
    status: ScanStatus
    progress_percent: int           # 0–100
    current_phase: str
    vulnerabilities_found: int
    fixes_applied: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]

class ScanDetailResponse(ScanStatusResponse):
    vulnerabilities: List[VulnerabilitySummary] = []
    fixes: List[FixSummary] = []
    pr_url: Optional[str]
    report_url: Optional[str]
```

### Report Schemas

```python
class ReportRequest(BaseModel):
    scan_id: str
    format: str = "json"        # json | html | pdf
    include_fixes: bool = True
    include_poc: bool = False   # PoC code (security-sensitive)

class ReportResponse(BaseModel):
    report_id: str
    scan_id: str
    format: str
    download_url: str
    generated_at: datetime
    expires_at: datetime
```

### Auth Schemas

```python
class UserCreate(BaseModel):
    email: str
    password: str           # min_length=8
    full_name: Optional[str]

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserResponse(BaseModel):
    id: int
    user_id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
```

### Error / Health

```python
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str]
    code: str
    timestamp: datetime

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    uptime_seconds: float
    components: Dict[str, str]

class LogEntry(BaseModel):
    id: str
    timestamp: str
    level: str      # info | warning | error | success
    source: str
    message: str
```

---

## 8. RED Agent (`src/agents/red_agent.py`)

**Model:** `Qwen2.5-Coder-3B` via `LlamaCpp` (temperature=0.9, top_p=0.95, repeat_penalty=1.1)

### Input / Output Schemas

```python
class REDAgentInput(AgentInput):
    repo_url: str
    commit_sha: str = "HEAD"
    branch: str = "main"
    auth_token: str = ""
    scan_profile: str = "standard"     # quick | standard | deep
    timeout_seconds: int = 300

class RedAgentVulnerability(BaseModel):
    id: str                             # e.g. "RED-20260227123456"
    title: str
    type: str
    severity: str                       # critical | high | medium | low | info
    cwe: str
    cvss: float
    location: VulnerabilityLocation     # {file, line, function, parameter}
    affected_endpoint: str
    description: str
    attack_vector: str                  # network | local | adjacent | physical
    poc_code: str
    poc_success_rate: float
    remediation_hint: str
    tools_detected_by: List[str]
    confidence: float
    reasoning: str

class REDAgentOutput(AgentOutput):
    scan_id: str
    vulnerabilities: List[RedAgentVulnerability]
    statistics: Dict[str, Any]
    scan_complete: bool
```

### Execution Flow (`execute()`)

1. **Phase 0 – Identification**: Detect target type (GitHub repo, live web app, or URL)
2. **Phase 1 – Dynamic Analysis** (repos): Clone → Docker sandbox → SAST (Semgrep) + DAST (Nuclei/Nmap)
3. **Phase 2 – LLM SAST** (`_run_llm_sast_scan`): Walk sandbox files; review each with LLM prompt for code-level vulns (SQLi, XSS, hardcoded secrets, misconfigs)
4. **Phase 3 – LLM Analysis** (`_analyze_with_llm`): Feed tool findings + recon context to Qwen; get creative attack chains; parse JSON vuln list
5. **Phase 4 – Exploit Verification** (`_verify_exploit`): Attempt SQLInjector / WebExploiter / RCEExploiter for `confidence > 0.7` findings
6. **Phase 5 – Post-Exploitation** (`_attempt_privesc`): Linux PrivEsc checks + CredentialHarvester (deep scan only)
7. **Phase 6 – APT Logic** (deep + shell access): Persistence establishment + lateral movement
8. **Report Generation**: HTML report via `ReportGenerator`

### Security Tools Used
- `Semgrep` (SAST), `Nuclei` (DAST templates), `Nmap` (network), `Playwright` (browser DAST)
- `PyRIT` orchestration, `Checkov` (IaC), `CodeQL` wrapper
- `SQLInjector`, `WebExploiter`, `RCEExploiter`, `MetasploitWrapper`
- `LinuxPrivEsc`, `CredentialHarvester`, `PersistenceTools`, `LateralMovementTools`

### LLM SAST File Selection
Scans all files with extensions in: `.py .js .ts .jsx .tsx .php .go .java .rb .sh .yml .yaml .json .xml .toml .tf .sql .graphql` etc.  
Skips: `node_modules/ venv/ .git/ __pycache__/ dist/ build/`  
Priority order: auth/login/secret → db/sql → config/api → other

---

## 9. BLUE Agent (`src/agents/blue_agent.py`)

**Model:** `DeepSeek-R1-Distill-Qwen-7B` via `LlamaCpp`

### Input / Output Schemas

```python
class BLUEAgentInput(AgentInput):
    vulnerability_id: str
    vulnerability_type: str
    vulnerability_location: Dict[str, Any]  # {file, line, function, parameter}
    vulnerable_code: str
    cwe: str
    cvss: float
    language: str = "python"
    sandbox_path: Optional[str] = None     # Path to cloned repo for file reading

class CodeDiff(BaseModel):
    file: str
    before: str
    after: str
    lines_changed: int

class FixOption(BaseModel):
    option: int
    description: str
    approach: str                           # conservative | balanced | aggressive
    code_diff: CodeDiff
    test_code: str
    safety_gates: Dict[str, GateResult]
    confidence: float
    recommendation: str                     # STRONG_ACCEPT | ACCEPT | WEAK_ACCEPT | REJECT
    reasoning: str

class BLUEAgentOutput(AgentOutput):
    fix_id: str
    vulnerability_id: str
    fixes: List[FixOption]
    selected_fix: int
    statistics: Dict[str, Any]
```

### Execution Flow (`execute()`)

1. **Generate Fix Options** (`_generate_fixes`): Reads actual file from sandbox; prompts LLM for 2 distinct fixes — _Conservative_ (minimal change) and _Balanced_ (standard security)
2. **Safety Gate Validation** (`_validate_fix`): Each fix is validated through 5 safety gates
3. **Fix Selection** (`_select_best_fix`): Prefers fixes where all gates pass → highest confidence → fewest lines changed

### Fix Templates (Fallback by Vulnerability Type)
| Type | Approach | Pattern |
|------|----------|---------|
| `sql_injection` | Parameterized queries | `execute(...+...)` |
| `xss` | HTML escaping / textContent | `innerHTML / document.write` |
| `command_injection` | Safe subprocess (list args) | `shell=True / os.system` |
| `path_traversal` | Path validation / basename | `../` sequences |
| `ssrf` | URL allowlist + private IP block | `requests.get(user_input)` |
| `insecure_deserialization` | JSON / HMAC verification | `pickle.loads / yaml.load` |
| `idor` | Authorization check | `params[id]` without ownership check |
| `authentication_bypass` | bcrypt/argon2 | `md5() / sha1() / password==` |
| `cryptographic_failure` | AES-256-GCM / secrets module | `DES / MD5 / ECB` |
| `security_misconfiguration` | Secure config | `DEBUG=True / CORS(*)` |
| `cwe-250` (root user) | Least privilege | missing `USER` in Dockerfile |
| `cwe-20` (no healthcheck) | Health monitoring | missing `HEALTHCHECK` |

### Safety Gate Requirements (from system prompt)
- ❌ No `eval()`, `exec()`, or `shell=True`
- ❌ No hardcoded passwords, API keys, or secrets
- ❌ No broken authentication patterns
- ✅ All user inputs validated
- ✅ All outputs encoded/escaped
- ✅ Safe APIs used (parameterized queries, etc.)

### CWE-to-Fix Guidance Map
`CWE-89` → parameterized queries · `CWE-79` → html.escape / CSP · `CWE-78` → subprocess list args · `CWE-22` → basename / allowlist · `CWE-918` → URL allowlist / block private IPs · `CWE-502` → JSON / HMAC · `CWE-639` → ownership check · `CWE-287` → bcrypt/argon2 · `CWE-327` → AES-256-GCM

---

## 10. Other Agents (`src/agents/`)

| Agent | File | Purpose |
|-------|------|---------|
| `DocumentationAgent` | `documentation_agent.py` (17.7 KB) | Generates initial & final scan reports (HTML, PDF, Google Docs export) |
| `GovernanceAgent` | `governance_agent.py` (13.3 KB) | Risk-scores vulnerabilities, prioritizes fix queue, enforces OPA policies |
| `AuditAgent` | `audit_agent.py` (9.9 KB) | Writes immutable audit entries to immudb |
| `ResearchAgent` | `research_agent.py` (26.2 KB) | Scheduled threat intelligence research using Brave MCP |
| `BaseAgent` | `base_agent.py` (6.5 KB) | Abstract base: LLM call, JSON parsing, retry logic |

---

## 11. Orchestration Workflow (`src/orchestration/`)

### Workflow Graph (`workflow.py`)

Built with **LangGraph** `StateGraph`:

```
START
  └─► red_scan
        └─► doc_initial
              └─► governance
                    └─► blue_fix
                          └─► red_verify
                                └─► check_verification
                                      ├─► [retry]  ──► blue_fix  (max 3 retries)
                                      └─► [proceed]──► audit
                                                         ├─► [create_pr] ──► pr_creation ──► doc_final ──► END
                                                         └─► [skip_pr]   ──────────────────► doc_final ──► END
```

### Shared State (`OuroborosState` TypedDict)

```python
# Metadata
repo_url, scan_id, user_id, scan_profile, commit_sha, branch, create_pr, working_dir

# Workflow Control
current_phase, retry_count, workflow_start_time, workflow_end_time
workflow_aborted, abort_reason, errors

# Infrastructure
sandbox_info: Optional[Dict]

# Data Artifacts
vulnerabilities: List[Dict]
scan_complete: bool
scan_statistics: Dict

# Documentation
initial_report_url, initial_report_id, final_report_url, final_report_id

# Governance
prioritized_queue: List[Dict]
governance_decisions: Dict
risk_scores: Dict[str, float]

# Remediation
fixes: List[Dict]
verification_results: List[Dict]
all_verified: bool

# PR & Audit
pr_url, pr_number, pr_error
audit_entries: List[str]
```

### Verification Retry Logic
- Max **3 retries** before `workflow_aborted = True`
- Routes back to `blue_fix` node on verification failure

---

## 12. Security Layer (`src/security/`)

| Module | Description |
|--------|-------------|
| `safety_gates.py` (28.6 KB) | 5-gate fix validation pipeline |
| `models.py` | Security domain models |
| `tools/` | `executor.py` (PentestExecutor), `exploitation.py` (SQLInjector, WebExploiter, RCEExploiter, MetasploitWrapper), `privesc.py` (LinuxPrivEsc, CredentialHarvester), `persistence.py`, `lateral.py`, `browser.py`, `proxy.py` (ProxyManager/Caido) |
| `memory/` | SecurityContextBuilder — recon context accumulation |
| `reporting/` | ReportGenerator — HTML/PDF report output |

---

## 13. Tool Wrappers (`src/tools/`)

| File | Tool | Purpose |
|------|------|---------|
| `semgrep_wrapper.py` | Semgrep | SAST code scanning |
| `nuclei_wrapper.py` | Nuclei | Template-based DAST |
| `checkov_wrapper.py` | Checkov | IaC vulnerability checks |
| `codeql_wrapper.py` | CodeQL | Deep code analysis |
| `docker_sandbox.py` | Docker | Sandbox container management |
| `pyrit_orchestrator.py` | PyRIT | AI red-team orchestration |
| `brave_mcp_client.py` | Brave MCP | Web search for research agent |

---

## 14. Key Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `run_actual_orchestrated_workflow.py` | Full E2E workflow runner |
| `run_full_cycle_test.py` | Complete scan→fix→verify→PR cycle test |
| `run_v1_workflow_test.py` | V1 workflow integration test (44.9 KB) |
| `run_blue_agent_debug.py` | Blue agent debug runner |
| `run_red_agent_full_test.py` | Red agent standalone test |
| `test_doc_audit_agents.py` | Documentation & audit agent tests |
| `test_scan_workflow.py` | Scan workflow API tests |
| `test_agent_safety_gates.py` | Safety gate validation tests |
| `setup.sh` | Environment setup script |
| `init_db.py` | Database initializer |
| `start_research_scheduler.py` | Background research scheduler |
| `check_github_prs.py` | GitHub PR status checker |

---

## 15. Frontend (`frontend/`)

React/Next.js dashboard (58 files). Communicates with the FastAPI backend at `http://localhost:8000`. CORS whitelist: `localhost:3000`.

---

## 16. Quick Start Reference

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Set up environment
cp .env.example .env
# Edit .env with real secrets

# 3. Install Python deps
pip install -r requirements.txt

# 4. Run API server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Start a scan (example)
curl -X POST http://localhost:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/example/app", "scan_profile": "standard", "auto_fix": true, "create_pr": true}'
```

---

*Generated from `integrating` branch — excludes `.git/`, `__pycache__/`, `venv/`, `node_modules/`.*
