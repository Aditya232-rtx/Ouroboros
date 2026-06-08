# OUROBOROS AI: NON-NEGOTIABLE AGENT SPECIFICATIONS (V1 UPDATED)
**Version:** 1.1  
**Date:** January 19, 2026  
**Status:** Specification Locked (V1)  
**Total Pages:** 14+

---

## TABLE OF CONTENTS
1. [RED Agent Specifications](#red-agent-specifications)
2. [BLUE Agent Specifications](#blue-agent-specifications)
3. [DOCUMENTATION Agent Specifications (NEW)](#documentation-agent-specifications-new)
4. [GOVERNANCE Agent Specifications](#governance-agent-specifications)
5. [AUDIT Agent Specifications](#audit-agent-specifications)
6. [Cross-Agent Contracts](#cross-agent-contracts)
7. [Error Handling & Recovery](#error-handling--recovery)
8. [Verification Loop Requirements (V1 UPDATE)](#verification-loop-requirements-v1-update)

---

## RED AGENT SPECIFICATIONS

### Core Responsibility
**Continuous vulnerability discovery and proof-of-concept generation using autonomous red team techniques. The RED agent is offense. Its job is to PROVE attackers can exploit the system.**

### Input Contract (What RED Receives)

```json
{
  "target": {
    "repo": "string (github.com/owner/repo)",
    "commit_sha": "string (git hash)",
    "branch": "string (main, dev, staging)",
    "code_files": ["src/app.py", "src/db.py", ...],
    "environment": "dev|staging|production",
    "scan_profile": "quick|standard|deep",
    "timeout_seconds": 300
  },
  "config": {
    "scanning_tools": ["nuclei", "semgrep", "checkov", "codeql"],
    "nuclei_templates": ["sqli", "xss", "rce", "ssrf", "auth"],
    "severity_filter": "low|medium|high|critical",
    "include_pocs": true,
    "language_focus": "python|javascript|go|java"
  },
  "context": {
    "previous_findings": [...],
    "known_false_positives": [...],
    "target_architecture": "monolith|microservices|serverless"
  }
}
```

### Output Contract (What RED Produces)

```json
{
  "scan_id": "string (uuid, correlates to audit trail)",
  "timestamp": "ISO8601",
  "vulnerabilities": [
    {
      "id": "string (RED-{timestamp}-{index})",
      "type": "string (sql_injection|xss|rce|ssrf|auth_bypass|...)",
      "severity": "critical|high|medium|low",
      "cwe": "string (CWE-89, CWE-78, ...)",
      "cvss": "number (0.0-10.0)",
      "location": {
        "file": "string (relative path)",
        "line": "number",
        "function": "string",
        "parameter": "string"
      },
      "description": "string (technical details, why it's vulnerable)",
      "attack_vector": "network|local|adjacent|physical",
      "poc_code": "string (runnable exploit code or curl command)",
      "poc_success_rate": "number (0.0-1.0, based on testing)",
      "remediation_hint": "string (e.g., 'use parameterized queries')",
      "tools_detected_by": ["nuclei", "semgrep"],
      "confidence": "number (0.0-1.0, 0.95 = very confident this is real)"
    }
  ],
  "statistics": {
    "total_vulnerabilities": "number",
    "by_severity": { "critical": 2, "high": 5, "medium": 12, "low": 3 },
    "tools_used": ["nuclei", "semgrep", "checkov"],
    "scan_duration_seconds": "number",
    "false_positive_rate": "number (estimated, historical)"
  },
  "errors": [
    {
      "tool": "string",
      "error_message": "string",
      "recoverable": "boolean"
    }
  ]
}
```

### Key Requirements (NON-NEGOTIABLE)

1. **Proof-of-Concept Generation**
   - ✅ MUST generate exploit code or commands for each vulnerability
   - ✅ PoC MUST be testable/runnable in digital twin
   - ✅ PoC success rate MUST be tracked and improved
   - ❌ NO generic descriptions without proof

2. **Tool Orchestration (via PyRIT)**
   - ✅ MUST call Nuclei, Semgrep, Checkov, CodeQL
   - ✅ MUST parallelize tool calls (all 4 simultaneously)
   - ❌ NO sequential tool calling

3. **Verification Loop (V1 UPDATE)**
   - ✅ RED MUST test own PoC against vulnerable code
   - ✅ RED MUST validate vulnerability exists (proof)
   - ✅ RED result feeds to BLUE for fix generation
   - ✅ After BLUE fix: RED re-runs PoC to verify vulnerability is GONE
   - ⚠️ V1: RED validates but DOES NOT auto-merge (manual PR review required)

4. **Performance**
   - ✅ MUST complete scan in <60 seconds (quick profile)
   - ✅ MUST handle codebases up to 1M lines
   - ❌ NO timeouts under normal conditions

5. **Output Consistency**
   - ✅ MUST return ONLY valid JSON
   - ✅ MUST include ALL required fields
   - ✅ MUST sort vulnerabilities by CVSS

### Integration Points
- **Input from**: LangGraph orchestrator
- **Calls to**: PyRIT, WhiteRabbitNeo LLM
- **Output to**: DOCUMENTATION Agent (new), BLUE Agent
- **Data stored in**: PostgreSQL, QLDB

### Model & Configuration (UPDATED)

#### Model Specifications
- **Model**: WhiteRabbitNeo-7B-v1.5a-GGUF Q4_K_M ⚠️ (CONFIRMED)
- **Quantization**: 4-bit K_M (optimized for speed + accuracy balance)
- **Model Size**: ~4.08 GB (fits in 8GB VRAM)
- **Context Window**: 8192 tokens (can handle large code files)
- **Temperature**: 0.7 (creative exploit generation, not deterministic)
- **Max Tokens**: 2048 (enough for PoC + analysis)
- **Top-p**: 0.9 (nucleus sampling for diverse attack vectors)
- **Top-k**: 40 (prevents too-random outputs)
- **Repeat Penalty**: 1.1 (avoids repetitive exploit suggestions)

#### Why WhiteRabbitNeo for RED Agent?
- ✅ **Specialized for offensive security** (trained on cybersecurity datasets)
- ✅ **Excellent at exploit chain generation** (multi-step attacks)
- ✅ **Strong vulnerability analysis** (understands CWE patterns)
- ✅ **PoC code generation** (produces runnable exploits in Python, Bash, curl)
- ✅ **Adversarial thinking** (thinks like an attacker, not defender)
- ✅ **Fast inference** (~30-40 tokens/sec on GPU, acceptable for real-time scanning)

#### System Prompt Template (UPDATED FOR WhiteRabbitNeo)

```python
"""
You are WhiteRabbitNeo, an elite offensive security AI agent specializing in vulnerability discovery and exploit development.

YOUR MISSION: Analyze code for security vulnerabilities and generate PROOF-OF-CONCEPT exploits that demonstrate real-world attack scenarios.

OPERATIONAL CONTEXT:
- You are the RED agent in an autonomous security pipeline
- Your findings feed into BLUE (defensive AI) for remediation
- You MUST provide runnable, testable PoC code for every vulnerability
- Your confidence scores directly impact fix prioritization

ANALYSIS PROTOCOL:
1. Review scan results from tools (Nuclei, Semgrep, Checkov, CodeQL)
2. Validate findings by analyzing vulnerable code context
3. Generate exploit code that proves the vulnerability is exploitable
4. Rate confidence based on exploit success probability
5. Provide remediation hints for BLUE agent

INPUT FORMAT:
{
  "tool_findings": [
    {
      "tool": "semgrep",
      "rule_id": "python.lang.security.sql-injection",
      "file": "src/app.py",
      "line": 42,
      "code_snippet": "cursor.execute('SELECT * FROM users WHERE id=' + user_id)",
      "severity": "high",
      "cwe": "CWE-89"
    }
  ],
  "code_context": {
    "language": "python",
    "framework": "flask",
    "database": "postgresql",
    "auth_method": "jwt"
  },
  "target_environment": "dev|staging|production"
}

OUTPUT FORMAT (JSON ONLY, NO MARKDOWN):
{
  "vulnerabilities": [
    {
      "id": "RED-<timestamp>-<index>",
      "type": "sql_injection",
      "severity": "critical",
      "cwe": "CWE-89",
      "cvss": 9.8,
      "location": {
        "file": "src/app.py",
        "line": 42,
        "function": "get_user",
        "parameter": "user_id"
      },
      "description": "SQL injection via unsanitized user_id parameter. Attacker can bypass authentication or extract sensitive data.",
      "attack_vector": "network",
      "poc_code": "curl -X GET 'http://localhost:5000/api/user/1%27%20OR%20%271%27=%271%27--'",
      "poc_success_rate": 0.95,
      "remediation_hint": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id=%s', (user_id,))",
      "tools_detected_by": ["semgrep", "codeql"],
      "confidence": 0.95,
      "reasoning": "Direct string concatenation in SQL query with no input validation. Classic SQL injection pattern."
    }
  ]
}

POC CODE REQUIREMENTS:
✅ MUST be runnable (curl command, Python script, or Bash script)
✅ MUST include payload that triggers the vulnerability
✅ MUST work against the digital twin environment
✅ MUST demonstrate actual exploit (not just theoretical)
✅ INCLUDE expected output/response in comments

VULNERABILITY TYPES TO PRIORITIZE:
1. SQL Injection (CWE-89)
2. Remote Code Execution (CWE-78, CWE-94)
3. Cross-Site Scripting (CWE-79)
4. Authentication Bypass (CWE-287)
5. SSRF (CWE-918)
6. Path Traversal (CWE-22)
7. Insecure Deserialization (CWE-502)
8. XXE (CWE-611)

CONFIDENCE SCORING:
- 0.9-1.0: Tool detected + manual code review confirms + PoC works
- 0.7-0.9: Tool detected + code pattern matches known vulnerability
- 0.5-0.7: Tool detected but requires validation
- 0.3-0.5: Potential vulnerability, needs deeper analysis
- <0.3: Likely false positive

CRITICAL RULES:
❌ NO generic descriptions without PoC code
❌ NO unvalidated tool outputs (always analyze code context)
❌ NO overly aggressive exploits (DoS, data destruction in production)
✅ ALL findings MUST be actionable
✅ ALL PoCs MUST be safe to run in digital twin
✅ ALL outputs MUST be valid JSON

THINK LIKE AN ATTACKER:
- How would a real adversary exploit this?
- What's the simplest attack path?
- Can this be chained with other vulnerabilities?
- What's the business impact if exploited?
"""
```

#### Performance Benchmarks (WhiteRabbitNeo-specific)
```yaml
expected_performance:
  inference_speed: 30-40 tokens/sec (GPU)
  scan_duration:
    quick_profile: <60 seconds (2-3 vulnerabilities)
    standard_profile: <300 seconds (10-15 vulnerabilities)
    deep_profile: <900 seconds (30+ vulnerabilities)
  
  memory_usage:
    model_vram: 4.08 GB
    tool_overhead: 2 GB (PyRIT + Docker)
    total_required: 8 GB VRAM minimum
  
  poc_generation_time: 5-10 seconds per vulnerability
```

#### Model Limitations (What WhiteRabbitNeo CAN'T Do)
```
❌ Cannot analyze binaries (ARM/x86 assembly)
❌ Limited mobile app analysis (APK/IPA)
❌ Weak at hardware vulnerabilities (firmware, IoT)
❌ May hallucinate PoCs for complex vulnerabilities
❌ Context window limit (8192 tokens = ~6000 lines of code max)

✅ Excellent at web app vulnerabilities
✅ Strong Python/JavaScript/Java analysis
✅ Great SQL injection/XSS/RCE detection
✅ Good authentication bypass scenarios
```

---

## BLUE AGENT SPECIFICATIONS

### Core Responsibility
**Autonomous fix generation and validation. The BLUE agent is defense. Its job is to GENERATE SAFE, TESTED, EFFECTIVE FIXES.**

### Output Contract (What BLUE Produces)

```json
{
  "fix_id": "string (BLUE-{timestamp}-{vulnerability.id}-{option_number})",
  "vulnerability_id": "RED-{...}",
  "timestamp": "ISO8601",
  "fixes": [
    {
      "option": "number (1, 2, or 3)",
      "description": "string (brief, human-readable fix description)",
      "approach": "string (constraint-based validation|parameterized_queries|...)",
      "code_diff": {
        "file": "string",
        "before": "string (original code snippet)",
        "after": "string (fixed code snippet)",
        "lines_changed": "number"
      },
      "test_code": "string (pytest/jest test verifying fix effectiveness)",
      "safety_gates": {
        "gate_1_input_validation": {"passed": true, "reason": "..."},
        "gate_2_no_new_vulnerabilities": {"passed": true, "reason": "..."},
        "gate_3_backward_compatibility": {"passed": true, "reason": "..."},
        "gate_4_performance": {"passed": true, "reason": "..."},
        "gate_5_test_coverage": {"passed": true, "reason": "..."}
      },
      "confidence": "number (0.0-1.0, overall fix quality)",
      "recommendation": "STRONG_ACCEPT|ACCEPT|WEAK_ACCEPT|REJECT"
    }
  ],
  "selected_fix": "number (1, 2, or 3, index of recommended fix)",
  "statistics": {
    "avg_confidence": "number (0.0-1.0)",
    "all_gates_passed": "boolean"
  }
}
```

### Verification Loop (V1 UPDATE)
- ✅ BLUE generates fix (30-60 seconds per vulnerability)
- ✅ BLUE validates all 5 safety gates locally
- ✅ BLUE passes to RED for verification
- ✅ RED tests fix with original PoC → PoC MUST FAIL (proof vuln is gone)
- ✅ Loop continues until verified ✓
- ⚠️ V1: NO auto-merge, creates PR for human review
- ✅ Data flows: BLUE → RED (verification) → GOVERNANCE → AUDIT

### Key Requirements (NON-NEGOTIABLE)

1. **Safety Gates (5 LAYERS)**
   - Gate 1: Input Validation (all user inputs checked)
   - Gate 2: No New Vulnerabilities (Semgrep scan = ZERO new CWEs)
   - Gate 3: Backward Compatibility (existing tests pass 100%)
   - Gate 4: Performance (<10% overhead acceptable)
   - Gate 5: Test Coverage (>80% required)
   - Gate 5: Test Coverage (>80% required)
   - ⚠️ ALL GATES MUST PASS or confidence ≤ 0.5

2. **Output Consistency**
   - ✅ MUST return ONLY valid JSON
   - ✅ Confidence score reflects actual gate passage

### Model & Configuration
- **Model**: DeepSeek-R1-Distill Qwen 7B Q4_K_M ⚠️ (UPDATE)
- **Temperature**: 0.2 (deterministic fix generation)
- **Max Tokens**: 4000 (increased for chain-of-thought reasoning)
- **Top-p**: 0.85
- **Special Features**: 
  - Built-in chain-of-thought reasoning (shows step-by-step fix logic)
  - Superior at multi-step vulnerability remediation
  - Excellent test case generation

### System Prompt Template (UPDATED)

You are DeepSeek-R1, a world-class security engineer specializing in secure code fixes.

REASONING PROTOCOL:
1. Analyze the vulnerability deeply (think step-by-step)
2. Consider multiple fix approaches
3. Evaluate trade-offs (security vs performance vs maintainability)
4. Select the optimal approach with justification

TASK: Fix this vulnerability with SAFE, TESTED, EFFECTIVE code.

INPUT: 
- Vulnerability details (type, location, CWE, CVSS)
- Vulnerable code snippet
- Programming language and framework

OUTPUT (JSON with EXACTLY 3 fix options + reasoning):
{
  "reasoning": {
    "vulnerability_analysis": "Step-by-step analysis of the vulnerability",
    "fix_approaches_considered": ["Approach 1", "Approach 2", "Approach 3"],
    "trade_offs": "Security vs performance vs complexity analysis",
    "selected_approach": "Why this approach is optimal"
  },
  "fixes": [
    {
      "option": 1,
      "description": "Conservative approach (safest)",
      "code_diff": "...",
      "test_code": "def test_fix(): ...",
      "confidence": 0.92,
      "reasoning": "Why this fix works",
      "safety_gates": { ... }
    },
    // Options 2, 3...
  ]
}

5-LAYER SAFETY GATES (ALL must pass):
1. Input Validation: All inputs validated (whitelist, length, type)
2. No New Vulnerabilities: Semgrep scan finds zero new CWEs
3. Backward Compatibility: Existing tests pass 100%
4. Performance: Overhead <10%
5. Test Coverage: New code coverage >80%

DANGEROUS PATTERNS TO AVOID:
❌ subprocess.call(..., shell=True)
❌ eval(), exec(), __import__()
❌ os.system()
❌ String concatenation in SQL queries
❌ Unescaped user input in HTML

REQUIRED PATTERNS:
✅ Parameterized queries (ORM or prepared statements)
✅ Input validation with regex/type checking
✅ HTML escaping (html.escape(), markupsafe)
✅ Use standard crypto libraries (cryptography.io)
✅ Include test code that verifies fix works

### Integration Points
- **Input from**: RED Agent
- **Calls to**: DeepSeek-R1 LLM, Docker API, Semgrep
- **Output to**: RED Agent (verification), GOVERNANCE Agent
- **Data stored in**: PostgreSQL, QLDB

### Detailed Safety Gates Configuration (UPDATED)

```yaml
# blue_agent_config.yaml (COMPLETE)

model:
  name: "DeepSeek-R1-Distill-Qwen-7B"
  quantization: "Q4_K_M"
  model_path: "/models/deepseek-r1-distill-qwen-7b-q4_k_m.gguf"
  inference_engine: "llama.cpp"
  
  generation_params:
    temperature: 0.2  # Deterministic fix generation
    max_tokens: 4000  # Large for chain-of-thought
    top_p: 0.85
    repeat_penalty: 1.05
    stop_sequences: ["</think>", "END_OF_FIX"]
  
  reasoning:
    extract_think_tags: true  # Parse <think>...</think> blocks
    log_reasoning: true  # Store in QLDB for audit
    include_in_pr: true  # Show reasoning in PR comments

safety_gates:
  gate_1_input_validation:
    method: "static_analysis"
    tools: ["semgrep", "bandit"]  # Python-specific
    rules:
      - "no-eval"
      - "no-exec"
      - "no-shell-true"
    timeout: 30
  
  gate_2_no_new_vulnerabilities:
    method: "differential_semgrep"
    baseline: "original_code"
    comparison: "fixed_code"
    rulesets:
      - "p/security-audit"
      - "p/owasp-top-10"
    acceptable_new_findings: 0  # ZERO tolerance
    timeout: 60
  
  gate_3_backward_compatibility:
    method: "test_execution"
    test_runner: "pytest"  # or jest, go test, etc.
    docker_image: "test-runner:latest"
    resource_limits:
      cpu: "2"
      memory: "4Gi"
    timeout: 300  # 5 minutes for full test suite
    required_pass_rate: 1.0  # 100%
    
    # Handle external dependencies
    services:
      - name: "postgres"
        image: "postgres:15"
        env:
          POSTGRES_DB: "test_db"
      - name: "redis"
        image: "redis:7"
  
  gate_4_performance:
    method: "load_testing"
    tool: "locust"
    test_duration: 60  # seconds
    baseline_rps: 1000  # requests per second
    acceptable_overhead: 0.10  # 10% max
    metrics:
      - "response_time_p95"
      - "requests_per_second"
      - "error_rate"
  
  gate_5_test_coverage:
    method: "coverage_diff"
    tool: "coverage.py"  # or istanbul, jacoco
    baseline: "original_code"
    comparison: "fixed_code"
    required_coverage: 0.80  # 80% minimum
    focus: "new_lines_only"  # Only measure fix coverage

docker_test_environment:
  base_image: "blue-test-env:latest"
  dockerfile: |
    FROM python:3.11-slim
    RUN apt-get update && apt-get install -y git curl
    COPY requirements.txt .
    RUN pip install -r requirements.txt
    WORKDIR /workspace
  
  network: "isolated"
  cleanup_policy: "always"
  max_lifetime: 600  # 10 minutes

verification_with_red:
  enabled: true
  method: "poc_rerun"
  max_attempts: 3
  success_criteria: "poc_must_fail"  # Exploit should be blocked
```

---

## DOCUMENTATION AGENT SPECIFICATIONS (NEW)

### Core Responsibility (V1 NEW)
**Automatic documentation generation in Google Docs for vulnerability findings and remediation plans. Creates live, auto-updating vulnerability reports linked from dashboard.**

### Model & Configuration
- **Model**: Phi-3.5-mini-instruct 3.8B Q6_K ⚠️ (UPDATE)
- **Temperature**: 0.15 (consistent documentation style)
- **Max Tokens**: 4000 (longer reports)
- **Top-p**: 0.9
- **Why Phi-3.5**: 
  - Excellent at technical writing
  - Fast structured output generation
  - Consistent formatting

### System Prompt Template (UPDATED)

You are Phi-3.5, a technical documentation specialist for security reports.

TASK: Create clear, professional Google Docs for security findings.

OUTPUT SECTIONS:
1. EXECUTIVE SUMMARY
   - Total vulnerabilities
   - Severity breakdown (critical/high/medium/low)
   - Overall risk score
   - Time to resolution

2. VULNERABILITY DETAILS (per vulnerability)
   - Type (SQL Injection, XSS, etc.)
   - Location (file:line:function)
   - CWE classification
   - CVSS score with vector string
   - Proof-of-concept code (formatted as code block)
   - Why it's dangerous (business impact)

3. FIX DETAILS (per vulnerability)
   - Approach used (parameterized queries, input validation, etc.)
   - Code changes (before/after diff)
   - Test coverage added
   - Verification results (attack attempts blocked)

4. COMPLIANCE EVIDENCE
   - SOC2 controls addressed
   - ISO27001 controls addressed
   - GDPR Article 32 compliance
   - Immutable audit trail reference

5. RECOMMENDATIONS
   - Additional hardening suggestions
   - Code review priorities
   - Monitoring recommendations

FORMAT:
- Use headers (H1, H2, H3)
- Use code blocks for code snippets
- Use tables for structured data
- Use bullet points for lists
- Include links to audit trail
- Professional, clear, concise writing

### Input Contract (What DOCUMENTATION Receives)

```json
{
  "vulnerabilities": [
    {
      "id": "RED-{...}",
      "type": "string",
      "cwe": "string",
      "cvss": "number",
      "location": {"file": "...", "line": 42},
      "description": "string",
      "poc_code": "string",
      "severity": "critical|high|medium|low"
    }
  ],
  "metadata": {
    "repo_name": "string",
    "repo_url": "string",
    "scan_date": "ISO8601",
    "scan_id": "string",
    "organization": "string"
  },
  "governance_plan": [
    {
      "vulnerability_id": "RED-{...}",
      "priority": 1,
      "estimated_fix_time": "number (minutes)"
    }
  ]
}
```

### Output Contract (What DOCUMENTATION Produces)

```json
{
  "documentation_id": "string (DOC-{timestamp})",
  "timestamp": "ISO8601",
  "google_doc": {
    "doc_id": "string (Google Docs document ID)",
    "doc_url": "string (https://docs.google.com/document/d/{doc_id})",
    "title": "string (Ouroboros Security Report - [Repo Name] - [Date])",
    "permissions": {
      "owner": "service-account@...",
      "viewers": ["security-team@company.com"],
      "editors": []
    },
    "created_at": "ISO8601",
    "last_updated": "ISO8601"
  },
  "sections_generated": [
    "Executive Summary",
    "Vulnerability Details",
    "Remediation Plan",
    "Compliance Impact",
    "Appendix - PoC Code"
  ],
  "content_summary": {
    "total_vulnerabilities": "number",
    "severity_breakdown": {"critical": 2, "high": 5, "medium": 12},
    "risk_score": "number (0-100)"
  },
  "update_frequency": "realtime (as new fixes generated)",
  "status": "created|updated|error"
}
```

### Key Requirements (NON-NEGOTIABLE)

1. **Google Workspace MCP Integration**
   - ✅ MUST authenticate via OAuth (service account or user)
   - ✅ MUST create/update Google Docs using Google Docs API
   - ✅ MUST support live document updates (as RED/BLUE produce new findings)
   - ✅ MUST include sharing permissions (security team read-only)
   - ❌ NO storing credentials in code
   - ❌ NO manual URL sharing (automatic via API)

2. **Document Structure**
   - ✅ Executive Summary (2-3 paragraphs max)
   - ✅ Vulnerability Details (per-vulnerability section)
   - ✅ Remediation Plan (prioritized by GOVERNANCE)
   - ✅ Compliance Impact (SOC2, ISO27001, GDPR, HIPAA)
   - ✅ Appendix - PoC Code (for reference)

3. **Update Behavior (V1)**
   - ✅ Create document on first vulnerability finding
   - ✅ Auto-update document as BLUE generates fixes
   - ✅ Mark sections with [IN PROGRESS], [FIXED], [VERIFIED]
   - ✅ Real-time sync: document reflects live workflow state
   - ⚠️ V1: No manual edits (read-only for team, editable only by agents)

4. **Output Consistency**
   - ✅ MUST return ONLY valid JSON
   - ✅ MUST include valid Google Doc URL
   - ✅ MUST track document permissions
   - ✅ MUST support concurrent updates

### Workflow Integration
- **Input from**: RED Agent (findings), GOVERNANCE Agent (priority plan), BLUE Agent (fixes)
- **Calls to**: Google Docs API (via MCP), Phi-3.5 LLM
- **Output to**: Dashboard (displays doc link), AUDIT Agent
- **Data stored in**: Google Drive, QLDB (audit trail)

### MCP Configuration Example

```python
# Google Workspace MCP connection
from langchain_google_community.tools.google_workspace import GoogleWorkspaceMCP

mcp_config = {
    "type": "google_workspace",
    "credentials_file": "/secrets/google-service-account.json",
    "scopes": [
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive"
    ]
}

mcp = GoogleWorkspaceMCP.from_config(mcp_config)

# Use in DOCUMENTATION Agent
async def create_vulnerability_report(vulns, metadata):
    # Create doc
    doc_id = await mcp.create_document(
        title=f"Ouroboros Report - {metadata['repo_name']} - {metadata['scan_date']}",
        body=generate_report_content(vulns)
    )
    
    # Share with security team
    await mcp.share_document(
        doc_id=doc_id,
        email="security-team@company.com",
        role="reader"
    )
    
    return doc_id
```

### Complete DOCUMENTATION Agent Configuration (UPDATED)

```yaml
# documentation_agent_config.yaml (COMPLETE)

model:
  name: "Phi-3.5-mini-instruct"
  quantization: "Q6_K"
  model_path: "/models/phi-3.5-mini-instruct-q6_k.gguf"
  
  generation_params:
    temperature: 0.15  # Very consistent
    max_tokens: 4000
    top_p: 0.9
    repeat_penalty: 1.05

google_workspace:
  authentication:
    method: "service_account"  # NOT OAuth (for automation)
    credentials_file: "/secrets/google-service-account.json"
    scopes:
      - "https://www.googleapis.com/auth/documents"
      - "https://www.googleapis.com/auth/drive"
      - "https://www.googleapis.com/auth/drive.file"
    
    token_refresh:
      enabled: true
      refresh_before_expiry: 300  # 5 minutes
    
    credential_rotation:
      policy: "quarterly"
      alert_before_expiry: 2592000  # 30 days
  
  mcp_config:
    package: "langchain-google-community"
    version: ">=0.1.0"
    connection_pool_size: 5
    retry_policy:
      max_attempts: 3
      backoff_multiplier: 2
      timeout: 30
  
  rate_limits:
    requests_per_minute: 60  # Google API limit
    documents_per_day: 1000
    updates_per_document_per_minute: 10  # Avoid conflicts
  
  document_updates:
    strategy: "append_only"  # Never overwrite, always append
    concurrency_control:
      method: "optimistic_locking"
      retry_on_conflict: true
      max_retries: 5
    
    versioning:
      enabled: true
      create_revision: true
      revision_comment: "Ouroboros auto-update"

risk_score_calculation:
  method: "weighted_cvss"
  formula: |
    risk_score = (
      (critical_count * 10) +
      (high_count * 7) +
      (medium_count * 4) +
      (low_count * 1)
    ) / total_vulnerabilities * 10
  
  max_score: 100
  thresholds:
    critical: 80  # Red zone
    high: 50
    medium: 20
    low: 0
```

---

## GOVERNANCE AGENT SPECIFICATIONS

### Core Responsibility
**Policy-based risk evaluation and autonomy determination.**

### Input Contract (What GOVERNANCE Receives)

```json
{
  "fix": {
    "fix_id": "BLUE-{...}",
    "vulnerability_id": "RED-{...}",
    "confidence": "number (0.0-1.0)",
    "all_safety_gates_passed": "boolean"
  },
  "vulnerability": {
    "type": "string",
    "cwe": "string",
    "cvss": "number (0.0-10.0)",
    "severity": "critical|high|medium|low"
  },
  "environment": {
    "target": "dev|staging|production",
    "customer_count": "number",
    "data_sensitivity": "public|internal|confidential|pii|pci"
  },
  "policies": {
    "rego_files": ["string (OPA Rego policy code)"],
    "approval_chain": ["on_call_engineer", "security_team"],
    "risk_thresholds": {
      "auto_approve": "number (0-100)",
      "suggest": "number",
      "require": "number",
      "escalate": "number"
    }
  }
}
```

### Output Contract (What GOVERNANCE Produces)

```json
{
  "governance_decision_id": "string (GOV-{timestamp})",
  "timestamp": "ISO8601",
  "fix_id": "BLUE-{...}",
  "decision": {
    "risk_score": "number (0-100)",
    "autonomy_level": "auto_approve|suggest|require|escalate",
    "rationale": "string (why this decision was made)",
    "policy_evaluations": {
      "policy_name": "string",
      "result": "pass|fail",
      "details": "string"
    }
  },
  "approval_workflow": {
    "required_approvers": ["on_call_engineer"],
    "optional_approvers": [],
    "escalation_contact": "security-team@company.com (if escalate)",
    "estimated_approval_time_minutes": "number"
  },
  "constraints": {
    "cannot_deploy_before": "ISO8601 (minimum delay)",
    "cannot_deploy_after": "ISO8601 (window expires)",
    "v1_no_auto_merge": true,
    "requires_pr_review": true
  }
}
```

### Key Requirements (NON-NEGOTIABLE)

1. **V1 Anti-Pattern: NO AUTO-MERGE**
   - ✅ GOVERNANCE may auto-approve fix as SAFE
   - ⚠️ V1: ALL fixes create PR (no auto-merge to main)
   - ✅ PR requires 2x human code review minimum
   - ✅ Only after PR approved does deployment proceed
   - ❌ NEVER deploy without human PR review in V1

2. **Risk-Based Autonomy**
   - Risk score <20: auto_approve (but still needs PR review)
   - Risk score 20-50: require (approval required)
   - Risk score 50-80: escalate (security team review)
   - Risk score >80: escalate critical (CISO approval)

3. **Model Configuration**
   - Model: Phi-3.5-mini-instruct 3.8B Q6_K ⚠️ (UPDATE)
   - Temperature: 0.1 (very deterministic policy evaluation)
   - Max Tokens: 1500
   - Top-p: 0.95
   - Why Phi-3.5: 
     - Microsoft-tuned for instruction following
     - Excellent at structured decision-making
     - Fast inference (50 tokens/sec)
     - Low memory footprint (3.2GB)

### System Prompt Template (UPDATED)

You are Phi-3.5, a security governance policy engine optimized for deterministic decision-making.

TASK: Evaluate vulnerabilities and prioritize fixes using policy-as-code.

INPUT:
- List of vulnerabilities with CVSS scores
- Environment (dev/staging/production)
- Policy rules (OPA Rego)

OUTPUT (JSON):
{
  "prioritized_queue": [
    {
      "vulnerability_id": "RED-...",
      "priority": 1,
      "risk_score": 87,
      "autonomy_level": "require",
      "reasoning": "Critical CVSS + production environment",
      "required_approvers": ["security_team"]
    }
  ]
}

RISK CALCULATION:
risk_score = CVSS × environment_multiplier × exploit_ease

ENVIRONMENT MULTIPLIERS:
- dev: 1.0
- staging: 2.0
- production: 5.0

AUTONOMY LEVELS:
- auto_approve: risk < 20 (V1: NOT USED, all require PR approval)
- suggest: risk 20-50
- require: risk 50-80 (V1: DEFAULT for all)
- escalate: risk > 80

V1 OVERRIDE: All fixes go through PR review (no auto-merge).

### Integration Points
- **Input from**: BLUE Agent (after verification by RED)
- **Calls to**: OPA engine, Phi-3.5 LLM
- **Output to**: PR Creation agent, AUDIT Agent
- **Data stored in**: PostgreSQL, QLDB

### Complete GOVERNANCE Agent Configuration (UPDATED)

```yaml
# governance_agent_config.yaml (COMPLETE)

model:
  name: "Phi-3.5-mini-instruct"
  quantization: "Q6_K"
  
  generation_params:
    temperature: 0.1  # Extremely deterministic
    max_tokens: 1500
    top_p: 0.95

opa_integration:
  engine: "opa"
  version: "0.60.0"
  endpoint: "http://opa-service:8181/v1/data"
  
  policy_loading:
    method: "file_watch"
    policy_dir: "/etc/opa/policies"
    reload_on_change: true
    hot_reload: true  # No restart needed
  
  policy_examples:
    production_critical: |
      package ouroboros.governance
      
      # Production + Critical = ESCALATE
      decision := "escalate" {
        input.environment == "production"
        input.cvss >= 9.0
      }
    
    dev_low_risk: |
      package ouroboros.governance
      
      # Dev + Low CVSS = SUGGEST (but still needs PR review in V1)
      decision := "suggest" {
        input.environment == "dev"
        input.cvss < 4.0
      }

risk_calculation:
  formula: "cvss × env_multiplier × exploit_ease × data_sensitivity"
  
  cvss:
    source: "RED agent output"
    range: [0.0, 10.0]
  
  environment_multipliers:
    dev: 1.0
    staging: 2.0
    production: 5.0
  
  exploit_ease:
    method: "poc_success_rate"  # From RED agent
    mapping:
      "0.9-1.0": 1.0   # Very easy (PoC works 90%+ of time)
      "0.7-0.9": 0.8   # Easy
      "0.5-0.7": 0.6   # Medium
      "0.3-0.5": 0.4   # Hard
      "0.0-0.3": 0.2   # Very hard
  
  data_sensitivity_multipliers:
    public: 1.0
    internal: 1.5
    confidential: 2.0
    pii: 3.0
    pci: 4.0

approval_chain:
  notification_method: "multi_channel"
  
  channels:
    pagerduty:
      api_key_env: "PAGERDUTY_API_KEY"
      escalation_policy: "security-incidents"
      urgency_mapping:
        escalate: "high"
        require: "low"
    
    slack:
      webhook_url_env: "SLACK_WEBHOOK_URL"
      channel: "#security-alerts"
      mention_mapping:
        on_call_engineer: "@oncall-security"
        security_team: "@security-team"
        ciso: "@ciso"
    
    email:
      smtp_server: "smtp.company.com"
      from: "ouroboros@company.com"
      recipients:
        on_call_engineer: "oncall-security@company.com"
        security_team: "security-team@company.com"
        ciso: "ciso@company.com"
  
  approval_sla:
    auto_approve: 0  # Instant (V1: NOT USED)
    suggest: 120  # 2 hours
    require: 240  # 4 hours
    escalate: 60  # 1 hour (urgent)

autonomy_thresholds:
  auto_approve: 20  # risk < 20 (V1: NOT USED, all need PR)
  suggest: 50       # 20 ≤ risk < 50
  require: 80       # 50 ≤ risk < 80
  escalate: 100     # risk ≥ 80
```

---

## AUDIT AGENT SPECIFICATIONS

### Core Responsibility
**Immutable compliance logging and cryptographic proof of all actions.**

### Output Contract (What AUDIT Produces)

```json
{
  "audit_id": "string (AUDIT-{timestamp})",
  "timestamp": "ISO8601",
  "events": [
    {
      "event_type": "red_discovery|blue_generation|blue_verification|governance_decision|pr_created|deployment",
      "entity_id": "RED-{...}|BLUE-{...}|GOV-{...}",
      "details": {...},
      "digital_signature": "string (SHA-256 HMAC)",
      "merkle_hash": "string (for chain verification)"
    }
  ],
  "compliance_mappings": {
    "soc2": ["CC6.1", "CC7.2"],
    "iso27001": ["A.12.2.1", "A.14.2.1"],
    "gdpr": ["Article 32"],
    "hipaa": ["164.312(a)(2)(i)"]
  },
  "ledger_entry": {
    "ledger_id": "string (immudb entry ID)",
    "hash_chain": "verified",
    "tamper_proof": true
  }
}
```

### Key Requirements (NON-NEGOTIABLE)

1. **Immutable Ledger (immudb)**
   - ✅ MUST append to immutable QLDB/immudb ledger
   - ✅ MUST use cryptographic signing (SHA-256 HMAC)
   - ✅ MUST track Merkle root for integrity verification
   - ❌ NO deletion, modification, or backtracking

2. **Compliance Mappings**
   - ✅ MUST map every event to 150+ compliance controls
   - ✅ SOC2 (CC6, CC7), ISO27001 (A.12, A.14), GDPR (Art 32), HIPAA (164.312)
   - ✅ Evidence collection automatic (no manual logs)

3. **Model Configuration**
   - Model: Phi-3.5-mini-instruct 3.8B Q6_K ⚠️ (UPDATE)
   - Temperature: 0.05 (fully deterministic)
   - Max Tokens: 1000
   - Top-p: 0.99
   - Why Phi-3.5: 
     - Extremely consistent output
     - Fast event processing
     - Perfect for structured logging

### System Prompt Template (UPDATED)

You are Phi-3.5, a compliance & audit logging system optimized for deterministic event normalization.

TASK: Normalize security events for immutable logging.

OUTPUT (JSON):
{
  "event_id": "uuid",
  "timestamp": "ISO8601",
  "event_type": "vulnerability_discovered|fix_generated|fix_verified|pr_created",
  "severity": "critical|high|medium|low",
  "entities": {
    "vulnerability": {...},
    "fix": {...},
    "verification": {...}
  },
  "compliance_mappings": {
    "SOC2": ["CC6.1", "CC7.2"],
    "ISO27001": ["12.2.1"],
    "GDPR": ["Article32"],
    "HIPAA": ["§164.308(a)"],
    "PCI_DSS": ["6.5.1"]
  },
  "digital_signature": "sha256-rsa-signature",
  "immutable_proof": "merkle-root-hash"
}

CRITICAL: Every field must be populated. No secrets in logs.

### Integration Points
- **Input from**: All agents (RED, BLUE, GOVERNANCE, DOCUMENTATION)
- **Calls to**: immudb API, Phi-3.5 LLM
- **Output to**: Compliance dashboard, auditor reports
- **Data stored in**: immudb (append-only), PostgreSQL (read replicas)

### Complete AUDIT Agent Configuration (UPDATED)

```yaml
# audit_agent_config.yaml (COMPLETE)

model:
  name: "Phi-3.5-mini-instruct"
  quantization: "Q6_K"
  
  generation_params:
    temperature: 0.05  # Fully deterministic
    max_tokens: 1000
    top_p: 0.99

immudb_connection:
  host: "immudb.ouroboros.svc"
  port: 3322
  database: "ouroboros_audit"
  
  authentication:
    username_env: "IMMUDB_USERNAME"
    password_env: "IMMUDB_PASSWORD"
  
  tls:
    enabled: true
    cert_file: "/certs/immudb-client.crt"
    key_file: "/certs/immudb-client.key"
    ca_file: "/certs/ca.crt"
  
  connection_pool:
    max_connections: 10
    idle_timeout: 300
    max_retries: 3

digital_signature:
  algorithm: "HMAC-SHA256"
  
  key_management:
    provider: "hashicorp_vault"
    vault_addr: "https://vault.company.com"
    key_path: "secret/data/ouroboros/hmac-key"
    
    rotation:
      policy: "quarterly"
      overlap_period: 604800  # 7 days (old + new keys valid)
    
    backup:
      enabled: true
      method: "shamir_secret_sharing"
      threshold: 3
      total_shares: 5
  
  merkle_tree:
    algorithm: "SHA-256"
    batch_size: 1000  # Entries per Merkle tree
    root_storage: "immudb"

compliance_mapping:
  method: "static_table"  # NOT LLM-generated (too critical)
  mapping_file: "/config/compliance_mappings.json"
  
  schema:
    event_type: "red_discovery"
    controls:
      soc2:
        - control_id: "CC6.1"
          description: "Logical and Physical Access Controls"
          evidence_type: "vulnerability_scan"
        - control_id: "CC7.2"
          description: "System Monitoring"
          evidence_type: "automated_detection"
      
      iso27001:
        - control_id: "A.12.2.1"
          description: "Controls Against Malware"
          evidence_type: "code_analysis"
        - control_id: "A.14.2.1"
          description: "Secure Development Policy"
          evidence_type: "automated_remediation"
      
      gdpr:
        - article: "Article 32"
          clause: "1(a)"
          description: "Pseudonymisation and encryption"
          evidence_type: "security_testing"
      
      hipaa:
        - section: "164.312(a)(2)(i)"
          description: "Unique User Identification"
          evidence_type: "authentication_testing"
  
  update_policy:
    method: "version_controlled"
    git_repo: "github.com/company/compliance-mappings"
    auto_pull_interval: 3600  # Every hour

event_schema:
  required_fields:
    - event_id
    - timestamp
    - event_type
    - entity_id
    - severity
    - digital_signature
    - merkle_hash
  
  optional_fields:
    - user_id
    - ip_address
    - user_agent
  
  pii_fields_to_redact:  # CRITICAL: No PII in logs
    - ssn
    - credit_card
    - email
    - phone_number
  
  secret_fields_to_redact:  # CRITICAL: No secrets in logs
    - api_key
    - password
    - token
    - private_key
```

---

## CROSS-AGENT CONTRACTS

### RED → DOCUMENTATION

```
RED output.vulnerabilities → DOCUMENTATION receives
- MUST include all fields (id, type, cwe, cvss, location, description, poc_code)
- DOCUMENTATION creates Google Doc section per vulnerability
- DOCUMENTATION uses poc_code as inline code block
```

### DOCUMENTATION → BLUE

```
DOCUMENTATION tracks fix progress
- As BLUE generates fix: DOCUMENTATION updates document
- Marks section [IN PROGRESS - Generating Fix]
- Marks section [READY FOR REVIEW] once fix complete
```

### BLUE → RED (Verification Loop)

```
BLUE generates fix → RED verifies
- RED.poc_code runs against BLUE.fix
- poc_code MUST FAIL (proof vuln is gone)
- If poc succeeds: confidence = 0.0, fix rejected
- If poc fails: confidence increases, fix approved
```

### GOVERNANCE → PR Creation

```
GOVERNANCE decision → PR Creation Agent
- autonomy_level determines PR template
- risk_score ≥ 50 → adds SECURITY_TEAM as reviewer
- Always requires 2x human review minimum (V1)
- Never auto-merge (V1 constraint)
```

### All → AUDIT

```
Every agent logs to QLDB:
- Event type (red_discovery, blue_generation, etc.)
- Entity ID (RED-..., BLUE-..., GOV-...)
- Digital signature
- Compliance mapping
✓ Immutable trail of entire security workflow
```

---

## VERIFICATION LOOP REQUIREMENTS (V1 UPDATE)

### Complete Loop (New in V1)

```
STEP 1: RED discovers vulnerability
  Input: GitHub repo URL
  Output: RED finds SQL injection at app.py:42
  PoC: curl "http://localhost/api/user/1' OR '1'='1'"
  ✓ Audit logs: RED_DISCOVERY event

STEP 2: DOCUMENTATION creates report
  Input: RED findings
  Output: Google Doc created + shared with security team
  Content: Executive summary + vulnerability details
  ✓ Audit logs: DOCUMENTATION_CREATED event

STEP 3: GOVERNANCE prioritizes
  Input: RED findings + OPA policies
  Output: Priority = 1 (CRITICAL)
  Risk score = 85 (ESCALATE)
  ✓ Audit logs: GOVERNANCE_DECISION event

STEP 4: BLUE generates fixes (3 options)
  Input: SQL injection vulnerability + code context
  Output: Fix option 1 (use parameterized query)
  Confidence: 0.92
  All safety gates: PASSED
  ✓ Audit logs: BLUE_GENERATION event

STEP 5: RED verifies fix
  Input: BLUE fix + original PoC
  Action: Run original PoC against fixed code
  Result: PoC FAILS (vulnerability is gone)
  ✓ Audit logs: VERIFICATION_SUCCESS event

STEP 6: GOVERNANCE approves PR
  Input: Verified fix + governance decision
  Output: Decision = auto_approve (but still needs PR review)
  ✓ Audit logs: GOVERNANCE_APPROVED event

STEP 7: PR Created on GitHub
  Input: BLUE fix
  Output: PR created + assigned to on_call_engineer + security_team
  ✓ Audit logs: PR_CREATED event

STEP 8: Human review & merge (outside Ouroboros)
  Input: PR with automated review comments
  Output: Human approves → PR merged to staging
  ✓ Manual approval (not automated in V1)

STEP 9: DOCUMENTATION updated
  Input: PR merged event
  Output: Google Doc marks vulnerability as [FIXED] + [VERIFIED]
  ✓ Audit logs: DOCUMENTATION_UPDATED event

TOTAL TIME: <2 hours (vs industry 70 days)
APPROVAL: 2x human review (safe for production)
```

### Verification Success Criteria

✅ RED PoC must FAIL after BLUE fix (proof of remediation)
✅ BLUE fix must pass ALL 5 safety gates
✅ No new vulnerabilities introduced
✅ Backward compatibility maintained
✅ Test coverage >80%
✅ Performance overhead <10%
✅ All agents complete cycle <2 hours
✅ Human review completes fix before production deployment

---

## CRITICAL CONSTRAINTS (V1)

```
DO NOT in V1:
❌ Auto-merge fixes to main branch
❌ Deploy without human PR review
❌ Skip Red verification loop
❌ Assume fix is safe without testing
❌ Override safety gates

DO in V1:
✅ Create PR automatically
✅ Assign to human reviewers
✅ Log everything immutably
✅ Require 2x code review
✅ Alert team of high-risk fixes
✅ Provide complete audit trail
```

---

**CRITICAL**: These specifications are LOCKED. No deviations without explicit approval from @security_lead.

**End of File 2: Agent Specifications (V1 Updated - 14 pages)**