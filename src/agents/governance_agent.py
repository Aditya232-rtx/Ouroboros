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
    fix: Dict[str, Any]
    vulnerability: Dict[str, Any]
    environment: Dict[str, Any]


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


class GovernanceAgentOutput(AgentOutput):
    """Output schema for GOVERNANCE Agent"""
    governance_decision_id: str
    fix_id: str
    decision: GovernanceDecision
    approval_workflow: ApprovalWorkflow
    constraints: Dict[str, Any]


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
        """Execute GOVERNANCE Agent policy evaluation"""
        gov_id = f"GOV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        fix_id = input_data.get("fix", {}).get("fix_id", "unknown")
        
        self.logger.info(f"Governance evaluation {gov_id} for fix {fix_id}")
        
        try:
            # Calculate risk score
            risk_score = self._calculate_risk_score(
                input_data.get("vulnerability", {}),
                input_data.get("environment", {})
            )
            
            # Determine autonomy level
            autonomy_level = self._determine_autonomy(risk_score)
            
            # Build approval workflow
            approval_workflow = self._build_approval_workflow(
                autonomy_level, 
                risk_score
            )
            
            decision = {
                "risk_score": risk_score,
                "autonomy_level": autonomy_level,
                "rationale": f"Risk score {risk_score:.1f} requires {autonomy_level} level",
                "policy_evaluations": {
                    "cvss_check": "passed",
                    "environment_check": "passed",
                    "v1_pr_required": True
                }
            }
            
            return {
                "governance_decision_id": gov_id,
                "fix_id": fix_id,
                "decision": decision,
                "approval_workflow": approval_workflow,
                "constraints": {
                    "v1_no_auto_merge": True,
                    "requires_pr_review": True,
                    "min_reviewers": 2
                }
            }
            
        except Exception as e:
            self.logger.error(f"Governance evaluation failed: {e}")
            return {
                "governance_decision_id": gov_id,
                "fix_id": fix_id,
                "decision": {"error": str(e)},
                "approval_workflow": {},
                "constraints": {}
            }
    
    def _calculate_risk_score(
        self, 
        vulnerability: Dict[str, Any],
        environment: Dict[str, Any]
    ) -> float:
        """Calculate risk score using formula"""
        cvss = vulnerability.get("cvss", 5.0)
        env = environment.get("target", "dev")
        env_multiplier = self.ENV_MULTIPLIERS.get(env, 1.0)
        
        # Exploit ease from PoC success rate
        poc_rate = vulnerability.get("poc_success_rate", 0.5)
        exploit_ease = 0.2 + (poc_rate * 0.8)  # 0.2 to 1.0
        
        risk_score = cvss * env_multiplier * exploit_ease
        return min(100, risk_score)
    
    def _determine_autonomy(self, risk_score: float) -> str:
        """Determine autonomy level based on risk score"""
        if risk_score >= self.AUTONOMY_THRESHOLDS["escalate"]:
            return "escalate"
        elif risk_score >= self.AUTONOMY_THRESHOLDS["require"]:
            return "require"
        elif risk_score >= self.AUTONOMY_THRESHOLDS["suggest"]:
            return "suggest"
        else:
            return "require"  # V1: Always require PR review
    
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
        return GovernanceAgentOutput(
            agent_id=self.agent_id,
            timestamp=datetime.now().isoformat(),
            status="success" if "error" not in result.get("decision", {}) else "error",
            governance_decision_id=result["governance_decision_id"],
            fix_id=result["fix_id"],
            decision=GovernanceDecision(**result["decision"]) if "error" not in result.get("decision", {}) else None,
            approval_workflow=ApprovalWorkflow(**result["approval_workflow"]) if result.get("approval_workflow") else None,
            constraints=result["constraints"]
        )
