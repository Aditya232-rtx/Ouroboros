"""
Ouroboros AI - LangGraph Workflow
Main orchestration workflow connecting all agents
"""

import logging
from datetime import datetime
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.orchestration.state import OuroborosState
from src.agents import (
    REDAgent,
    BLUEAgent,
    DocumentationAgent,
    GovernanceAgent,
    AuditAgent
)

logger = logging.getLogger(__name__)


class OuroborosWorkflow:
    """
    LangGraph workflow orchestrating all Ouroboros agents.
    Implements the complete vulnerability discovery → fix → verification → PR cycle.
    """
    
    def __init__(self):
        """Initialize workflow with all agents"""
        self.red_agent = REDAgent()
        self.blue_agent = BLUEAgent()
        self.doc_agent = DocumentationAgent()
        self.governance_agent = GovernanceAgent()
        self.audit_agent = AuditAgent()
        
        # Build workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """
        Build LangGraph workflow with all nodes and edges.
        
        Workflow Flow:
        1. RED scan → 2. Initial doc → 3. Governance → 4. BLUE fix
        → 5. RED verify → 6. Check verification → 7. Final doc → 8. Create PR → 9. Audit
        """
        workflow = StateGraph(OuroborosState)
        
        from src.orchestration.nodes.red_scan_node import red_scan_node
        from src.orchestration.nodes.doc_initial_node import doc_initial_node
        from src.orchestration.nodes.governance_node import governance_node
        from src.orchestration.nodes.blue_fix_node import blue_fix_node
        from src.orchestration.nodes.red_verify_node import red_verify_node
        from src.orchestration.nodes.doc_final_node import doc_final_node
        from src.orchestration.nodes.create_pr_node import create_pr_node
        from src.orchestration.nodes.audit_node import audit_node
        
        # Add nodes
        workflow.add_node("red_scan", red_scan_node)
        workflow.add_node("doc_initial", doc_initial_node)
        workflow.add_node("governance", governance_node)
        workflow.add_node("blue_fix", blue_fix_node)
        workflow.add_node("red_verify", red_verify_node)
        workflow.add_node("check_verification", self._check_verification_node)  # Keep inline for now as it's simple logic
        workflow.add_node("doc_final", doc_final_node)
        workflow.add_node("pr_creation", create_pr_node)
        workflow.add_node("audit", audit_node)
        
        # Add edges with detailed logging
        workflow.set_entry_point("red_scan")
        logger.info("🔗 Workflow edge: START → red_scan")
        
        workflow.add_edge("red_scan", "doc_initial")
        logger.info("🔗 Workflow edge: red_scan → doc_initial")
        
        workflow.add_edge("doc_initial", "governance")
        logger.info("🔗 Workflow edge: doc_initial → governance")
        
        workflow.add_edge("governance", "blue_fix")
        logger.info("🔗 Workflow edge: governance → blue_fix")
        
        workflow.add_edge("blue_fix", "red_verify")
        logger.info("🔗 Workflow edge: blue_fix → red_verify")
        
        workflow.add_edge("red_verify", "check_verification")
        logger.info("🔗 Workflow edge: red_verify → check_verification")
        
        # Conditional edge: retry fixes or proceed
        workflow.add_conditional_edges(
            "check_verification",
            self._route_after_verification,
            {
                "retry": "blue_fix",  # Loop back
                "proceed": "audit"    # User Req: Audit runs before PR/Doc
            }
        )
        logger.info("🔗 Workflow conditional edge: check_verification → [retry: blue_fix | proceed: audit]")
        
        workflow.add_conditional_edges(
            "audit",
            self._route_to_pr,
            {
                "create_pr": "pr_creation",
                "skip_pr": "doc_final"
            }
        )
        logger.info("🔗 Workflow conditional edge: audit → [create_pr: pr_creation | skip_pr: doc_final]")
        
        workflow.add_edge("pr_creation", "doc_final")
        logger.info("🔗 Workflow edge: pr_creation → doc_final")
        
        workflow.add_edge("doc_final", END)
        logger.info("🔗 Workflow edge: doc_final → END")
        
        logger.info("✅ Workflow graph compilation complete")
        return workflow.compile()
    
    # ===== WORKFLOW NODES =====
    # Note: Most nodes are imported from src/orchestration/nodes/
    # Only _check_verification_node is defined inline here
    
    async def _check_verification_node(self, state: OuroborosState) -> OuroborosState:
        """Node 6: Check if all fixes verified"""
        verified_count = sum(
            1 for r in state.get("verification_results", []) 
            if r.get("verified", False)
        )
        total_count = len(state.get("verification_results", []))
        
        all_verified = (verified_count == total_count) and total_count > 0
        state["all_verified"] = all_verified
        
        logger.info(f"Verification: {verified_count}/{total_count} fixes verified")
        
        # Incremental Retry Logic:
        # If not fully verified, we consume one retry attempt here.
        if not all_verified:
            current_retries = state.get("retry_count", 0)
            new_retries = current_retries + 1
            state["retry_count"] = new_retries
            
            if new_retries > 3: # Hardcoded MAX_RETRIES for now to match router
                 state["workflow_aborted"] = True
                 state["abort_reason"] = f"Max verification retries (3) exceeded"
                 logger.error("   ❌ Max retries reached - flagging for abort in router")
            else:
                 logger.info(f"   ⚠️  Verification failed (Attempt {new_retries})")
        
        return state
    
    # ===== CONDITIONAL ROUTING =====
    
    def _route_after_verification(self, state: OuroborosState) -> str:
        from src.orchestration.edges.verification_router import route_after_verification
        return route_after_verification(state)
    
    def _route_to_pr(self, state: OuroborosState) -> str:
        """Route to PR creation or skip to audit."""
        if state.get("create_pr", True):
            return "create_pr"
        return "skip_pr"
    
    # ===== PUBLIC API =====
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the complete Ouroboros workflow.
        
        Args:
            input_data: {repo_url, user_id, scan_profile, create_pr}
        
        Returns:
            Final workflow state
        """
        # Initialize state
        initial_state: OuroborosState = {
            "repo_url": input_data["repo_url"],
            "scan_id": input_data.get("scan_id", f"SCAN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"), # <--- USE PASSED ID
            "user_id": input_data.get("user_id", "anonymous"),
            "scan_profile": input_data.get("scan_profile", "standard"),
            "commit_sha": input_data.get("commit_sha", "HEAD"),
            "branch": input_data.get("branch", "main"),
            "create_pr": input_data.get("create_pr", True),
            "working_dir": "",  # Will be set by RED agent
            "workflow_start_time": datetime.now().isoformat(),
            "current_phase": "initializing",
            "retry_count": 0,
            "workflow_aborted": False,  # NEW: Abort tracking
            "abort_reason": None,
            "vulnerabilities": [],
            "scan_complete": False,
            "scan_statistics": {},
            "initial_report_url": None,
            "initial_report_id": None,
            "final_report_url": None,
            "final_report_id": None,
            "prioritized_queue": [],
            "governance_decisions": {},
            "risk_scores": {},
            "fixes": [],
            "verification_results": [],
            "all_verified": False,
            "pr_url": None,
            "pr_number": None,
            "pr_error": None,
            "audit_entries": [],
            "workflow_end_time": None,
            "errors": []
        }
        
        logger.info(f"🚀 Starting Ouroboros workflow for {input_data['repo_url']}")
        logger.info(f"   Scan ID: {initial_state['scan_id']}")
        logger.info(f"   Profile: {initial_state['scan_profile']}")
        
        # Execute workflow
        final_state = await self.workflow.ainvoke(initial_state)
        
        # Check if workflow was aborted
        if final_state.get("workflow_aborted"):
            logger.warning(f"⚠️  Workflow aborted: {final_state.get('abort_reason')}")
        
        logger.info(f"✅ Workflow complete: {final_state.get('scan_id')}")
        
        return final_state


# Global workflow instance
workflow = OuroborosWorkflow()
