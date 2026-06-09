"""
Governance Node - Risk-based prioritization
Orchestration node for GOVERNANCE agent decisions
"""

import logging
from typing import Dict, Any
from src.orchestration.state import OuroborosState
from src.agents import GovernanceAgent

logger = logging.getLogger(__name__)

async def governance_node(state: OuroborosState) -> OuroborosState:
    """
    Node 3: GOVERNANCE Agent prioritizes vulnerabilities
    
    Applies OPA policies to calculate risk scores and prioritize fixes.
    """
    logger.info("⚖️  Applying governance policies")
    
    gov_agent = GovernanceAgent()
    
    result = await gov_agent.execute({
        "vulnerabilities": state["vulnerabilities"],
        "environment": state.get("environment", "production")
    })
    
    state["prioritized_queue"] = result.get("prioritized_queue", [])
    state["governance_decisions"] = result.get("decisions", [])
    state["risk_scores"] = result.get("risk_scores", {})
    state["current_phase"] = "governance_complete"
    
    logger.info(f"✅ Governance complete: {len(state['prioritized_queue'])} vulnerabilities prioritized")
    
    return state
