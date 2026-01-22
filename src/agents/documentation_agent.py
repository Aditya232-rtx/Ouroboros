"""
Ouroboros AI - DOCUMENTATION Agent
Creates and updates Google Docs reports automatically using Phi-3.5-mini
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.models import get_model

logger = logging.getLogger(__name__)


class DocumentationAgentInput(AgentInput):
    """Input schema for DOCUMENTATION Agent"""
    vulnerabilities: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    governance_plan: List[Dict[str, Any]] = Field(default_factory=list)
    fixes: List[Dict[str, Any]] = Field(default_factory=list)


class GoogleDocInfo(BaseModel):
    """Google Doc information"""
    doc_id: str
    doc_url: str
    title: str
    created_at: str
    last_updated: str


class DocumentationAgentOutput(AgentOutput):
    """Output schema for DOCUMENTATION Agent"""
    documentation_id: str
    google_doc: GoogleDocInfo
    sections_generated: List[str]
    content_summary: Dict[str, Any]


class DocumentationAgent(BaseAgent):
    """
    DOCUMENTATION Agent - Technical documentation specialist
    
    Uses Phi-3.5-mini-instruct for creating Google Docs reports
    """
    
    def __init__(self):
        """Initialize DOCUMENTATION Agent with Phi-3.5 model"""
        model = get_model("documentation")
        super().__init__(model=model, agent_id="DOCUMENTATION")
        
        self.system_prompt = """You are Phi-3.5, a technical documentation specialist for security reports.

TASK: Create clear, professional security reports.

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
   - Approach used
   - Code changes (before/after diff)
   - Test coverage added
   - Verification results

4. COMPLIANCE EVIDENCE
   - SOC2 controls addressed
   - ISO27001 controls addressed
   - GDPR Article 32 compliance
   - Immutable audit trail reference

5. RECOMMENDATIONS
   - Additional hardening
   - Code review priorities
   - Monitoring recommendations

FORMAT: Use headers, code blocks, tables, bullet points. Professional and concise."""
    
    def validate_input(self, input_data: Dict[str, Any]) -> DocumentationAgentInput:
        """Validate DOCUMENTATION Agent input"""
        return DocumentationAgentInput(**input_data)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute DOCUMENTATION Agent to create report"""
        doc_id = f"DOC-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.logger.info(f"Creating documentation {doc_id}")
        
        try:
            # Generate report content
            content = await self._generate_report(input_data)
            
            # Create Google Doc (simulated for now)
            doc_info = await self._create_google_doc(content, input_data)
            
            # Calculate summary
            vulns = input_data.get("vulnerabilities", [])
            severity_breakdown = self._calculate_severity(vulns)
            
            return {
                "documentation_id": doc_id,
                "google_doc": doc_info,
                "sections_generated": [
                    "Executive Summary",
                    "Vulnerability Details",
                    "Remediation Plan",
                    "Compliance Impact",
                    "Appendix - PoC Code"
                ],
                "content_summary": {
                    "total_vulnerabilities": len(vulns),
                    "severity_breakdown": severity_breakdown,
                    "risk_score": self._calculate_risk_score(vulns)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Documentation creation failed: {e}")
            return {
                "documentation_id": doc_id,
                "google_doc": None,
                "sections_generated": [],
                "content_summary": {"error": str(e)}
            }
    
    async def _generate_report(self, data: Dict[str, Any]) -> str:
        """Generate report content using Phi-3.5"""
        prompt = f"""{self.system_prompt}

VULNERABILITIES:
{data.get('vulnerabilities', [])}

METADATA:
{data.get('metadata', {})}

Generate a comprehensive security report."""
        
        return self._call_llm(prompt)
    
    async def _create_google_doc(
        self, 
        content: str, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create Google Doc via MCP
        
        TODO: Implement actual Google Workspace MCP integration
        """
        self.logger.info("Creating Google Doc (simulated)...")
        
        repo_name = data.get("metadata", {}).get("repo_name", "unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        # Simulated doc info
        return {
            "doc_id": f"google-doc-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "doc_url": f"https://docs.google.com/document/d/simulated-{repo_name}",
            "title": f"Ouroboros Security Report - {repo_name} - {timestamp}",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
    
    def _calculate_severity(self, vulns: List[Dict]) -> Dict[str, int]:
        """Calculate severity breakdown"""
        breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for v in vulns:
            sev = v.get("severity", "low").lower()
            breakdown[sev] = breakdown.get(sev, 0) + 1
        return breakdown
    
    def _calculate_risk_score(self, vulns: List[Dict]) -> float:
        """Calculate overall risk score (0-100)"""
        if not vulns:
            return 0.0
        
        weights = {"critical": 10, "high": 7, "medium": 4, "low": 1}
        total = sum(weights.get(v.get("severity", "low").lower(), 1) for v in vulns)
        return min(100, (total / len(vulns)) * 10)
    
    def format_output(self, result: Dict[str, Any]) -> DocumentationAgentOutput:
        """Format DOCUMENTATION Agent output"""
        return DocumentationAgentOutput(
            agent_id=self.agent_id,
            timestamp=datetime.now().isoformat(),
            status="success" if result.get("google_doc") else "error",
            documentation_id=result["documentation_id"],
            google_doc=GoogleDocInfo(**result["google_doc"]) if result.get("google_doc") else None,
            sections_generated=result["sections_generated"],
            content_summary=result["content_summary"]
        )
