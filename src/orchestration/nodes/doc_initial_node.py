"""
Documentation Initial Node - Create initial report
Orchestration node for DOCUMENTATION agent initial report
"""

import logging
from typing import Dict, Any
from src.orchestration.state import OuroborosState
from src.agents import DocumentationAgent

logger = logging.getLogger(__name__)

async def doc_initial_node(state: OuroborosState) -> OuroborosState:
    """
    Node 2: DOCUMENTATION Agent creates initial vulnerability report
    
    Creates initial Google Doc with discovered vulnerabilities.
    """
    logger.info("📝 Creating initial documentation")
    
    doc_agent = DocumentationAgent()
    
    result = await doc_agent.execute({
        "vulnerabilities": state["vulnerabilities"],
        "metadata": {
            "repo_url": state["repo_url"],
            "scan_id": state["scan_id"],
            "scan_stats": state.get("scan_statistics", {})
        },
        "report_type": "initial"
    })
    
    state["initial_report_url"] = result.get("doc_url", "")
    state["initial_report_id"] = result.get("doc_id", "")
    state["current_phase"] = "documentation_initial"
    
    logger.info(f"✅ Initial report created: {state.get('initial_report_url')}")
    
    return state
