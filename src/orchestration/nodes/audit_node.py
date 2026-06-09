"""
Audit Node - Immutable audit logging
Orchestration node for AUDIT agent
"""

import logging
from typing import Dict,Any
from datetime import datetime
from src.orchestration.state import OuroborosState
from src.agents import AuditAgent

logger = logging.getLogger(__name__)

async def audit_node(state: OuroborosState) -> OuroborosState:
    """
    Node 9: AUDIT Agent logs complete workflow to immudb
    
    Creates immutable audit trail for compliance.
    """
    logger.info("📋 Logging audit trail")
    
    audit_agent = AuditAgent()
    
    result = await audit_agent.execute({
        "workflow_state": state,
        "event_type": "workflow_complete"
    })
    
    state["audit_entries"] = result.get("audit_ids", [])
    state["current_phase"] = "complete"
    state["workflow_end_time"] = datetime.now().isoformat()
    
    logger.info(f"✅ Audit complete: {len(state.get('audit_entries', []))} entries logged")
    
    return state
