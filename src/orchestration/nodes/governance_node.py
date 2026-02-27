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
    
    # Persist governance results to DB immediately
    try:
        from src.database.session import SessionLocal
        from src.database.models import Scan
        
        db = SessionLocal()
        scan_id = state.get("scan_id")
        if scan_id:
            scan = db.query(Scan).filter(Scan.scan_id == scan_id).first()
            if scan:
                # Update metadata with governance results
                metadata = dict(scan.scan_metadata or {})
                
                # Use enriched queue for metadata (detailed for frontend)
                # Fallback to prioritized_queue (raw for blue agent) if enriched missing
                gov_queue = result.get("enriched_queue", []) or state["prioritized_queue"]
                
                metadata.update({
                    "current_phase": "governance_complete",
                    "governance_queue": gov_queue,
                    "risk_scores": state["risk_scores"],
                    "governance_decisions": state["governance_decisions"]
                })
                scan.scan_metadata = metadata
                db.commit()
                logger.info(f"💾 Persisted governance results to DB for {scan_id}")
        db.close()
    except Exception as e:
        logger.error(f"Failed to persist governance results: {e}")
    
    return state
