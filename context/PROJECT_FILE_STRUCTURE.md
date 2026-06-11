# OUROBOROS AI - COMPLETE PROJECT FILE STRUCTURE
# Version: 1.0
# Last Updated: 2026-01-21
# Status: Production Ready (V1)

ouroboros-ai/
│
├── README.md                              # Project overview and quick start
├── LICENSE                                # License file
├── .gitignore                            # Git ignore (MUST include secrets/)
├── .env.example                          # Environment variables template (NO actual secrets)
├── docker-compose.yml                    # Multi-container orchestration
├── Dockerfile                            # Main application container
├── requirements.txt                      # Python dependencies
├── setup.py                              # Package installation
│
├── context/                              # 🔴 CRITICAL: All design documents (ALWAYS REFERENCE)
│   ├── Project_Context.md               # Complete technical architecture
│   ├── 02_AGENT_SPECIFICATIONS_V1_UPDATED.md
│   ├── 03_CRITICAL_DO_NOT_FILE_V1_UPDATED.md
│   ├── 04_CYBERATTACK_PROOF_V1_UPDATED.md
│   ├── 05_TRAINING_DATASET_RESOURCES.md
│   ├── 05_DOCUMENTATION_TRAINING_V1.md
│   ├── athenaguard-security-guide-1.pdf
│   └── OUROBOROS_SYSTEM_CONTEXT.xml     # System prompt for AI assistants
│
├── config/                               # Configuration files
│   ├── __init__.py
│   ├── settings.py                      # Global settings (loads from .env)
│   ├── agent_configs.py                 # Agent-specific configurations
│   ├── model_configs.py                 # Model loading configurations
│   ├── security_configs.py              # Security settings (WAF, rate limits)
│   └── opa_policies/                    # Open Policy Agent Rego policies
│       ├── governance_policies.rego
│       ├── risk_scoring.rego
│       └── approval_workflows.rego
│
├── src/                                  # Main source code
│   ├── __init__.py
│   │
│   ├── agents/                          # Agent implementations
│   │   ├── __init__.py
│   │   ├── base_agent.py               # Abstract base agent class
│   │   ├── red_agent.py                # RED Agent (WhiteRabbitNeo 7B)
│   │   ├── blue_agent.py               # BLUE Agent (DeepSeek-R1-Distill 7B)
│   │   ├── documentation_agent.py      # DOCUMENTATION Agent (Phi-3.5-mini)
│   │   ├── governance_agent.py         # GOVERNANCE Agent (Phi-3.5-mini)
│   │   └── audit_agent.py              # AUDIT Agent (Phi-3.5-mini)
│   │
│   ├── orchestration/                   # LangGraph workflow orchestration
│   │   ├── __init__.py
│   │   ├── state.py                    # OuroborosState TypedDict
│   │   ├── workflow.py                 # LangGraph workflow definition
│   │   ├── nodes/                      # Workflow nodes
│   │   │   ├── __init__.py
│   │   │   ├── red_scan_node.py
│   │   │   ├── doc_initial_node.py
│   │   │   ├── governance_node.py
│   │   │   ├── blue_fix_node.py
│   │   │   ├── red_verify_node.py
│   │   │   ├── doc_final_node.py
│   │   │   ├── create_pr_node.py
│   │   │   └── audit_node.py
│   │   └── edges/                      # Conditional routing logic
│   │       ├── __init__.py
│   │       ├── verification_router.py  # Route after verification
│   │       └── error_handler.py        # Error recovery routing
│   │
│   ├── models/                          # LLM model loading and management
│   │   ├── __init__.py
│   │   ├── model_loader.py             # Load GGUF models with llama-cpp-python
│   │   ├── red_model.py                # WhiteRabbitNeo 7B Q4_K_M
│   │   ├── blue_model.py               # DeepSeek-R1-Distill 7B Q4_K_M
│   │   └── support_model.py            # Phi-3.5-mini 3.8B Q6_K (shared)
│   │
│   ├── tools/                           # External tool integrations
│   │   ├── __init__.py
│   │   ├── pyrit_orchestrator.py       # PyRIT for Nuclei/Semgrep/Checkov/CodeQL
│   │   ├── nuclei_wrapper.py           # Nuclei template scanner
│   │   ├── semgrep_wrapper.py          # Semgrep SAST
│   │   ├── checkov_wrapper.py          # Checkov IaC scanner
│   │   ├── codeql_wrapper.py           # CodeQL semantic analysis
│   │   └── docker_sandbox.py           # Docker container execution
│   │
│   ├── integrations/                    # External service integrations
│   │   ├── __init__.py
│   │   ├── github_api.py               # GitHub API (clone, PR creation)
│   │   ├── google_workspace_mcp.py     # Google Docs via MCP
│   │   ├── mcp_manager.py              # MCP Server Orchestrator (NEW)
│   │   ├── opa_client.py               # Open Policy Agent client
│   │   └── immudb_client.py            # Immutable ledger client
│   │
│   ├── security/                        # Security validation and hardening
│   │   ├── __init__.py
│   │   ├── input_validation.py         # Pydantic validators
│   │   ├── code_analysis.py            # Dangerous pattern detection
│   │   ├── safety_gates.py             # 5-layer safety gate validation
│   │   ├── oauth_validator.py          # Google OAuth validation
│   │   ├── crypto_utils.py             # Digital signatures (HMAC-SHA256)
│   │   └── secrets_manager.py          # AWS Secrets Manager integration
│   │
│   ├── verification/                    # Verification loop logic
│   │   ├── __init__.py
│   │   ├── verification_engine.py      # RED-BLUE verification loop
│   │   ├── poc_executor.py             # Execute PoC attacks
│   │   └── fix_validator.py            # Validate fix effectiveness
│   │
│   ├── documentation/                   # Documentation generation
│   │   ├── __init__.py
│   │   ├── report_generator.py         # Google Docs report builder
│   │   ├── templates/                  # Report templates
│   │   │   ├── executive_summary.py
│   │   │   ├── vulnerability_details.py
│   │   │   ├── fix_details.py
│   │   │   └── compliance_evidence.py
│   │   └── formatters/                 # Document formatting utilities
│   │       ├── __init__.py
│   │       ├── markdown_to_gdocs.py
│   │       └── code_block_formatter.py
│   │
│   ├── audit/                           # Audit trail and compliance
│   │   ├── __init__.py
│   │   ├── event_logger.py             # Immutable event logging
│   │   ├── compliance_mapper.py        # SOC2/ISO27001/GDPR mapping
│   │   ├── signature_generator.py      # Digital signature creation
│   │   └── merkle_tree.py              # Merkle root calculation
│   │
│   ├── api/                             # FastAPI web interface
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI app
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── scan_routes.py          # /api/scan endpoints
│   │   │   ├── status_routes.py        # /api/status endpoints
│   │   │   ├── report_routes.py        # /api/reports endpoints
│   │   │   └── health_routes.py        # /health endpoint
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth_middleware.py      # GitHub OAuth
│   │   │   ├── rate_limiter.py         # Rate limiting (100 req/min)
│   │   │   └── waf.py                  # Web Application Firewall
│   │   └── schemas/                    # Pydantic request/response models
│   │       ├── __init__.py
│   │       ├── scan_schemas.py
│   │       └── report_schemas.py
│   │
│   ├── database/                        # Database layer
│   │   ├── __init__.py
│   │   ├── postgres.py                 # PostgreSQL connection
│   │   ├── redis_cache.py              # Redis caching
│   │   ├── immudb_ledger.py            # Immutable ledger
│   │   └── models/                     # SQLAlchemy models
│   │       ├── __init__.py
│   │       ├── scan_model.py
│   │       ├── vulnerability_model.py
│   │       ├── fix_model.py
│   │       └── audit_model.py
│   │
│   └── utils/                           # Utility functions
│       ├── __init__.py
│       ├── logger.py                   # Structured logging
│       ├── error_handler.py            # Global error handling
│       ├── metrics.py                  # Prometheus metrics
│       └── helpers.py                  # Common utility functions
│
├── tests/                               # Test suite
│   ├── __init__.py
│   ├── conftest.py                     # Pytest fixtures
│   ├── unit/                           # Unit tests
│   │   ├── test_red_agent.py
│   │   ├── test_blue_agent.py
│   │   ├── test_documentation_agent.py
│   │   ├── test_governance_agent.py
│   │   ├── test_audit_agent.py
│   │   └── test_safety_gates.py
│   ├── integration/                    # Integration tests
│   │   ├── test_verification_loop.py
│   │   ├── test_google_docs_mcp.py
│   │   ├── test_github_integration.py
│   │   └── test_opa_policies.py
│   └── e2e/                            # End-to-end tests
│       ├── test_full_workflow.py
│       └── test_sample_repos/
│           ├── vulnerable_app_python/
│           └── vulnerable_app_javascript/
│
├── models/                              # Downloaded GGUF model files
│   ├── whiterabbitneo-7b-q4_k_m.gguf   # RED Agent (4.5GB)
│   ├── deepseek-r1-distill-qwen-7b-q4_k_m.gguf  # BLUE Agent (4.8GB)
│   ├── phi-3.5-mini-instruct-q6_k.gguf # Support Agents (3.2GB)
│   └── README.md                       # Download instructions
│
├── data/                                # Training data and datasets
│   ├── red_agent_training/             # RED Agent fine-tuning data
│   │   ├── nuclei-templates/
│   │   ├── nvd_cves/
│   │   ├── codeql_patterns/
│   │   └── bug_bounty_reports/
│   ├── blue_agent_training/            # BLUE Agent fine-tuning data
│   │   ├── secure_code_examples/
│   │   ├── github_patches/
│   │   └── owasp_practices/
│   ├── governance_agent_training/      # GOVERNANCE Agent fine-tuning data
│   │   ├── opa_policies/
│   │   └── compliance_mappings/
│   └── audit_agent_training/           # AUDIT Agent fine-tuning data
│       ├── event_logs/
│       └── compliance_samples/
│
│   ├── test_red_plus_governance.py     # RED + GOVERNANCE Integration Test
│   ├── test_governance_risk.py         # Governance logic test
│   ├── test_llm_sast_integration.py    # LLM SAST verification
│   ├── run_red_agent_full_test.py      # End-to-end Red Agent test
│   ├── debug_google_mcp.py             # MCP debugging tool
│   ├── download_models.sh              # Download GGUF models from HuggingFace
│   ├── setup_environment.sh            # Setup local dev environment
│   ├── run_migrations.sh               # Database migrations
│   ├── fine_tune_models.py             # QLoRA fine-tuning script
│   ├── benchmark_models.py             # Model performance benchmarking
│   └── data_preparation/               # Training data preparation
│       ├── convert_nuclei_to_training.py
│       ├── convert_nvd_to_training.py
│       └── convert_opa_policies_to_training.py
│
├── docker/                              # Docker configurations
│   ├── app.Dockerfile                  # Main application
│   ├── red-agent-sandbox.Dockerfile    # RED Agent sandbox
│   ├── blue-agent-sandbox.Dockerfile   # BLUE Agent sandbox
│   └── nginx.Dockerfile                # Reverse proxy
│
├── infra/                               # Infrastructure as Code
│   ├── terraform/                      # Terraform configs
│   │   ├── main.tf
│   │   ├── vpc.tf
│   │   ├── security_groups.tf
│   │   ├── ec2.tf
│   │   └── rds.tf
│   └── kubernetes/                     # Kubernetes manifests
│       ├── deployment.yaml
│       ├── service.yaml
│       └── ingress.yaml
│
├── frontend/                            # Web dashboard (optional for V1)
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ScanDashboard.jsx
│   │   │   ├── VulnerabilityList.jsx
│   │   │   └── ReportViewer.jsx
│   │   └── api/
│   │       └── client.js
│   └── public/
│       └── index.html
│
├── docs/                                # Additional documentation
│   ├── architecture.md                 # System architecture diagrams
│   ├── api_reference.md                # API documentation
│   ├── deployment_guide.md             # Deployment instructions
│   ├── user_guide.md                   # User manual
│   └── diagrams/                       # Architecture diagrams (Mermaid)
│       ├── workflow.mmd
│       ├── agent_interactions.mmd
│       └── verification_loop.mmd
│
├── secrets/                             # 🔴 NEVER COMMIT - Add to .gitignore
│   ├── .gitkeep                        # Keep folder in repo
│   ├── google-service-account.json    # Google Workspace OAuth (from AWS Secrets Manager)
│   ├── github-token.env                # GitHub PAT (from AWS Secrets Manager)
│   └── anthropic-api-key.env           # Anthropic API key (from AWS Secrets Manager)
│
├── logs/                                # Application logs
│   ├── app.log
│   ├── red_agent.log
│   ├── blue_agent.log
│   └── audit.log
│
└── monitoring/                          # Monitoring and observability
    ├── prometheus.yml                  # Prometheus config
    ├── grafana/
    │   └── dashboards/
    │       ├── system_metrics.json
    │       └── agent_performance.json
    └── alerts/
        └── alert_rules.yml


# CRITICAL FILE STRUCTURE NOTES

## 🔴 MANDATORY FILES (Create First)
1. context/ folder with ALL context files
2. .gitignore (MUST exclude secrets/, logs/, models/)
3. config/settings.py (load from .env)
4. src/agents/base_agent.py
5. src/orchestration/workflow.py

## 🔴 NEVER COMMIT TO GIT
- secrets/ folder (service accounts, API keys)
- models/ folder (GGUF files are 4-5GB each)
- data/training_datasets/ (20GB+)
- logs/ folder
- .env file

## 📁 FOLDER PURPOSES

### context/
**Purpose:** Source of truth for all design decisions
**Contents:** All specification documents, security guidelines
**Usage:** ALWAYS reference before implementing anything

### src/agents/
**Purpose:** Agent implementations
**Critical:** Each agent MUST use its designated model (see context/02_AGENT_SPECIFICATIONS)

### src/orchestration/
**Purpose:** LangGraph workflow coordination
**Critical:** MUST follow patterns in context/Project_Context.md

### src/security/
**Purpose:** Security validation and hardening
**Critical:** MUST implement patterns from context/04_CYBERATTACK_PROOF

### src/verification/
**Purpose:** RED-BLUE verification loop
**Critical:** This is the differentiator - proof that fixes work

### models/
**Purpose:** Store downloaded GGUF model files
**Size:** ~12.5GB total (WhiteRabbitNeo 4.5GB + DeepSeek-R1 4.8GB + Phi-3.5 3.2GB)
**Download:** Use scripts/download_models.sh

### data/
**Purpose:** Training datasets for fine-tuning
**Size:** 20-30GB (see context/05_TRAINING_DATASET_RESOURCES.md)


## 🚀 QUICK START FILE CREATION ORDER

1. Create context/ folder → Copy all 7 context files
2. Create .gitignore → Add secrets/, models/, logs/, data/
3. Create requirements.txt → Add all dependencies
4. Create config/settings.py → Load environment variables
5. Create src/models/model_loader.py → Load GGUF models
6. Create src/agents/base_agent.py → Abstract agent class
7. Create src/agents/red_agent.py → RED Agent implementation
8. Create src/agents/blue_agent.py → BLUE Agent implementation
9. Create src/orchestration/workflow.py → LangGraph workflow
10. Create src/verification/verification_engine.py → Verification loop


## 📋 DEPENDENCIES (requirements.txt)

# Core Framework
langchain>=0.1.0
langgraph>=0.1.0
llama-cpp-python>=0.2.0  # For GGUF model loading

# Agent Tools
pyrit>=0.3.0  # Microsoft PyRIT
nuclei>=3.0.0
semgrep>=1.45.0
checkov>=3.0.0

# Integrations
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
requests>=2.31.0
PyGithub>=2.1.1
google-auth>=2.23.0
google-api-python-client>=2.100.0

# Database
psycopg2-binary>=2.9.0
redis>=5.0.0
immudb-py>=1.4.0

# Security
cryptography>=41.0.0
python-jose>=3.3.0
python-dotenv>=1.0.0
boto3>=1.28.0  # AWS Secrets Manager

# Monitoring
prometheus-client>=0.18.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0

# Utilities
docker>=6.1.0
