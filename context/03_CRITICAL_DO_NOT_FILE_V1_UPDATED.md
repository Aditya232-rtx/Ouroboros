# OUROBOROS AI: CRITICAL DO-NOT FILE (V1 UPDATED)
**Version:** 1.1  
**Date:** January 19, 2026  
**Status:** Safety Critical (V1)  
**Total Pages:** 16+

---

## FOREWORD: CRITICAL SECURITY MANDATE

**THIS FILE CONTAINS HARD STOPS. FAILURE TO FOLLOW THESE RULES WILL RESULT IN:**
- ❌ Deploying unfixed vulnerabilities to production
- ❌ Corrupting immutable audit trails
- ❌ Compliance violation (SOC2, ISO27001, PCI-DSS failures)
- ❌ Unauthorized autonomous code execution
- ❌ Destruction of competitive advantage

**If ANY item in this file is violated, STOP IMMEDIATELY and escalate to @security_lead.**

---

## TABLE OF CONTENTS
1. [Security Do-Nots (Production Killer)](#security-do-nots)
2. [LangGraph Do-Nots (Orchestration Killer)](#langgraph-do-nots)
3. [Agent Do-Nots (Output Killer)](#agent-do-nots)
4. [Data Do-Nots (Audit Killer)](#data-do-nots)
5. [V1 Do-Nots (Verification Killer)](#v1-do-nots-verification-killer)
6. [Deployment Do-Nots (Reliability Killer)](#deployment-do-nots)
7. [Model Do-Nots (Accuracy Killer)](#model-do-nots)

---

## SECURITY DO-NOTS (PRODUCTION KILLER)

### DO NOT: Deploy Without 3-Layer Safety Gate Validation

**❌ FORBIDDEN:**
```python
# WRONG - Deploying fix without validation
if fix.confidence > 0.7:
    deploy_to_production(fix)  # INSTANT DISASTER
```

**✅ REQUIRED:**
```python
# CORRECT - All 5 gates must pass
if (fix.gate_1_input_validation.passed and
    fix.gate_2_no_new_vulnerabilities.passed and
    fix.gate_3_backward_compatibility.passed and
    fix.gate_4_performance.passed and
    fix.gate_5_test_coverage.passed):
    
    # Only then proceed
    pass
else:
    fix.confidence = 0.0
    fix.recommendation = "REJECT"
    # NO DEPLOYMENT
```

**Why:** Without validation, you deploy code that INTRODUCES vulnerabilities.

**Penalty:** Loss of customer trust, regulatory audit failure, attacker exploitation.

---

### DO NOT: Execute Generated Code Without Sandboxing

**❌ FORBIDDEN:**
```python
# WRONG - Executing generated fix code directly
exec(generated_fix_code)  # INSTANT SYSTEM COMPROMISE
```

**✅ REQUIRED:**
```python
# CORRECT - Execute ONLY in Docker container with resource limits
import docker
container = docker.from_env().containers.run(
    image="python:3.11-slim",
    command=["python", "-c", generated_fix_code],
    volumes={"/tmp": {"bind": "/tmp", "mode": "rw"}},
    read_only=True,
    network_disabled=True,
    mem_limit="512m",
    cpus=2.0,
    timeout=300
)
```

**Why:** Generated code could contain malicious patterns. LLMs can be manipulated by prompt injection.

**Penalty:** System compromise, attacker backdoor, infrastructure destroyed.

---

### DO NOT: Skip Audit Logging

**❌ FORBIDDEN:**
```python
# WRONG - No audit trail
for fix in fixes:
    deploy(fix)
    # Forgot to log
```

**✅ REQUIRED:**
```python
# CORRECT - EVERY action logged immutably
for fix in fixes:
    audit_id = await audit_agent.log_event({
        "type": "fix_deployed",
        "fix_id": fix.fix_id,
        "timestamp": now(),
        "digital_signature": sign(event)
    })
    
    # ONLY AFTER successful audit logging
    deploy(fix)
```

**Why:** Without immutable audit trail, compliance audits fail. Auditors need proof.

**Penalty:** SOC2 audit failure, €20M GDPR fine, startup death.

---

### DO NOT: Store Credentials in Code/Git

**❌ FORBIDDEN:**
```python
GITHUB_TOKEN = "ghp_xyz789..."
ANTHROPIC_API_KEY = "sk-proj-abc123..."
```

**✅ REQUIRED:**
```python
# Use environment variables + secrets manager
import os
from boto3 import client as boto_client

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
sm = boto_client('secretsmanager')
API_KEY = sm.get_secret_value(SecretId="anthropic-key")["SecretString"]
```

**Why:** Git history is FOREVER. Once committed, credentials are compromised forever.

**Penalty:** Attacker steals API keys, massive billing abuse, reputation destroyed.

---

### DO NOT: Disable SSL/TLS Verification

**❌ FORBIDDEN:**
```python
import requests
response = requests.get(url, verify=False)  # COMPROMISE
```

**✅ REQUIRED:**
```python
response = requests.get(url, verify=True)  # SSL verification ALWAYS enabled
```

**Why:** Disabling SSL = MITM attack possible. Attacker intercepts API calls.

**Penalty:** Code intercept, credentials stolen, entire product reversed.

---

## LANGGRAPH DO-NOTS (ORCHESTRATION KILLER)

### DO NOT: Create Circular Dependencies in Graph

**❌ FORBIDDEN:**
```python
workflow.add_edge("red_agent", "blue_agent")
workflow.add_edge("blue_agent", "governance_agent")
workflow.add_edge("governance_agent", "red_agent")  # CYCLE = INFINITE LOOP
```

**✅ REQUIRED:**
```python
# Acyclic DAG (Directed Acyclic Graph)
workflow.add_edge("red_agent", "documentation_agent")
workflow.add_edge("documentation_agent", "blue_agent")
workflow.add_edge("blue_agent", "red_agent_verify")  # Verification loop (controlled)
workflow.add_edge("red_agent_verify", "governance_agent")
workflow.add_edge("governance_agent", END)
```

**Why:** Circular edges = infinite execution. System hangs forever.

**Penalty:** Vulnerabilities never get fixed, customers hacked.

---

### DO NOT: Lose State Between Agents

**❌ FORBIDDEN:**
```python
@workflow.add_node("red_agent")
def red_agent(state):
    state["vulnerabilities"] = find_vulns()
    return {}  # LOST STATE!
```

**✅ REQUIRED:**
```python
@workflow.add_node("red_agent")
def red_agent(state: AgentState) -> AgentState:
    state["vulnerabilities"] = find_vulns()
    return state  # STATE PRESERVED
```

**Why:** State = execution context. Losing it = losing vulnerability data.

**Penalty:** Next agent gets no input, vulnerability not fixed, customer hacked.

---

### DO NOT: Skip Error Handling in Edges

**❌ FORBIDDEN:**
```python
workflow.add_edge("red_agent", "blue_agent")
# If RED fails? Blue gets no input. System crashes.
```

**✅ REQUIRED:**
```python
def route_to_blue(state: AgentState) -> str:
    if "error" in state and state["error"]:
        return "error_recovery"
    if not state["vulnerabilities"]:
        return "red_agent_retry"
    return "blue_agent"

workflow.add_conditional_edge("red_agent", route_to_blue)
workflow.add_node("error_recovery", error_handler)
```

**Why:** Network fails, rate limits happen, timeouts occur. Without error handling = silent failure.

**Penalty:** Agent fails silently, workflow stops, vulnerabilities accumulate unfixed.

---

## AGENT DO-NOTS (OUTPUT KILLER)

### DO NOT: Return Non-JSON Output

**❌ FORBIDDEN:**
```python
def red_agent():
    return "Found SQL injection at line 42"  # NOT JSON
```

**✅ REQUIRED:**
```python
def red_agent():
    return {
        "vulnerabilities": [
            {
                "type": "sql_injection",
                "location": {"file": "app.py", "line": 42},
                "confidence": 0.95
            }
        ]
    }
```

**Why:** Next agent expects JSON. String output = parsing fails.

**Penalty:** Next agent crashes, fix never generated, vulnerability unfixed.

---

### DO NOT: Include Hallucinations in Output

**❌ FORBIDDEN:**
```python
{
    "vulnerabilities": [
        {
            "type": "sql_injection",
            "location": "somewhere in the database",  # VAGUE = HALLUCINATION
            "poc_code": "select * from users"  # NOT ACTUAL PoC
        }
    ]
}
```

**✅ REQUIRED:**
```python
{
    "vulnerabilities": [
        {
            "type": "sql_injection",
            "location": {"file": "app.py", "line": 42, "function": "get_user"},
            "poc_code": "GET /api/user/1' OR '1'='1' returns entire table",
            "confidence": 0.95
        }
    ]
}
```

**Why:** Hallucinations = false positives. Developers lose trust.

**Penalty:** System stops being used, real vulnerabilities missed.

---

### DO NOT: Skip Confidence Scores

**❌ FORBIDDEN:**
```python
{
    "vulnerabilities": [
        {
            "type": "xss",
            "location": "...",
            "poc_code": "..."
            # Missing confidence!
        }
    ]
}
```

**✅ REQUIRED:**
```python
{
    "vulnerabilities": [
        {
            "type": "xss",
            "location": "...",
            "poc_code": "...",
            "confidence": 0.92  # Critical for risk scoring
        }
    ]
}
```

**Why:** GOVERNANCE uses confidence for risk calculation. No confidence = broken autonomy.

**Penalty:** All fixes require human approval (slow), system doesn't save time.

---

## DATA DO-NOTS (AUDIT KILLER)

### DO NOT: Create Audit Entries Without Digital Signatures

**❌ FORBIDDEN:**
```python
# WRONG - Not tamper-proof
audit_entry = {
    "event": "fix_deployed",
    "timestamp": "...",
    "fix_id": "..."
    # Missing signature!
}
immudb.set("audit_entry", audit_entry)  # COMPLIANCE FAIL
```

**✅ REQUIRED:**
```python
# CORRECT - Cryptographically signed
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

audit_entry = {
    "event": "fix_deployed",
    "timestamp": "...",
    "fix_id": "..."
}

entry_json = json.dumps(audit_entry, sort_keys=True)
signature = private_key.sign(
    entry_json.encode(),
    padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
    hashes.SHA256()
)

audit_entry["digital_signature"] = signature.hex()
immudb.set("audit_entry", audit_entry)  # ✓ Tamper-proof
```

**Why:** Auditors verify if logs are tamper-proof. Without signature = no proof.

**Penalty:** SOC2 audit failure, auditors don't trust logs.

---

### DO NOT: Store Secrets in Audit Trail

**❌ FORBIDDEN:**
```python
# WRONG - Secrets leaked forever
audit_entry = {
    "event": "fix_deployed",
    "github_token": "ghp_xyz789...",  # SECRET LEAKED
    "api_key": "sk-proj-..."  # SECRET LEAKED
}
immudb.set("audit_entry", audit_entry)  # Immutable = forever compromised
```

**✅ REQUIRED:**
```python
# CORRECT - Only metadata, not secrets
audit_entry = {
    "event": "fix_deployed",
    "actor_id": "user_12345",  # Not the secret
    "secret_reference": "github_token_v1",  # Reference only
    "timestamp": "..."
}
immudb.set("audit_entry", audit_entry)  # ✓ Safe
```

**Why:** Audit trail is immutable. If secrets leaked, they're FOREVER compromised.

**Penalty:** All credentials compromised, attacker has full system access.

---

## V1 DO-NOTS (VERIFICATION KILLER)

### DO NOT: Auto-Merge Fixes in V1

**❌ FORBIDDEN (V1 ONLY):**
```python
# WRONG - Auto-merging in V1
if fix.all_gates_passed and fix.confidence > 0.9:
    github.merge_pr(pr_number)  # INSTANT DISASTER IN V1
```

**✅ REQUIRED (V1):**
```python
# CORRECT - Create PR for human review
if fix.all_gates_passed:
    pr = github.create_pull_request(
        title=f"Security Fix: {fix.vulnerability_type}",
        body=generate_pr_description(fix),
        reviewers=["on_call_engineer", "security_team"]
    )
    # ⚠️ STOP HERE - Humans must review and merge
    # NO auto-merge in V1
```

**Why:** V1 is MVP. Humans must review every fix before production deployment.

**Penalty:** Bad fix deployed, production broken, customers compromised.

---

### DO NOT: Skip RED Verification Loop in V1

**❌ FORBIDDEN:**
```python
# WRONG - No verification
if blue_fix.all_gates_passed:
    governance_approve(blue_fix)  # Trust blind
```

**✅ REQUIRED:**
```python
# CORRECT - RED must verify fix works
red_verification = await red_agent.verify_fix(
    original_poc=red_finding.poc_code,
    fixed_code=blue_fix.code_diff.after
)

if red_verification.poc_fails:  # Proof vuln is gone
    governance_approve(blue_fix)
else:
    blue_fix.confidence = 0.0
    blue_fix.recommendation = "REJECT"
```

**Why:** Verification loop = proof that fix actually works. Can't skip.

**Penalty:** Deploy broken fix, vulnerability still exists, attacker exploits immediately.

---

### DO NOT: Deploy Without PR Review in V1

**❌ FORBIDDEN:**
```python
# WRONG - No human eyes on code
governance.approve_fix(fix)
deploy_to_production(fix)
```

**✅ REQUIRED:**
```python
# CORRECT - 2x human code review minimum
pr = create_pr(fix)
await pr.require_approvals(min=2)
await pr.wait_for_approvals(timeout=1hour)

# Only then:
deploy_to_production(fix)
```

**Why:** V1 is beta. Humans must understand and approve every change.

**Penalty:** Deploy untested/unreviewed code, production crashes.

---

## DEPLOYMENT DO-NOTS (RELIABILITY KILLER)

### DO NOT: Deploy Without Rollback Plan

**❌ FORBIDDEN:**
```python
deploy_to_production(fix)  # No rollback plan
```

**✅ REQUIRED:**
```python
# CORRECT - Always have rollback ready
rollback_version = get_current_version()
deploy_to_staging(fix)
await verify_staging_health(timeout=5min)

# Only then deploy to production with rollback ready
deploy_to_production(fix, rollback_plan=rollback_version)
```

**Why:** Production has 1000x users. Need rollback if something breaks.

**Penalty:** Production downtime, SLA breach, legal liability.

---

## MODEL DO-NOTS (ACCURACY KILLER)

### DO NOT: Use High Temperature for Security Tasks

**❌ FORBIDDEN:**
```python
response = model.generate(
    prompt=security_prompt,
    temperature=0.9  # Random, creative responses
)
```

**✅ REQUIRED:**
```python
response = model.generate(
    prompt=security_prompt,
    temperature=0.1 or 0.2  # Deterministic, consistent
)
```

**Why:** Security = deterministic. Randomness = unpredictable fixes.

**Penalty:** Inconsistent fix quality, hallucinations, false confidence.

---

### DO NOT: Skip Fine-Tuning on Security Data

**❌ FORBIDDEN:**
```python
# Using base model without security training
model = load_model("qwen-2.5-7b")  # Generic model
red_agent.model = model
```

**✅ REQUIRED:**
```python
# Fine-tuned on security data
model = load_model("qwen-2.5-7b")
model = finetune(model, dataset="security_vulnerabilities", epochs=3)
red_agent.model = model
```

**Why:** Generic models don't understand security context. Need domain-specific training.

**Penalty:** Low accuracy, false positives, missed real vulnerabilities.

---

## CRITICAL SUMMARY (V1)

```
ABSOLUTE HARD STOPS:
❌ Never auto-merge in V1
❌ Never skip RED verification
❌ Never deploy without PR review (2x minimum)
❌ Never deploy without audit logging
❌ Never execute code without sandboxing
❌ Never store secrets in code
❌ Never skip safety gates
❌ Never lose state between agents

ALWAYS REQUIRED:
✅ All 5 safety gates passing
✅ RED PoC fails after BLUE fix (proof)
✅ Digital signatures on all audit entries
✅ 2x human code review minimum
✅ Complete audit trail to immudb
✅ Immutable compliance mapping
✅ Google Docs report for findings
✅ <2 hour end-to-end cycle
```

---

**CRITICAL**: These do-nots are LOCKED. Violation = immediate security incident.

**End of File 3: Critical Do-Not File (V1 Updated - 16 pages)**

### DO NOT: Use Wrong Model for Agent Role

**❌ FORBIDDEN:**
```python
# WRONG - Using same model for all agents
red_agent.model = "qwen-2.5-7b"
blue_agent.model = "qwen-2.5-7b"  # Should be DeepSeek-R1!
governance_agent.model = "qwen-2.5-7b"  # Should be Phi-3.5!
```

**✅ REQUIRED:**
```python
# CORRECT - Specialized models per agent
red_agent.model = "whiterabbitneo-7b-q4"  # Security-specialized
blue_agent.model = "deepseek-r1-distill-7b-q4"  # Reasoning-optimized
governance_agent.model = "phi-3.5-mini-q6"  # Instruction-following
documentation_agent.model = "phi-3.5-mini-q6"  # Technical writing
audit_agent.model = "phi-3.5-mini-q6"  # Deterministic logging
```

**Why:** Each model is optimized for specific tasks. DeepSeek-R1 has built-in chain-of-thought for complex reasoning (critical for BLUE fixes). Phi-3.5 is instruction-tuned for deterministic outputs (critical for GOVERNANCE/AUDIT).

**Penalty:** Wrong model = lower fix quality, inconsistent decisions, audit log corruption.