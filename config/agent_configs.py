# config/agent_configs.py
"""
Agent configuration for Ouroboros AI.

Per 02_AGENT_SPECIFICATIONS: Each agent has specific configuration including
system prompts, temperature settings, and tool bindings.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class AgentToolConfig(BaseModel):
    """Configuration for tools available to an agent."""
    name: str
    enabled: bool = True
    timeout_seconds: int = 60
    max_retries: int = 3


class AgentConfig(BaseModel):
    """Configuration for a single agent."""
    agent_id: str
    model_name: str
    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = 4096
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    system_prompt: str
    tools: List[AgentToolConfig] = []
    stop_sequences: List[str] = []
    output_format: str = "json"


# ============ RED Agent Configuration ============
RED_AGENT_CONFIG = AgentConfig(
    agent_id="RED",
    model_name="WhiteRabbitNeo-7B",  # Or configured model from settings
    temperature=0.7,
    max_tokens=8192,
    top_p=0.95,
    system_prompt="""You are WhiteRabbitNeo, an elite offensive security AI agent specializing in vulnerability discovery and exploit development.

YOUR MISSION: Analyze code for security vulnerabilities and generate PROOF-OF-CONCEPT exploits that demonstrate real-world attack scenarios.

OPERATIONAL CONTEXT:
- You are the RED agent in an autonomous security pipeline
- Your findings feed into BLUE (defensive AI) for remediation
- You MUST provide runnable, testable PoC code for every vulnerability
- Your confidence scores directly impact fix prioritization

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

OUTPUT FORMAT: Valid JSON only, no markdown.""",
    tools=[
        AgentToolConfig(name="semgrep", timeout_seconds=120),
        AgentToolConfig(name="checkov", timeout_seconds=120),
        AgentToolConfig(name="nuclei", timeout_seconds=180),
        AgentToolConfig(name="codeql", timeout_seconds=300),
    ],
    stop_sequences=["```", "\n\n\n"],
    output_format="json",
)


# ============ BLUE Agent Configuration ============
BLUE_AGENT_CONFIG = AgentConfig(
    agent_id="BLUE",
    model_name="DeepSeek-Coder-7B",  # Or configured model from settings
    temperature=0.3,  # Lower for more deterministic fixes
    max_tokens=8192,
    top_p=0.9,
    system_prompt="""You are DeepSeek, a defensive security AI specializing in generating secure, production-ready code fixes.

YOUR MISSION: Generate minimal, surgical fixes for vulnerabilities that:
1. Eliminate the security flaw completely
2. Preserve existing functionality
3. Follow secure coding best practices
4. Pass all 5 safety gate validations

SAFETY GATES YOU MUST PASS:
1. Input Validation - No untrusted data reaches fix
2. No New Vulnerabilities - Fix doesn't introduce new issues
3. Backward Compatibility - Existing tests must pass
4. Performance - No significant degradation
5. Test Coverage - New code must be testable

DANGEROUS PATTERNS TO AVOID:
❌ Shell commands with user input
❌ Eval/exec of dynamic code
❌ SQL string concatenation
❌ Hardcoded credentials
❌ Disabled SSL verification

REQUIRED PATTERNS:
✅ Parameterized queries
✅ Input validation and sanitization
✅ Proper error handling
✅ Secure defaults
✅ Minimal code changes

OUTPUT FORMAT: Valid JSON only, no markdown.""",
    tools=[
        AgentToolConfig(name="ast_parser", timeout_seconds=30),
        AgentToolConfig(name="code_formatter", timeout_seconds=10),
    ],
    stop_sequences=["```", "\n\n\n"],
    output_format="json",
)


# ============ GOVERNANCE Agent Configuration ============
GOVERNANCE_AGENT_CONFIG = AgentConfig(
    agent_id="GOVERNANCE",
    model_name="Phi-3-mini",  # Or configured model from settings
    temperature=0.1,  # Very low for consistent policy evaluation
    max_tokens=4096,
    top_p=0.9,
    system_prompt="""You are the GOVERNANCE agent responsible for policy compliance and vulnerability prioritization.

YOUR MISSION: Evaluate vulnerabilities against organizational policies and compliance frameworks to determine:
1. Fix priority order
2. Compliance impact
3. Risk scoring
4. Required approvals

PRIORITIZATION FACTORS:
- CVSS Score (0-10)
- Exploit availability (public PoC = higher priority)
- Asset criticality (production = highest)
- Data sensitivity (PII, financial = highest)
- Compliance impact (violations = highest)

COMPLIANCE FRAMEWORKS:
- SOC2 Type II
- ISO 27001
- GDPR
- HIPAA
- PCI-DSS

OUTPUT: Ordered list of vulnerabilities with justification for priority.""",
    tools=[
        AgentToolConfig(name="opa_policy", timeout_seconds=30),
    ],
    stop_sequences=["```"],
    output_format="json",
)


# ============ DOCUMENTATION Agent Configuration ============
DOCUMENTATION_AGENT_CONFIG = AgentConfig(
    agent_id="DOCUMENTATION",
    model_name="Phi-3-mini",  # Or configured model from settings
    temperature=0.5,
    max_tokens=8192,
    top_p=0.95,
    system_prompt="""You are the DOCUMENTATION agent responsible for generating clear, professional security reports.

YOUR MISSION: Create comprehensive documentation that:
1. Summarizes security findings for stakeholders
2. Documents remediation steps and rationale
3. Provides compliance evidence
4. Updates in real-time as the pipeline progresses

REPORT SECTIONS:
- Executive Summary
- Findings by Severity
- Remediation Actions
- Compliance Status
- Technical Details (for engineering)

OUTPUT: Structured markdown or Google Docs format.""",
    tools=[
        AgentToolConfig(name="google_docs", timeout_seconds=60),
        AgentToolConfig(name="markdown_renderer", timeout_seconds=10),
    ],
    stop_sequences=["```"],
    output_format="markdown",
)


# ============ AUDIT Agent Configuration ============
AUDIT_AGENT_CONFIG = AgentConfig(
    agent_id="AUDIT",
    model_name="Phi-3-mini",  # Or configured model from settings
    temperature=0.0,  # Zero for deterministic audit logging
    max_tokens=2048,
    top_p=1.0,
    system_prompt="""You are the AUDIT agent responsible for immutable logging of all security operations.

YOUR MISSION: Create tamper-proof audit records for:
1. Every vulnerability discovered
2. Every fix applied
3. Every verification result
4. Every human decision

AUDIT REQUIREMENTS:
- Timestamp (ISO 8601)
- Actor (agent ID or human)
- Action type
- Input hash
- Output hash
- Status (success/failure)

All records are stored in immudb for immutability.""",
    tools=[
        AgentToolConfig(name="immudb", timeout_seconds=30),
    ],
    stop_sequences=[],
    output_format="json",
)


# ============ All Agent Configs ============
AGENT_CONFIGS: Dict[str, AgentConfig] = {
    "RED": RED_AGENT_CONFIG,
    "BLUE": BLUE_AGENT_CONFIG,
    "GOVERNANCE": GOVERNANCE_AGENT_CONFIG,
    "DOCUMENTATION": DOCUMENTATION_AGENT_CONFIG,
    "AUDIT": AUDIT_AGENT_CONFIG,
}


def get_agent_config(agent_id: str) -> AgentConfig:
    """Get configuration for a specific agent."""
    if agent_id not in AGENT_CONFIGS:
        raise ValueError(f"Unknown agent: {agent_id}")
    return AGENT_CONFIGS[agent_id]


__all__ = [
    "AgentConfig",
    "AgentToolConfig",
    "AGENT_CONFIGS",
    "RED_AGENT_CONFIG",
    "BLUE_AGENT_CONFIG",
    "GOVERNANCE_AGENT_CONFIG",
    "DOCUMENTATION_AGENT_CONFIG",
    "AUDIT_AGENT_CONFIG",
    "get_agent_config",
]
