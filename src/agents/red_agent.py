"""
Ouroboros AI - RED Agent
Vulnerability discovery using WhiteRabbitNeo-7B and PyRIT tool orchestration
"""

import logging
import json
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_community.llms import LlamaCpp

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.models import get_model

logger = logging.getLogger(__name__)


class VulnerabilityLocation(BaseModel):
    """Location of a vulnerability"""
    file: str
    line: int
    function: str = ""
    parameter: str = ""


class Vulnerability(BaseModel):
    """Individual vulnerability found by RED Agent"""
    id: str
    type: str
    severity: str  # critical|high|medium|low
    cwe: str
    cvss: float
    location: VulnerabilityLocation
    description: str
    attack_vector: str  # network|local|adjacent|physical
    poc_code: str
    poc_success_rate: float
    remediation_hint: str
    tools_detected_by: List[str]
    confidence: float
    reasoning: str = ""


class REDAgentInput(AgentInput):
    """Input schema for RED Agent"""
    repo_url: str
    commit_sha: str = Field(default="HEAD")
    branch: str = Field(default="main")
    scan_profile: str = Field(default="standard")  # quick|standard|deep
    timeout_seconds: int = Field(default=300)


class REDAgentOutput(AgentOutput):
    """Output schema for RED Agent"""
    scan_id: str
    vulnerabilities: List[Vulnerability]
    statistics: Dict[str, Any]
    scan_complete: bool


class REDAgent(BaseAgent):
    """
    RED Agent - Offensive security specialist
    
    Uses WhiteRabbitNeo-7B for vulnerability discovery and PoC generation
    Orchestrates Nuclei, Semgrep, Checkov, CodeQL via PyRIT
    """
    
    def __init__(self):
        """Initialize RED Agent with WhiteRabbitNeo model"""
        model = get_model("red")
        super().__init__(model=model, agent_id="RED")
        
        # System prompt for WhiteRabbitNeo
        self.system_prompt = """You are WhiteRabbitNeo, an elite offensive security AI agent specializing in vulnerability discovery and exploit development.

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
- What's the business impact if exploited?"""
    
    def validate_input(self, input_data: Dict[str, Any]) -> REDAgentInput:
        """Validate RED Agent input"""
        return REDAgentInput(**input_data)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute RED Agent vulnerability discovery
        
        Steps:
        1. Run security scanning tools via PyRIT
        2. Analyze results with WhiteRabbitNeo
        3. Generate PoC exploits
        4. Filter for high confidence (>0.85)
        """
        scan_id = f"SCAN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.logger.info(f"Starting scan {scan_id} for {input_data['repo_url']}")
        
        try:
            # Step 1: Run security scanning tools
            self.logger.info("Running security scanning tools...")
            tool_findings = await self._run_security_tools(input_data)
            
            # Step 2: Analyze with WhiteRabbitNeo
            self.logger.info("Analyzing findings with WhiteRabbitNeo...")
            vulnerabilities = await self._analyze_with_llm(tool_findings, input_data)
            
            # Step 3: Filter for high confidence only
            high_confidence_vulns = [
                v for v in vulnerabilities 
                if v.confidence >= 0.85
            ]
            
            self.logger.info(
                f"Found {len(vulnerabilities)} potential vulnerabilities, "
                f"{len(high_confidence_vulns)} high confidence"
            )
            
            # Calculate statistics
            statistics = self._calculate_statistics(high_confidence_vulns)
            
            return {
                "scan_id": scan_id,
                "vulnerabilities": [v.model_dump() for v in high_confidence_vulns],
                "statistics": statistics,
                "scan_complete": True
            }
            
        except Exception as e:
            self.logger.error(f"RED Agent execution failed: {e}", exc_info=True)
            return {
                "scan_id": scan_id,
                "vulnerabilities": [],
                "statistics": {"error": str(e)},
                "scan_complete": False
            }
    
    async def _run_security_tools(self, input_data: Dict[str, Any]) -> List[Dict]:
        """
        Run security scanning tools via PyRIT orchestrator.
        
        Integrates Nuclei, Semgrep, Checkov for comprehensive scanning.
        Per 02_AGENT_SPECIFICATIONS: Must use actual tools, not mocks.
        """
        try:
            from src.tools.pyrit_orchestrator import PyRITOrchestrator
            from src.integrations.github_api import github_client
            from pathlib import Path
            import tempfile
            
            self.logger.info("Cloning repository for scanning...")
            
            # Clone repository to temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_path = github_client.clone_repository(
                    repo_url=input_data['repo_url'],
                    branch=input_data.get('branch', 'main'),
                    target_dir=Path(temp_dir)
                )
                
                self.logger.info(f"Repository cloned to {repo_path}")
                
                # Initialize PyRIT orchestrator
                orchestrator = PyRITOrchestrator()
                
                # Determine tools based on scan profile
                scan_profile = input_data.get('scan_profile', 'standard')
                tools = self._get_tools_for_profile(scan_profile)
                
                self.logger.info(f"Running {scan_profile} scan with tools: {tools}")
                
                # Run security scan
                findings = await orchestrator.run_scan(
                    target_path=str(repo_path),
                    tools=tools
                )
                
                self.logger.info(f"Scan complete: {len(findings)} findings from tools")
                
                return findings
                
        except Exception as e:
            self.logger.error(f"Security tool execution failed: {e}", exc_info=True)
            # Return empty findings on error, don't crash
            return []
    
    def _get_tools_for_profile(self, profile: str) -> List[str]:
        """Determine which tools to run based on scan profile"""
        profiles = {
            "quick": ["semgrep"],
            "standard": ["semgrep", "checkov"],
            "deep": ["semgrep", "checkov", "nuclei"]
        }
        return profiles.get(profile, ["semgrep", "checkov"])
    
    async def _analyze_with_llm(
        self, 
        tool_findings: List[Dict], 
        context: Dict[str, Any]
    ) -> List[Vulnerability]:
        """
        Analyze tool findings with WhiteRabbitNeo to:
        1. Validate vulnerabilities
        2. Generate PoC exploits
        3. Calculate confidence scores
        """
        if not tool_findings:
            self.logger.info("No tool findings to analyze")
            return []
        
        # Construct prompt with tool findings
        prompt = f"""{self.system_prompt}

TOOL FINDINGS:
{json.dumps(tool_findings, indent=2)}

CODE CONTEXT:
Repository: {context.get('repo_url', 'unknown')}
Branch: {context.get('branch', 'main')}

Analyze these findings and output a JSON response with your vulnerability assessment."""
        
        try:
            # Call WhiteRabbitNeo
            response = self._call_llm(prompt)
            
            # Parse JSON response
            result = self._parse_json_response(response)
            
            # Convert to Vulnerability objects
            vulnerabilities = []
            for i, vuln_data in enumerate(result.get("vulnerabilities", [])):
                try:
                    # Add ID if not present
                    if "id" not in vuln_data:
                        vuln_data["id"] = f"RED-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i+1}"
                    
                    vuln = Vulnerability(**vuln_data)
                    vulnerabilities.append(vuln)
                except Exception as e:
                    self.logger.error(f"Failed to parse vulnerability {i+1}: {e}")
                    continue
            
            return vulnerabilities
            
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            return []
    
    def _calculate_statistics(self, vulnerabilities: List[Vulnerability]) -> Dict[str, Any]:
        """Calculate statistics from vulnerabilities"""
        by_severity = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for vuln in vulnerabilities:
            by_severity[vuln.severity] = by_severity.get(vuln.severity, 0) + 1
        
        return {
            "total_vulnerabilities": len(vulnerabilities),
            "by_severity": by_severity,
            "avg_confidence": sum(v.confidence for v in vulnerabilities) / len(vulnerabilities) if vulnerabilities else 0.0,
            "avg_cvss": sum(v.cvss for v in vulnerabilities) / len(vulnerabilities) if vulnerabilities else 0.0
        }
    
    def format_output(self, result: Dict[str, Any]) -> REDAgentOutput:
        """Format RED Agent output"""
        return REDAgentOutput(
            agent_id=self.agent_id,
            timestamp=datetime.now().isoformat(),
            status="success" if result.get("scan_complete") else "error",
            scan_id=result["scan_id"],
            vulnerabilities=[Vulnerability(**v) for v in result["vulnerabilities"]],
            statistics=result["statistics"],
            scan_complete=result["scan_complete"]
        )
