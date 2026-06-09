"""
RED Scan Node - Vulnerability Discovery
Orchestration node for RED agent execution
"""

import logging
from typing import Dict, Any
from src.orchestration.state import OuroborosState
from src.agents import REDAgent

logger = logging.getLogger(__name__)

async def red_scan_node(state: OuroborosState) -> OuroborosState:
    """
    Node 1: RED Agent vulnerability discovery
    
    Executes security scanning and vulnerability discovery using RED agent.
    """
    logger.info(f"🔴 RED Scan starting for {state['repo_url']}")
    
    red_agent = REDAgent()
    
    result = await red_agent.execute({
        "repo_url": state["repo_url"],
        "commit_sha": state.get("commit_sha", "HEAD"),
        "branch": state.get("branch", "main"),
        "scan_profile": state.get("scan_profile", "standard")
    })
    
    state["vulnerabilities"] = result.get("vulnerabilities", [])
    state["scan_complete"] = result.get("scan_complete", False)
    state["scan_statistics"] = result.get("statistics", {})
    state["current_phase"] = "scan_complete"
    
    logger.info(f"✅ RED Scan complete: {len(state['vulnerabilities'])} vulnerabilities found")
    
    return state
