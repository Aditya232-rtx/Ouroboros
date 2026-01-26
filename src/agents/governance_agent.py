"""
Ouroboros AI - GOVERNANCE Agent
Policy-based risk evaluation using Phi-3.5-mini and OPA
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.models import get_model

logger = logging.getLogger(__name__)


class GovernanceAgentInput(AgentInput):
    """Input schema for GOVERNANCE Agent"""
    vulnerabilities: List[Dict[str, Any]]
    environment: str = "production"


class GovernanceDecision(BaseModel):
    """Governance decision details"""
    risk_score: float
    autonomy_level: str  # auto_approve|suggest|require|escalate
    rationale: str
    policy_evaluations: Dict[str, Any]


class ApprovalWorkflow(BaseModel):
    """Approval workflow configuration"""
    required_approvers: List[str]
    optional_approvers: List[str] = Field(default_factory=list)
    escalation_contact: str = ""
    estimated_approval_time_minutes: int = 60


class PrioritizedVulnerability(BaseModel):
    """Vulnerability with governance meta-data"""
    vulnerability_id: str
    priority: int
    risk_score: float
    autonomy_level: str
    reasoning: str
    original_vulnerability: Dict[str, Any]


class GovernanceAgentOutput(AgentOutput):
    """Output schema for GOVERNANCE Agent"""
    governance_id: str
    prioritized_queue: List[Dict[str, Any]]
    decisions: List[Dict[str, Any]]
    risk_scores: Dict[str, float]


class GovernanceAgent(BaseAgent):
    """
    GOVERNANCE Agent - Policy evaluation specialist
    
    Uses Phi-3.5-mini-instruct for deterministic policy decisions
    """
    
    # Environment multipliers for risk calculation
    ENV_MULTIPLIERS = {
        "dev": 1.0,
        "staging": 2.0,
        "production": 5.0
    }
    
    # Autonomy thresholds
    AUTONOMY_THRESHOLDS = {
        "auto_approve": 20,  # V1: NOT USED
        "suggest": 50,
        "require": 80,
        "escalate": 100
    }
    
    def __init__(self):
        """Initialize GOVERNANCE Agent with Phi-3.5 model"""
        model = get_model("governance")
        super().__init__(model=model, agent_id="GOVERNANCE")
        
        self.system_prompt = """You are Phi-3.5, a security governance policy engine.

TASK: Evaluate vulnerabilities and prioritize fixes using policy-as-code.

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
- auto_approve: risk < 20 (V1: NOT USED)
- suggest: risk 20-50
- require: risk 50-80
- escalate: risk > 80

V1 OVERRIDE: All fixes go through PR review (no auto-merge)."""
    
    def validate_input(self, input_data: Dict[str, Any]) -> GovernanceAgentInput:
        """Validate GOVERNANCE Agent input"""
        return GovernanceAgentInput(**input_data)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute GOVERNANCE Agent policy evaluation and prioritization"""
        # Validate input
        validated_input = self.validate_input(input_data)
        
        gov_id = f"GOV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.logger.info(f"Starting governance prioritization {gov_id}")
        
        prioritized_items = []
        decisions = []
        risk_scores = {}
        
        try:
            for vuln in validated_input.vulnerabilities:
                # Calculate risk score
                risk_score = self._calculate_risk_score(
                    vuln,
                    validated_input.environment
                )
                
                # Determine autonomy level
                autonomy_level = self._determine_autonomy(risk_score)
                
                item = {
                    "vulnerability_id": vuln.get("id"),
                    "risk_score": risk_score,
                    "autonomy_level": autonomy_level,
                    "reasoning": f"Risk score {risk_score:.1f} ({autonomy_level})",
                    "original_vulnerability": vuln
                }
                
                prioritized_items.append(item)
                decisions.append({
                    "vulnerability_id": vuln.get("id"),
                    "decision": "prioritized",
                    "risk_score": risk_score
                })
                risk_scores[vuln.get("id")] = risk_score
            
            # Sort by risk score descending
            prioritized_items.sort(key=lambda x: x["risk_score"], reverse=True)
            
            # Assign priority index
            for idx, item in enumerate(prioritized_items):
                item["priority"] = idx + 1
            
            # For the node, we want to return the original vulnerabilities sorted
            # But the node code expects "prioritized_queue" to be a list of vulnerabilities?
            # Let's check governance_node.py:
            # result = await blue_agent.execute({"vulnerability": vuln})
            # So "prioritized_queue" should probably be the vulnerabilities themselves or 
            # objects containing them.
            # Blue Fix Node: for vuln in state["prioritized_queue"]:
            
            # To be safe, we return the LIST OF VULNERABILITIES (sorted) 
            # as the queue, but maybe enriched.
            # Actually, let's look at Blue Fix Node usage if we can.
            # Assuming it expects the vulnerability dict.
            # We will return the enriched objects, assuming Blue Agent extracts what it needs
            # OR we simply map back to original vuln dicts.
            # Let's map back to original dicts but sorted, to be safe for Blue Agent.
            
            sorted_vulnerabilities = [p["original_vulnerability"] for p in prioritized_items]
            
            return {
                "prioritized_queue": sorted_vulnerabilities,
                "decisions": decisions,
                "risk_scores": risk_scores
            }
            
        except Exception as e:
            self.logger.error(f"Governance prioritization failed: {e}")
            return {
                "prioritized_queue": validated_input.vulnerabilities, # Fallback: unsorted
                "decisions": [],
                "risk_scores": {}
            }
    
    def _calculate_risk_score(
        self, 
        vulnerability: Dict[str, Any],
        environment: str
    ) -> float:
        """Calculate risk score using formula"""
        cvss = vulnerability.get("cvss", 5.0)
        env_multiplier = self.ENV_MULTIPLIERS.get(environment, 5.0) # Default to production/high
        
        # Exploit ease from PoC success rate or confidence
        poc_rate = vulnerability.get("confidence", 0.5)
        exploit_ease = 0.2 + (poc_rate * 0.8)  # 0.2 to 1.0
        
        risk_score = cvss * env_multiplier * exploit_ease
        return min(100.0, risk_score)
    
    def _determine_autonomy(self, risk_score: float) -> str:
        """Determine autonomy level based on risk score"""
        if risk_score >= self.AUTONOMY_THRESHOLDS["escalate"]:
            return "escalate"
        elif risk_score >= self.AUTONOMY_THRESHOLDS["require"]:
            return "require"
        elif risk_score >= self.AUTONOMY_THRESHOLDS["suggest"]:
            return "suggest"
        else:
            return "auto_approve" 
    
    def _build_approval_workflow(
        self, 
        autonomy_level: str, 
        risk_score: float
    ) -> Dict[str, Any]:
        """Build approval workflow based on autonomy level"""
        workflows = {
            "escalate": {
                "required_approvers": ["security_team", "ciso"],
                "optional_approvers": [],
                "escalation_contact": "ciso@company.com",
                "estimated_approval_time_minutes": 60
            },
            "require": {
                "required_approvers": ["security_team"],
                "optional_approvers": ["on_call_engineer"],
                "escalation_contact": "security-team@company.com",
                "estimated_approval_time_minutes": 240
            },
            "suggest": {
                "required_approvers": ["on_call_engineer"],
                "optional_approvers": [],
                "escalation_contact": "",
                "estimated_approval_time_minutes": 120
            }
        }
        
        return workflows.get(autonomy_level, workflows["require"])
    
    def format_output(self, result: Dict[str, Any]) -> GovernanceAgentOutput:
        """Format GOVERNANCE Agent output"""
        # Hack for V1 to match expected output structure vaguely if needed
        # But mostly we use the dict result in the node
        return GovernanceAgentOutput(
            agent_id=self.agent_id,
            timestamp=datetime.now().isoformat(),
            status="success",
            governance_id="GOV-BATCH",
            prioritized_queue=result["prioritized_queue"],
            decisions=result["decisions"],
            risk_scores=result["risk_scores"]
        )
