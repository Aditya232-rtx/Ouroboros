"""
BLUE Fix Node - Secure fix generation
Orchestration node for BLUE agent fix generation
"""

import logging
from typing import Dict, Any
from src.orchestration.state import OuroborosState
from src.agents import BLUEAgent

logger = logging.getLogger(__name__)

async def blue_fix_node(state: OuroborosState) -> OuroborosState:
    """
    Node 4: BLUE Agent generates secure fixes
    
    Generates fixes for prioritized vulnerabilities with safety gate validation.
    """
    retry_count = state.get("retry_count", 0)
    logger.info(f"🔵 BLUE Fix generation (attempt {retry_count + 1})")
    
    blue_agent = BLUEAgent()
    
    # Process prioritized vulnerabilities
    fixes = []
    for vuln in state["prioritized_queue"]:
        logger.info(f"Generating fix for {vuln.get('id')}: {vuln.get('type')}")
        
        result = await blue_agent.execute({
            "vulnerability_id": vuln.get("id"),
            "vulnerability_type": vuln.get("type"),
            "vulnerability_location": vuln.get("location", {}),
            "vulnerable_code": vuln.get("code_snippet", ""),
            "cwe": vuln.get("cwe", ""),
            "cvss": vuln.get("cvss", 0.0)
        })
        
        fixes.append(result)
    
    state["fixes"] = fixes
    state["current_phase"] = "fixes_generated"
    
    logger.info(f"✅ Fix generation complete: {len(fixes)} fixes created")
    
    return state
