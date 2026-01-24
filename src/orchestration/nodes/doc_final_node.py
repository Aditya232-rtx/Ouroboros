"""
Documentation Final Node - Create final report with fixes
Orchestration node for DOCUMENTATION agent final report
"""

import logging
from typing import Dict, Any
from src.orchestration.state import OuroborosState
from src.agents import DocumentationAgent

logger = logging.getLogger(__name__)

async def doc_final_node(state: OuroborosState) -> OuroborosState:
    """
    Node 7: DOCUMENTATION Agent creates final report
    
    Updates Google Doc with fixes and verification results.
    """
    logger.info("📝 Creating final documentation")
    
    doc_agent = DocumentationAgent()
    
    result = await doc_agent.execute({
        "vulnerabilities": state["vulnerabilities"],
        "fixes": state["fixes"],
        "verification_results": state["verification_results"],
        "metadata": {
            "repo_url": state["repo_url"],
            "scan_id": state["scan_id"]
        },
        "report_type": "final"
    })
    
    state["final_report_url"] = result.get("doc_url", "")
    state["final_report_id"] = result.get("doc_id", "")
    state["current_phase"] = "documentation_final"
    
    logger.info(f"✅ Final report created: {state.get('final_report_url')}")
    
    return state
