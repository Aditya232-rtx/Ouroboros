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
    
    # Cleanup Sandbox
    sandbox_info = state.get("sandbox_info")
    if sandbox_info:
        logger.info(f"🧹 Cleaning up sandbox resources...")
        try:
             import subprocess
             container_id = sandbox_info.get("container_id")
             compose_project = sandbox_info.get("compose_project")
             sandbox_path = sandbox_info.get("sandbox_path")
             
             if compose_project and sandbox_path:
                 subprocess.run(["docker-compose", "-p", compose_project, "down", "-v"], cwd=sandbox_path, capture_output=True)
             
             if container_id:
                 subprocess.run(["docker", "rm", "-f", container_id], capture_output=True)
                 logger.info(f"Stopped container {container_id}")
                 
        except Exception as e:
            logger.error(f"Failed to cleanup sandbox: {e}")

    return state
