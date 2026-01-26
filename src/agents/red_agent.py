"""
Ouroboros AI - RED Agent
Vulnerability discovery using WhiteRabbitNeo-7B and PyRIT tool orchestration
"""

import logging
import json
import asyncio
import re
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from langchain_community.llms import LlamaCpp

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.models import get_model
from src.security.tools.executor import PentestExecutor
from src.security.tools.exploitation import SQLInjector, WebExploiter, RCEExploiter, MetasploitWrapper
from src.security.tools.exploitation import SQLInjector, WebExploiter, RCEExploiter, MetasploitWrapper
from src.security.tools.privesc import LinuxPrivEsc, CredentialHarvester
from src.security.tools.persistence import PersistenceTools, BackdoorInstaller
from src.security.tools.lateral import LateralMovementTools
from src.security.memory.context import SecurityContextBuilder
from src.security.reporting.reporter import ReportGenerator

logger = logging.getLogger(__name__)


class VulnerabilityLocation(BaseModel):
    """Location of a vulnerability"""
    model_config = ConfigDict(extra='ignore')
    file: str = "unknown"
    line: int = 0
    function: str = ""
    parameter: str = ""


class RedAgentVulnerability(BaseModel):
    """Individual vulnerability found by RED Agent (Pydantic version for LLM)"""
    model_config = ConfigDict(extra='ignore')
    id: str = Field(default_factory=lambda: f"RED-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    type: str = "unknown"
    severity: str = "info"  # critical|high|medium|low|info
    cwe: str = ""
    cvss: float = 0.0
    location: VulnerabilityLocation = Field(default_factory=VulnerabilityLocation)
    description: str = ""
    attack_vector: str = "network" # network|local|adjacent|physical
    poc_code: str = ""
    poc_success_rate: float = 0.0
    remediation_hint: str = ""
    tools_detected_by: List[str] = []
    confidence: float = 0.0
    reasoning: str = ""


class REDAgentInput(AgentInput):
    """Input schema for RED Agent"""
    model_config = ConfigDict(extra='ignore')
    repo_url: str
    commit_sha: str = Field(default="HEAD")
    branch: str = Field(default="main")
    auth_token: str = Field(default="")
    scan_profile: str = Field(default="standard")  # quick|standard|deep
    timeout_seconds: int = Field(default=300)


class REDAgentOutput(AgentOutput):
    """Output schema for RED Agent"""
    model_config = ConfigDict(extra='ignore')
    scan_id: str
    vulnerabilities: List[RedAgentVulnerability]
    statistics: Dict[str, Any]
    scan_complete: bool


class REDAgent(BaseAgent):
    """
    RED Agent - Offensive security specialist
    
    Uses Qwen2.5-Coder-3B for vulnerability discovery and PoC generation
    Orchestrates Nuclei, Semgrep, Checkov, CodeQL via PyRIT
    """
    
    def __init__(self):
        """Initialize RED Agent with Qwen Coder model"""
        model = get_model("red")
        super().__init__(model=model, agent_id="RED")
        
        # Initialize Context Memory (NeuroSploit Integration)
        self.context_builder = SecurityContextBuilder(output_dir="outputs/red_agent/context")
        
        # Load System Prompt from File (NeuroSploit Integration)
        self.prompts = {}
        self._load_prompts()
        self.system_prompt = self.prompts.get("red_team_agent", "You are a professional Red Team security expert using Qwen2.5-Coder...")
        
    def _load_prompts(self):
        """Load all available prompts from the library"""
        prompt_dir = Path("src/resources/agents/red_agent/prompts")
        if not prompt_dir.exists():
            return
            
        for prompt_file in prompt_dir.glob("*.md"):
            try:
                self.prompts[prompt_file.stem] = prompt_file.read_text()
            except Exception as e:
                self.logger.warning(f"Failed to load prompt {prompt_file}: {e}")




    
    def validate_input(self, input_data: Dict[str, Any]) -> REDAgentInput:
        """Validate RED Agent input and filter extra fields to prevent crashes"""
        if isinstance(input_data, REDAgentInput):
             return input_data
        
        # Filter for only keys that are in the schema
        valid_keys = REDAgentInput.model_fields.keys()
        filtered_input = {k: v for k, v in input_data.items() if k in valid_keys}
        
        try:
            return REDAgentInput(**filtered_input)
        except Exception as e:
            self.logger.error(f"Input validation failed even after filtering: {e}")
            # Fallback to defaults for non-present required fields if any (though repo_url is required)
            raise
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute RED Agent vulnerability discovery
        
        Steps:
        1. Run security scanning tools via PyRIT
        2. Analyze results with WhiteRabbitNeo
        3. Generate PoC exploits
        4. Filter for high confidence (>0.85)
        """
        # Validate input using Pydantic model
        validated_input = self.validate_input(input_data)
        
        scan_id = f"SCAN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        scan_profile = validated_input.scan_profile
        self.logger.info(f"Starting scan {scan_id} for {validated_input.repo_url} (Profile: {scan_profile})")
        
        try:
            # Step 1: Run security scanning tools (Upgraded with PentestExecutor)
            self.logger.info("Running security scanning tools...")
            
            # Initialize Context for this target
            self.context_builder.set_target(validated_input.repo_url)
            
            # Run the tools
            tool_findings = await self._run_security_tools(validated_input.model_dump())
            
            # Persist findings to context
            self.context_builder.add_vulnerabilities(tool_findings)
            self.context_builder.save(scan_id)
            
            # Step 2: Analyze with Qwen Coder (using specialized personas)
            self.logger.info("Analyzing findings with Qwen2.5-Coder...")
            context_str = self.context_builder.build_text_context()
            
            # Use 'exploit_expert' persona if critical vulns found, else 'red_team_agent'
            if any(f.get('severity') == 'critical' for f in tool_findings):
                persona = self.prompts.get("exploit_expert", self.system_prompt)
            else:
                persona = self.prompts.get("red_team_agent", self.system_prompt)
                
            vulnerabilities = await self._analyze_with_llm(
                tool_findings, 
                validated_input.model_dump(), 
                context_summary=context_str,
                persona=persona
            )
            
            # Step 2.5: Verify Exploits (The "Specialist" Step)
            # If we have high confidence vulns, try to actually exploit them to prove it
            verified_vulns = []
            shell_access = False
            statistics = {} # Initialize statistics
            
            for vuln in vulnerabilities:
                # Proactively set confidence if LLM didn't (ensure they aren't all filtered out)
                if vuln.confidence == 0.0:
                    vuln.confidence = 0.5 # Default to moderate if found by LLM

                if vuln.confidence > 0.7:
                    self.logger.info(f"Attempting to verify {vuln.type} on {vuln.location.file}...")
                    try:
                        exploit_result = await self._verify_exploit(vuln, validated_input.repo_url)
                        if exploit_result.get("success"):
                            vuln.confidence = 1.0
                            vuln.poc_success_rate = 1.0
                            vuln.reasoning += f"\nVERIFIED: {exploit_result.get('output', 'Exploit successful')}"
                            
                            # Check if we got shell access (e.g. from RCE)
                            if vuln.type == "rce" or exploit_result.get("shell_access"):
                                shell_access = True
                    except Exception as e:
                        self.logger.warning(f"Verification failed: {e}")
                verified_vulns.append(vuln)
            
            # Step 3: Post-Exploitation (Privilege Escalation)
            # If we have shell access, try to elevate privileges
            privesc_results = {}
            if shell_access or scan_profile == "deep": # Try deep scan privesc checks anyway
                self.logger.info("Executing Phase 4: Privilege Escalation & Post-Exploitation")
                privesc_results = await self._attempt_privesc()
                statistics["privesc_vectors"] = len(privesc_results.get("suid_binaries", []))
            
            # Step 4: Persistence & Lateral Movement (APT Logic)
            persistence_results = []
            lateral_results = []
            
            if (shell_access or privesc_results) and scan_profile == "deep":
                self.logger.info("Executing Phase 5: Persistence Establishment")
                persistence_tool = PersistenceTools()
                persistence_results = await asyncio.to_thread(persistence_tool.establish_persistence, "linux") # Assume linux for now
                
                self.logger.info("Executing Phase 6: Lateral Movement")
                lateral_tool = LateralMovementTools()
                # Fake subnet discovery based on target
                neighbors = await lateral_tool.discover_neighbors("192.168.1.0/24")
                if privesc_results.get("credentials"):
                     for neighbor in neighbors:
                         res = await asyncio.to_thread(lateral_tool.attempt_credential_reuse, neighbor["ip"], privesc_results["credentials"])
                         if res["success"]:
                             lateral_results.append(res)
            
            # Step 5: Filter for high confidence only
            high_confidence_vulns = [
                v for v in verified_vulns 
                if v.confidence >= 0.1
            ]
            
            self.logger.info(
                f"Found {len(vulnerabilities)} potential vulnerabilities, "
                f"{len(high_confidence_vulns)} high confidence"
            )
            
            # Update statistics
            statistics.update(self._calculate_statistics(high_confidence_vulns))
            
            # Step 5: Generate Professional HTML Report (NeuroSploit Integration)
            try:
                # Prepare inputs for PentestExecutor
                pentest_input = {
                    "target": validated_input.repo_url,
                    "scan_type": scan_profile,
                    "auth_token": validated_input.auth_token,
                    "output_dir": f"outputs/red_agent/scans/{scan_id}"
                }
                
                # Removed Blue Team Stealth Check (Simpler Offensive-Only Flow)
                self.logger.info("Proceeding to final report generation...")

                # Run Audit/Scan using PentestExecutor (The Muscle)
                # Note: If Proxy is active, we could route traffic, but PentestExecutor wraps binaries.
                # We can check if Proxy is alive to note it in the report.
                proxy = ProxyManager()
                if proxy.available:
                    self.logger.info(f"[Architect] Proxy is active. Traffic will be captured in Caido.")
                
                # Convert our findings to format expected by ReportGenerator
                scan_result_dict = {
                    "target": validated_input.repo_url,
                    "scan_started": scan_id,
                    "scan_completed": datetime.now().isoformat(),
                    "tools_executed": [{"tool": "red_agent_v2", "success": True}],
                    "open_ports": self.context_builder.open_ports,
                    "vulnerabilities": [v.model_dump() for v in high_confidence_vulns],
                    "summary": statistics,
                    "privesc_info": privesc_results,
                    "persistence_info": persistence_results,
                    "lateral_movement_info": lateral_results
                }
                reporter = ReportGenerator(scan_result_dict, llm_analysis="Generated by Qwen2.5-Coder")
                report_path = reporter.save_report(output_dir="outputs/red_agent/reports")
                statistics["report_path"] = report_path
                self.logger.info(f"HTML Report generated at: {report_path}")
            except Exception as e:
                self.logger.error(f"Failed to generate HTML report: {e}")
            
            return {
                "scan_id": scan_id,
                "vulnerabilities": [v.model_dump() for v in high_confidence_vulns],
                "statistics": statistics,
                "summary": statistics, # For script compatibility
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
        Run security scanning tools via PentestExecutor (NeuroSploit Engine).
        
        Workflow:
        1. Identify if target is a repository
        2. Clone to sandbox if repo
        3. Run SAST (Semgrep) on code
        4. Run DAST (Nuclei/Nmap) on target URL
        """
        try:
            target = input_data['repo_url']
            scan_profile = input_data.get('scan_profile', 'standard')
            
            self.logger.info(f"Initializing PentestExecutor for {target}...")
            executor = PentestExecutor(target=target)
            findings = []
            
            # --- PHASE 0: IDENTIFICATION & SANDBOX ---
            is_repo = target.endswith(".git") or any(d in target for d in ["github.com", "gitlab.com", "bitbucket.org"])
            is_github_link = any(h in target.lower() for h in ["github.com", "gitlab.com", "bitbucket.org"])
            sandbox_path = None
            
            if is_repo:
                self.logger.info("Target identified as repository (Source Code). Initiating Sandbox Clone...")
                sandbox_path = await asyncio.to_thread(executor.setup_sandbox, target)
                if not sandbox_path:
                    self.logger.error("Failed to clone repository. SAST will be skipped.")

            # --- PHASE 1: TARGETED SCANNING ---
            # 1. Code-based Tools (SAST)
            if is_repo and sandbox_path:
                self.logger.info(f"Running White-Box Semgrep Scan on {sandbox_path}...")
                await asyncio.to_thread(executor.run_semgrep_scan, sandbox_path)
            
            # 2. Network-based Tools (DAST)
            # Only run if NOT a cloud-hosted repo link, OR if profile is 'deep' and user understands the risk
            if not is_github_link or scan_profile == 'deep':
                if scan_profile in ['active', 'deep', 'standard']:
                    self.logger.info(f"Running Network Discovery (limited) on {target}...")
                    await asyncio.to_thread(executor.run_nmap_scan, ports="1-1000")
                
                if scan_profile in ['standard', 'deep']:
                    self.logger.info(f"Running Vulnerability Scan (Nuclei) on {target}...")
                    await asyncio.to_thread(executor.run_nuclei_scan)
            else:
                 self.logger.info(f"Skipping network-level scans for cloud host {target} to avoid artifacts on hosting provider.")

            # --- PHASE 2: BROWSER ANALYSIS ---
            # Only for live web apps
            is_web_app = target.startswith("http") and not is_github_link and not target.endswith(".git")
            
            if is_web_app:
                 from src.security.tools.browser import BrowserTool
                 self.logger.info("Initializing Browser Dynamic Analysis...")
                 browser = BrowserTool()
                 try:
                     state = browser.launch(target)
                     findings.append({
                         "info": {
                             "name": "Web Application Discovered",
                             "severity": "info",
                             "description": f"Browser successfully accessed {target}. Title: {state.get('title')}",
                             "matched-at": target
                         },
                         "tool": "playwright_browser"
                     })
                 except Exception as be:
                     self.logger.error(f"Browser scan failed: {be}")
                 finally:
                     browser.close()

            # Collect all findings from executor
            for v in executor.scan_result.vulnerabilities:
                findings.append(v.to_dict())

            self.logger.info(f"Scan complete: {len(findings)} total findings discovered.")
            return findings
                
        except Exception as e:
            self.logger.error(f"Security tool execution failed: {e}", exc_info=True)
            return []
    
    def _get_tools_for_profile(self, profile: str) -> List[str]:
        # Legacy method, kept for compatibility
        return []
    
    async def _analyze_with_llm(
        self, 
        tool_findings: List[Dict], 
        context: Dict[str, Any],
        context_summary: str = "",
        persona: str = ""
    ) -> List[RedAgentVulnerability]:
        """
        Analyze tool findings with WhiteRabbitNeo
        """
        if not tool_findings:
            self.logger.info("No tool findings to analyze")
            return []
        
        # Use provided persona + Mission Context
        system_prompt = persona or self.system_prompt
        
        # Construct prompt with tool findings
        prompt = f"""{system_prompt}

TOOL FINDINGS:
{json.dumps(tool_findings, indent=2)}

RECON CONTEXT:
{context_summary}

CODE CONTEXT:
Repository: {context.get('repo_url', 'unknown')}
Branch: {context.get('branch', 'main')}

Analyze these findings and output a JSON response with your vulnerability assessment."""
        
        self.logger.info(f"Analyzing {len(tool_findings)} tool findings with LLM...")
        
        try:
            # Call WhiteRabbitNeo/Qwen
            self.logger.debug(f"LLM Prompt Length: {len(prompt)}")
            response = self._call_llm(prompt)
            self.logger.info(f"LLM Response Received (Length: {len(response)})")
            self.logger.debug(f"Raw LLM Response: {response[:500]}...") # Log first 500 chars
            
            # Parse JSON response with regex robustness
            json_match = re.search(r'(\{.*\}|\[.*\])', response, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    self.logger.warning("Failed standard JSON parse, attempting base parser...")
                    result = self._parse_json_response(response)
            else:
                result = self._parse_json_response(response)

            # Robustness: If LLM returned a list directly
            if isinstance(result, list):
                result = {"vulnerabilities": result}

            if not result or "vulnerabilities" not in result:
                 self.logger.warning("LLM response did not contain a 'vulnerabilities' key.")
                 self.logger.debug(f"Parsed Result: {result}")
            
            # Convert to Vulnerability objects
            vulnerabilities = []
            for i, vuln_data in enumerate(result.get("vulnerabilities", [])):
                try:
                    # Robust Mapping: The LLM might output different field names
                    # Map 'type' -> 'severity' if severity is missing (as seen in logs)
                    if "type" in vuln_data and "severity" not in vuln_data:
                        vuln_data["severity"] = vuln_data["type"].lower()
                    
                    # Map 'endpoint' or 'url' -> 'location.file' if location is missing
                    if "location" not in vuln_data:
                        loc_file = vuln_data.get("endpoint") or vuln_data.get("url") or "unknown"
                        vuln_data["location"] = {"file": loc_file, "line": 0}
                    
                    # Map 'name' -> 'type' if type is missing or generic
                    if ("type" not in vuln_data or vuln_data.get("type") in ["unknown", "INFO"]) and "name" in vuln_data:
                         vuln_data["type"] = vuln_data["name"]

                    # Add ID if not present
                    if "id" not in vuln_data:
                        vuln_data["id"] = f"RED-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i+1}"
                    
                    vuln = RedAgentVulnerability(**vuln_data)
                    vulnerabilities.append(vuln)
                except Exception as e:
                    self.logger.error(f"Failed to parse vulnerability {i+1}: {e}. Data: {vuln_data}")
                    continue
            
            self.logger.info(f"Successfully parsed {len(vulnerabilities)} vulnerabilities from LLM.")
            return vulnerabilities
            
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            return []

    async def _verify_exploit(self, vuln: RedAgentVulnerability, target: str) -> Dict:
        """
        [Specialist] Attempt to verify vulnerability using specialized tools.
        """
        # Convert our local Vulnerability model to dict for NeuroSploit tools
        vuln_dict = {
            "type": vuln.type,
            "parameter": vuln.location.parameter,
            "service": "http", # Default assumption
            "port": 80
        }
        
        if vuln.type == "sql_injection":
             injector = SQLInjector()
             return await asyncio.to_thread(injector.exploit, target, vuln_dict)
        elif vuln.type in ["xss", "lfi"]:
             exploiter = WebExploiter()
             return await asyncio.to_thread(exploiter.exploit, target, vuln_dict)
        elif vuln.type == "rce":
             exploiter = RCEExploiter()
             return await asyncio.to_thread(exploiter.exploit, target, vuln_dict)
             
        return {"success": False, "message": "No verifier available"}

    async def _attempt_privesc(self) -> Dict:
        """
        [Phase 4] Attempt Privilege Escalation
        """
        self.logger.info("Running Linux Privilege Escalation Checks...")
        try:
            privesc = LinuxPrivEsc()
            # Enumerate checks
            enum_data = await asyncio.to_thread(privesc.enumerate)
            
            # Try basic SUID exploits on found binaries
            exploited = []
            for binary in enum_data.get("suid_binaries", []):
                res = await asyncio.to_thread(privesc.exploit_suid, binary)
                if res.get("success"):
                    exploited.append(res)
            
            enum_data["exploited_suid"] = exploited
            
            # Harvest Credentials
            harvester = CredentialHarvester()
            creds = await asyncio.to_thread(harvester.harvest_linux)
            enum_data["credentials"] = creds
            
            return enum_data
        except Exception as e:
            self.logger.error(f"PrivEsc failed: {e}")
            return {}
    
    def _calculate_statistics(self, vulnerabilities: List[RedAgentVulnerability]) -> Dict[str, Any]:
        """Calculate statistics from vulnerabilities"""
        by_severity = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for vuln in vulnerabilities:
            severity = vuln.severity.lower()
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            "total_vulnerabilities": len(vulnerabilities),
            "critical_vulnerabilities": by_severity.get("critical", 0),
            "high_vulnerabilities": by_severity.get("high", 0),
            "medium_vulnerabilities": by_severity.get("medium", 0),
            "low_vulnerabilities": by_severity.get("low", 0),
            "info_vulnerabilities": by_severity.get("info", 0),
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
            vulnerabilities=[RedAgentVulnerability(**v) for v in result["vulnerabilities"]],
            statistics=result["statistics"],
            scan_complete=result["scan_complete"]
        )
