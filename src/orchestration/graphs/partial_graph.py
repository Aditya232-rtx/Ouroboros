"""
Partial Workflow Graph - Simplified execution starting from GOVERNANCE

Skips RED agent vulnerability detection and starts from GOVERNANCE prioritization.
Designed for reusing existing vulnerability scan outputs.
"""

import logging
from langgraph.graph import StateGraph, END
from src.orchestration.state import OuroborosState
from src.orchestration.nodes.governance_node import governance_prioritize_node
from src.orchestration.nodes.blue_fix_node import blue_fix_node
from src.orchestration.nodes.red_verify_node import red_verify_node
from src.orchestration.nodes.doc_final_node import final_documentation_node
from src.orchestration.nodes.pr_node import pr_create_node

logger = logging.getLogger(__name__)


def create_partial_workflow_graph():
    """
    Create simplified workflow starting from GOVERNANCE.
    
    Flow: GOVERNANCE → BLUE_FIX → RED_VERIFY → DOC_FINAL → PR_CREATE → END
    
    No retry loops - single pass through with max 1 verification attempt.
    """
    logger.info("Creating partial workflow graph (GOVERNANCE → PR)")
    
    workflow = StateGraph(OuroborosState)
    
    # Add only required nodes
    workflow.add_node("governance", governance_prioritize_node)
    workflow.add_node("blue_fix", blue_fix_node)
    workflow.add_node("red_verify", red_verify_node)
    workflow.add_node("doc_final", final_documentation_node)
    workflow.add_node("pr_create", pr_create_node)
    
    # Linear flow (no conditional routing, no retry loops)
    workflow.add_edge("governance", "blue_fix")
    workflow.add_edge("blue_fix", "red_verify")
    workflow.add_edge("red_verify", "doc_final")
    workflow.add_edge("doc_final", "pr_create")
    workflow.add_edge("pr_create", END)
    
    # Start from GOVERNANCE
    workflow.set_entry_point("governance")
    
    compiled = workflow.compile()
    logger.info("✅ Partial workflow graph created")
    return compiled
