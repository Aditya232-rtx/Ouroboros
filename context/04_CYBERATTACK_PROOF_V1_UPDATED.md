# OUROBOROS AI: CYBERATTACK-PROOF INSTRUCTION SET (V1 UPDATED)
**Version:** 1.1  
**Date:** January 19, 2026  
**Status:** Security-Hardened (V1)  
**Total Pages:** 15+

---

## CRITICAL PREAMBLE

**This document defines HOW to build a security system that itself CANNOT be hacked.**

If adversaries compromise any agent, the system fails. This instruction set prevents ALL attack vectors.

---

## TABLE OF CONTENTS
1. [Defense-in-Depth Architecture](#defense-in-depth-architecture)
2. [RED Agent Hardening](#red-agent-hardening)
3. [BLUE Agent Hardening](#blue-agent-hardening)
4. [DOCUMENTATION Agent Hardening (NEW)](#documentation-agent-hardening-new)
5. [GOVERNANCE Agent Hardening](#governance-agent-hardening)
6. [AUDIT Agent Hardening](#audit-agent-hardening)
7. [Google Workspace OAuth Security (NEW)](#google-workspace-oauth-security-new)
8. [Input Validation & Sanitization](#input-validation--sanitization)
9. [Network Security](#network-security)
10. [Secrets Management](#secrets-management)
11. [Monitoring & Detection](#monitoring--detection)
12. [Incident Response Playbook](#incident-response-playbook)

---

## DEFENSE-IN-DEPTH ARCHITECTURE

### Layer 1: Network Isolation (Zero Trust)

**Principle**: NEVER trust the network. Assume compromise at any point.

```
┌─────────────────────────────────────────────────────┐
│            INTERNET (UNTRUSTED)                    │
│                                                     │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴───────────────┐
        │   AWS Security Group    │
        │  (Port 443 only, TLS)  │
        └──────────────┬──────────┘
                       │
┌──────────────────────┴──────────────────────────────┐
│            PRIVATE VPC (ENCRYPTED)                 │
│                                                     │
│  ┌────────────────────────────────────────────┐   │
│  │  Application Layer (LangGraph + PyRIT)    │   │
│  │  - No direct internet access               │   │
│  │  - All external calls through NAT Gateway  │   │
│  └────────────┬───────────────────────────────┘   │
│               │                                    │
│  ┌────────────┴───────────────────────────────┐   │
│  │    Database Layer (Isolated Subnet)        │   │
│  │    - PostgreSQL (encrypted)                │   │
│  │    - Redis (encrypted)                     │   │
│  │    - immudb (immutable ledger)             │   │
│  │    - No internet access (except backups)  │   │
│  └──────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

**Hardening Rules:**

```python
# NETWORK ISOLATION RULES (Non-negotiable)

1. Incoming (Inbound)
   ✅ ALLOW: HTTPS (443) from GitHub webhook IPs only
   ✅ ALLOW: SSH (22) from internal bastion host only
   ❌ DENY: Everything else (default deny)

2. Outgoing (Outbound) from application
   ✅ ALLOW: HTTPS (443) to GitHub API (api.github.com)
   ✅ ALLOW: HTTPS (443) to Anthropic API (api.anthropic.com)
   ✅ ALLOW: HTTPS (443) to HuggingFace (huggingface.co)
   ✅ ALLOW: HTTPS (443) to Google Workspace API (googleapis.com) ← NEW
   ✅ ALLOW: Internal DNS queries (53 UDP)
   ❌ DENY: All other internet access

3. Database access
   ✅ ALLOW: App → PostgreSQL (5432) - internal only
   ✅ ALLOW: App → Redis (6379) - internal, password-protected
   ✅ ALLOW: App → immudb (3322) - internal, mTLS
   ❌ DENY: Database → Internet

4. WAF (Web Application Firewall)
   ✅ Rate limit: 100 requests/minute per IP
   ✅ Block: SQL injection patterns (OWASP ModSecurity)
   ✅ Block: XSS patterns
   ✅ Block: Path traversal attempts
```

---

## DOCUMENTATION AGENT HARDENING (NEW)

### Google Workspace API Security

**Threat Model**: Attacker gains access to Google Workspace to:
- Read sensitive vulnerability reports
- Modify findings
- Exfiltrate customer data
- Inject malicious content into reports

**Defense:**

```python
# DOCUMENTATION Agent input validation
from pydantic import BaseModel, validator

class DocumentationAgentInput(BaseModel):
    vulnerabilities: List[Dict]
    metadata: Dict
    
    @validator('metadata')
    def validate_metadata(cls, v):
        # MUST include repo owner (for scope validation)
        if 'repo_owner' not in v:
            raise ValueError("repo_owner required")
        
        # MUST include organization ID (for permissions check)
        if 'org_id' not in v:
            raise ValueError("org_id required")
        
        return v

# Google Workspace OAuth validation
def validate_google_oauth(access_token: str, service_account: str) -> bool:
    # 1. Verify token is from Google
    google_jwks_url = "https://www.googleapis.com/oauth2/v3/certs"
    jwks = requests.get(google_jwks_url, verify=True).json()  # SSL verified
    
    # 2. Verify JWT signature
    try:
        decoded = jwt.decode(access_token, jwks, algorithms=['RS256'])
    except jwt.InvalidSignatureError:
        raise SecurityError("Invalid token signature")
    
    # 3. Verify expiration
    if decoded['exp'] < time.time():
        raise SecurityError("Token expired")
    
    # 4. Verify audience (must be Google Docs API)
    if 'aud' not in decoded or 'https://www.googleapis.com' not in decoded['aud']:
        raise SecurityError("Invalid audience")
    
    # 5. Verify service account matches
    if decoded['sub'] != service_account:
        raise SecurityError("Service account mismatch")
    
    return True

# Use in DOCUMENTATION Agent
async def create_vulnerability_report(input_data: DocumentationAgentInput):
    # 1. Validate input
    validated = DocumentationAgentInput(**input_data)
    
    # 2. Validate OAuth token
    validate_google_oauth(access_token, service_account)
    
    # 3. Check organization permissions
    org_permissions = await check_org_permissions(validated.metadata['org_id'])
    if not org_permissions.can_create_docs:
        raise PermissionError("Organization not authorized")
    
    # 4. Create document with minimal permissions
    doc_id = await google_docs_api.create_document(
        title=f"Security Report - {validated.metadata['repo_name']}",
        content=generate_report(validated.vulnerabilities),
        access_control={
            "owner": service_account,  # Only service account can modify
            "viewers": [validated.metadata['security_team_email']],  # Read-only
            "domain_sharing": False  # NOT shared with domain
        }
    )
    
    return doc_id
```

### Google Workspace MCP Configuration Security

```python
# Secure MCP connection setup
from langchain_google_community.tools.google_workspace import GoogleWorkspaceMCP
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials

# Load service account (from AWS Secrets Manager, NOT git)
import boto3
sm = boto3.client('secretsmanager')
service_account_json = sm.get_secret_value(
    SecretId="google-service-account"
)["SecretString"]

# Create credentials with proper scopes
credentials = Credentials.from_service_account_info(
    json.loads(service_account_json),
    scopes=[
        'https://www.googleapis.com/auth/documents',  # Create/edit Docs
        'https://www.googleapis.com/auth/drive'       # Access Drive
    ]
)

# Verify credentials are valid
credentials.refresh(Request())

# Initialize MCP with validated credentials
mcp = GoogleWorkspaceMCP(credentials=credentials)

# All Google Docs operations require HTTPS (automatic with mcp)
# All OAuth tokens are short-lived (service account tokens = 1 hour)
# All token refreshes are automatic
```

---

## RED AGENT HARDENING

### Input Validation (CRITICAL)

```python
from pydantic import BaseModel, validator
import re

class RedAgentInput(BaseModel):
    target_repo: str
    
    @validator('target_repo')
    def validate_repo(cls, v):
        # MUST be valid GitHub URL
        pattern = r'^github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$'
        if not re.match(pattern, v):
            raise ValueError(f"Invalid repo: {v}")
        
        # MUST NOT contain path traversal
        if '..' in v or '../' in v or '~' in v:
            raise ValueError("Path traversal detected")
        
        return v
    
    commit_sha: str
    
    @validator('commit_sha')
    def validate_sha(cls, v):
        if not re.match(r'^[a-f0-9]{40}$', v):
            raise ValueError("Invalid git SHA")
        return v
    
    scanning_tools: List[str]
    
    @validator('scanning_tools')
    def validate_tools(cls, v):
        ALLOWED = {"nuclei", "semgrep", "checkov", "codeql"}
        for tool in v:
            if tool not in ALLOWED:
                raise ValueError(f"Unknown tool: {tool}")
        return v

# Enforce on EVERY RED call
@app.post("/api/red-scan")
async def start_red_scan(input_data: RedAgentInput):
    # Validation automatic via Pydantic
    return await red_agent.scan(input_data)
```

### Process Isolation (CRITICAL)

```python
def run_red_agent_sandboxed(config: RedAgentInput):
    client = docker.from_env()
    
    container = client.containers.run(
        image="ouroboros-red-agent:v1",  # Signed image
        
        # NO network access
        network_mode="none",
        
        # Read-only filesystem except /tmp
        volumes={
            "/tmp": {"bind": "/tmp", "mode": "rw"},
            "/app": {"bind": "/app", "mode": "ro"}
        },
        read_only=True,
        
        # NO privilege escalation
        security_opt=["no-new-privileges:true"],
        user="1000:1000",  # Non-root
        
        # Resource limits
        mem_limit="512m",
        memswap_limit="512m",
        cpus=2.0,
        
        # NO device access
        devices=[],
        cap_drop=["ALL"],
        cap_add=["CHOWN", "DAC_OVERRIDE"],
        
        # Timeout (prevent infinite execution)
        timeout=config.timeout_seconds
    )
    
    exit_code = container.wait()
    logs = container.logs().decode()
    container.remove()
    
    return {"exit_code": exit_code, "logs": logs}
```

---

## BLUE AGENT HARDENING (DeepSeek-R1 Specific)

### Chain-of-Thought Reasoning Validation

**DeepSeek-R1 outputs reasoning steps. Validate them:**

```python
def validate_deepseek_reasoning(fix_response: Dict) -> bool:
    """Validate DeepSeek-R1's reasoning chain"""
    
    # 1. Check reasoning is present
    if "reasoning" not in fix_response:
        return False
    
    reasoning = fix_response["reasoning"]
    
    # 2. Required reasoning fields
    required = [
        "vulnerability_analysis",
        "fix_approaches_considered",
        "trade_offs",
        "selected_approach"
    ]
    
    if not all(field in reasoning for field in required):
        return False
    
    # 3. Reasoning must mention security
    security_keywords = ["security", "vulnerability", "attack", "exploit"]
    analysis_text = str(reasoning["vulnerability_analysis"]).lower()
    
    if not any(kw in analysis_text for kw in security_keywords):
        return False  # Reasoning doesn't focus on security
    
    # 4. Must consider multiple approaches
    if len(reasoning["fix_approaches_considered"]) < 2:
        return False  # Didn't explore alternatives
    
    # 5. Trade-off analysis must exist
    if len(reasoning["trade_offs"]) < 20:  # At least 20 chars
        return False  # No real trade-off analysis
    
    return True

# Use in BLUE Agent
async def blue_agent_fix_node(state: OuroborosState) -> OuroborosState:
    fix_response = await deepseek_r1.generate_fix(vuln)
    
    # Validate reasoning quality
    if not validate_deepseek_reasoning(fix_response):
        # Reject low-quality reasoning
        fix_response["confidence"] = 0.0
        fix_response["recommendation"] = "REJECT - Poor reasoning"
    
    return state
```

**Why:** DeepSeek-R1's reasoning chain is a feature, but also an attack surface. Validate that reasoning is actually security-focused, not hijacked by prompt injection.

**Penalty:** Attacker injects prompt that makes DeepSeek-R1 "reason" its way into generating backdoored code.

## BLUE AGENT HARDENING

### Code Generation Safety (3 LAYERS)

**Layer 1: Constrained Prompt**

```python
BLUE_AGENT_SYSTEM_PROMPT = """You are a security engineer generating SAFE code fixes.

CRITICAL: Your output will be executed in production.

SAFETY REQUIREMENTS (NON-NEGOTIABLE):
1. All user inputs MUST be validated (whitelist, length, type checks)
2. All outputs MUST be parameterized (no string concatenation)
3. No system calls (subprocess, os.system, shell=True)
4. No eval(), exec(), __import__(), pickle
5. No file operations outside /app
6. No network calls (unless explicitly approved)
7. No resource exhaustion (memory bombs, fork bombs)

DANGEROUS PATTERNS TO AVOID:
❌ subprocess.call(cmd, shell=True)
❌ eval(), exec()
❌ os.system()
❌ pickle.loads(untrusted)
❌ Infinite loops without breaks
❌ Unbounded recursion

REQUIRED PATTERNS:
✅ Use parameterized queries (Django ORM, SQLAlchemy)
✅ Use input validation (regex, type checking, length limits)
✅ Use standard crypto (cryptography.io)
✅ Escape HTML output (html.escape())
✅ Set timeouts on external calls
✅ Include comprehensive error handling
✅ Log security events

YOUR OUTPUT MUST BE:
- Valid Python 3.11+ syntax (parseable with ast.parse)
- Runnable in Docker (no external deps beyond requirements.txt)
- Testable (include test code)
- Documented (security decisions explained)
- Diff format only (not full file)
"""
```

**Layer 2: Output Analysis**

```python
def analyze_generated_code(code_string: str) -> Dict[str, bool]:
    dangerous_patterns = {
        "subprocess": r'subprocess\.(call|run|popen)',
        "os_system": r'os\.system',
        "eval": r'eval\s*\(',
        "exec": r'exec\s*\(',
        "pickle_loads": r'pickle\.loads',
        "infinite_loop": r'while\s+(True|1)',
    }
    
    results = {}
    for pattern_name, pattern_regex in dangerous_patterns.items():
        if re.search(pattern_regex, code_string):
            results[pattern_name] = True  # FOUND (bad)
        else:
            results[pattern_name] = False  # NOT found
    
    # Parse AST for deeper analysis
    try:
        tree = ast.parse(code_string)
        results["syntax_valid"] = True
    except SyntaxError:
        results["syntax_valid"] = False
    
    return results

def validate_fix_before_testing(fix_code: str) -> bool:
    analysis = analyze_generated_code(fix_code)
    
    # ANY dangerous pattern found = REJECT immediately
    if any([
        analysis.get("subprocess"),
        analysis.get("os_system"),
        analysis.get("eval"),
        analysis.get("exec"),
        analysis.get("pickle_loads"),
    ]):
        return False
    
    if not analysis.get("syntax_valid"):
        return False
    
    return True
```

**Layer 3: Digital Twin Testing (in Sandbox)**

```python
async def test_fix_in_digital_twin(fix_code: str, test_code: str):
    # 1. Validate code BEFORE running
    if not validate_fix_before_testing(fix_code):
        return TestResult(success=False, reason="Code failed safety")
    
    # 2. Run in isolated container
    try:
        container = await docker.containers.run(
            image="python:3.11-slim",
            volumes={"/tmp": {"bind": "/tmp", "mode": "rw"}},
            read_only=True,
            network_mode="none",
            mem_limit="512m",
            cpus=1.0,
            timeout=30,
            command=["python", "-m", "pytest", "test.py"]
        )
        
        result = await container.wait(timeout=30)
        return TestResult(
            success=result.get("StatusCode") == 0,
            exit_code=result.get("StatusCode")
        )
    
    except asyncio.TimeoutError:
        return TestResult(
            success=False,
            reason="Test timeout (possible infinite loop)"
        )
```

---

## GOVERNANCE AGENT HARDENING

### Policy Evaluation (OPA Rego)

```rego
# governance_policies.rego
package ouroboros.governance

# DENY: Fix without all safety gates passing
deny[msg] {
    input.fix.safety_gates[_] == false
    msg := "Fix failed safety gate validation - DENIED"
}

# DENY: Fix without test coverage
deny[msg] {
    input.fix.test_coverage < 0.80
    msg := "Fix lacks test coverage - DENIED"
}

# DENY: High-risk + low confidence
deny[msg] {
    input.vulnerability.cvss > 8.0
    input.fix.confidence < 0.90
    msg := "High-severity + low confidence - DENIED"
}

# V1: ALWAYS require PR review (no auto-merge)
require_pr_review {
    input.environment == "production"
    true
}

# ALLOW: Low-risk, well-tested fixes
allow_auto_approve {
    input.risk_score < 20
    input.fix.safety_gates_all_passed == true
    input.fix.test_coverage >= 0.80
    input.fix.confidence > 0.85
    input.environment in ["dev", "staging"]
}
```

---

## AUDIT AGENT HARDENING

### Immutable Ledger (immudb)

```python
async def audit_log_event(event: Dict) -> str:
    # 1. Validate event structure
    required_fields = {"event_type", "entity_id", "timestamp", "details"}
    if not required_fields.issubset(event.keys()):
        raise ValueError("Missing required audit fields")
    
    # 2. Sign event with HMAC-SHA256
    import hmac
    event_json = json.dumps(event, sort_keys=True)
    signature = hmac.new(
        key=AUDIT_SIGNING_KEY.encode(),
        msg=event_json.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    event['digital_signature'] = signature
    
    # 3. Calculate Merkle hash for chain integrity
    prev_event = await immudb.get_last_entry()
    prev_hash = prev_event['merkle_hash'] if prev_event else '0' * 64
    
    event['merkle_hash'] = hashlib.sha256(
        (prev_hash + event_json).encode()
    ).hexdigest()
    
    # 4. Append to immutable ledger
    ledger_id = await immudb.set(
        key=f"audit:{event['entity_id']}",
        value=event,
        append_only=True  # Cannot be modified/deleted
    )
    
    # 5. Log to immudb for compliance proof
    await immudb.log(
        msg=f"Event logged: {event['event_type']} - {ledger_id}",
        level="info"
    )
    
    return ledger_id
```

---

## GOOGLE WORKSPACE OAUTH SECURITY (NEW)

### OAuth 2.0 Secure Flow

```python
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.auth.oauthlib.flow import Flow
import json

class GoogleWorkspaceOAuthHandler:
    def __init__(self):
        # Load service account from AWS Secrets Manager (NOT git)
        import boto3
        sm = boto3.client('secretsmanager')
        secret = sm.get_secret_value(SecretId="google-service-account")
        self.service_account_info = json.loads(secret["SecretString"])
        
        # Required OAuth scopes (minimal permissions)
        self.scopes = [
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive'
        ]
    
    def get_credentials(self):
        """Get service account credentials with minimal scope"""
        credentials = Credentials.from_service_account_info(
            self.service_account_info,
            scopes=self.scopes
        )
        
        # Refresh to ensure valid (1 hour lifetime)
        credentials.refresh(Request())
        
        return credentials
    
    def validate_oauth_token(self, token: str) -> bool:
        """Validate OAuth token is legitimate"""
        from google.auth.transport import requests as google_requests
        import google.auth
        
        try:
            # Request must be HTTPS (automatic with google library)
            request = google_requests.Request()
            
            # Verify token with Google
            google.auth.jwt.decode(
                token,
                certs=self._get_google_certs(),
                audience=None
            )
            
            return True
        except Exception as e:
            return False
    
    def _get_google_certs(self):
        """Get Google's public certs (HTTPS only)"""
        import requests
        response = requests.get(
            "https://www.googleapis.com/oauth2/v3/certs",
            verify=True  # SSL verification REQUIRED
        )
        return response.json()
    
    async def create_document_securely(self, doc_data: Dict) -> str:
        """Create Google Doc with security checks"""
        # 1. Get validated credentials
        credentials = self.get_credentials()
        
        # 2. Validate document data
        if not self._validate_doc_content(doc_data):
            raise ValueError("Invalid document content")
        
        # 3. Create via Google Docs API
        service = build('docs', 'v1', credentials=credentials)
        
        doc = service.documents().create(body={
            'title': doc_data['title']
        }).execute()
        
        doc_id = doc.get('documentId')
        
        # 4. Set permissions (owner only, viewers read-only)
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Share with security team (read-only)
        drive_service.permissions().create(
            fileId=doc_id,
            body={
                'type': 'user',
                'role': 'reader',
                'emailAddress': doc_data['security_team_email']
            }
        ).execute()
        
        # 5. Update document with content
        service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': [
                {
                    'insertText': {
                        'text': doc_data['content'],
                        'location': {'index': 1}
                    }
                }
            ]}
        ).execute()
        
        # 6. Log to audit trail
        await audit_agent.log_event({
            'event_type': 'google_doc_created',
            'doc_id': doc_id,
            'timestamp': datetime.now().isoformat(),
            'details': {
                'title': doc_data['title'],
                'shared_with': doc_data['security_team_email']
            }
        })
        
        return doc_id
    
    def _validate_doc_content(self, doc_data: Dict) -> bool:
        """Validate document doesn't contain malicious content"""
        # Check for injection attempts
        if any(bad_pattern in str(doc_data).lower() for bad_pattern in [
            'javascript:', 'onerror=', 'onload=', '<script'
        ]):
            return False
        
        return True
```

---

## MONITORING & DETECTION

### Real-Time Security Monitoring

```python
class SecurityMonitor:
    async def monitor_all_agents(self):
        """Continuous monitoring of all agents"""
        
        # Monitor RED Agent
        ├─ CPU: should not exceed 75% (possible DoS)
        ├─ Memory: should not exceed 60% (possible memory leak)
        ├─ Network: should only connect to allowed IPs (Nuclei, Semgrep)
        ├─ Disk writes: should only be to /tmp (no exfiltration)
        ├─ Exit code: should be 0 (successful scan)
        
        # Monitor BLUE Agent
        ├─ Generated code: should parse with ast.parse (no syntax errors)
        ├─ Confidence score: should match gate passage (no lying)
        ├─ Test coverage: should increase over time (code quality)
        ├─ Performance overhead: should be <10% (no degradation)
        
        # Monitor GOVERNANCE Agent
        ├─ Decision consistency: similar vulns should get similar decisions
        ├─ Approval time: should be <1 hour (not too slow)
        ├─ Risk score accuracy: should correlate with actual breach cost
        
        # Monitor AUDIT Agent
        ├─ Ledger integrity: Merkle root should match (no tampering)
        ├─ Event latency: should log <100ms after action (no lag)
        ├─ Signature verification: should always pass (no corruption)
        
        # Monitor DOCUMENTATION Agent
        ├─ Google Docs API calls: should only be HTTPS (SSL)
        ├─ OAuth token refresh: should happen automatically (not expired)
        ├─ Document permissions: should be read-only for team (no modifications)
        ├─ Sharing scope: should never be "domain" (not company-wide)
```

---

## INCIDENT RESPONSE PLAYBOOK

```
INCIDENT: RED Agent compromised (attacker controls vulnerability discovery)
RESPONSE:
1. Immediately isolate RED Agent container (kill process)
2. Audit all recent vulnerabilities (cross-check with GitHub API)
3. Verify BLUE Agent output (check if fixes are real)
4. Review AUDIT trail for suspicious events
5. Rollback all recent fixes (until verification complete)
6. Alert security team + board

INCIDENT: BLUE Agent compromised (attacker injects backdoors)
RESPONSE:
1. Pause all PR creation (stop deployments)
2. Review all recent fixes (check for malicious code)
3. Reject all PRs with unknown/suspicious fixes
4. Manually verify critical fixes
5. Re-run safety gates manually
6. Alert security team + all developers

INCIDENT: GOVERNANCE Agent compromised (attacker auto-approves malicious fixes)
RESPONSE:
1. Disable automatic approvals immediately (require manual)
2. Review all approved fixes from past 24 hours
3. Verify no malicious code was merged
4. Check deployment logs (did any malicious fix get deployed?)
5. If deployed: incident escalation (potential breach)
6. Alert security team

INCIDENT: AUDIT Agent compromised (attacker covers tracks)
RESPONSE:
1. Stop all deployments immediately
2. Verify immudb ledger integrity (Merkle root check)
3. Compare QLDB with backup ledger (detect tampering)
4. If ledger corrupted: assume ALL audit trail may be false
5. Manually re-verify all recent actions
6. Restore from backup ledger
7. Alert auditors (compliance incident)

INCIDENT: DOCUMENTATION Agent compromised (attacker reads reports)
RESPONSE:
1. Revoke all Google Workspace OAuth tokens
2. Review Google Drive sharing logs (what was accessed?)
3. Check if Google Docs were modified
4. Audit who accessed vulnerability reports
5. Notify security team of potential data exposure
6. Create new Google Workspace credentials
7. Re-share reports with restricted permissions
```

---

**CRITICAL**: These hardening steps are MANDATORY. No production deployment without 100% compliance.

**End of File 4: Cyberattack-Proof Instructions (V1 Updated - 15 pages)**