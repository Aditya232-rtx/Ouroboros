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
from src.agents.research_agent import ResearchAgent

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
        self.research_agent = ResearchAgent()
        
        # Build workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """
        Build LangGraph workflow with all nodes and edges.
        
        Workflow Flow:
        1. RED scan → 2. Initial doc → 3. Governance → 4. BLUE fix
        → 5. RED verify → 6. Check verification → 7. Final doc → 8. Create PR → 9. Audit
        
        Note: Research Agent runs independently on schedule (see scheduled_research.py)
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
        # Note: research_threats removed - now runs as scheduled background job
        workflow.add_node("red_scan", red_scan_node)
        workflow.add_node("doc_initial", doc_initial_node)
        workflow.add_node("governance", governance_node)
        workflow.add_node("blue_fix", blue_fix_node)
        workflow.add_node("red_verify", red_verify_node)
        workflow.add_node("check_verification", self._check_verification_node)
        workflow.add_node("doc_final", doc_final_node)
        workflow.add_node("create_pr", create_pr_node)
        workflow.add_node("audit", audit_node)
        
        # Add edges
        workflow.set_entry_point("red_scan")  # Changed from research_threats
        workflow.add_edge("red_scan", "doc_initial")
        workflow.add_edge("doc_initial", "governance")
        workflow.add_edge("governance", "blue_fix")
        workflow.add_edge("blue_fix", "red_verify")
        workflow.add_edge("red_verify", "check_verification")
        
        # Conditional edge: retry fixes or proceed
        workflow.add_conditional_edges(
            "check_verification",
            self._route_after_verification,
            {
                "retry": "blue_fix",  # Loop back
                "proceed": "doc_final"  # Continue
            }
        )
        
        workflow.add_conditional_edges(
            "doc_final",
            self._route_after_doc_final,
            {
                "create_pr": "create_pr",
                "skip_pr": "audit"
            }
        )
        workflow.add_edge("create_pr", "audit")
        workflow.add_edge("audit", END)
        
        return workflow.compile()
    
    # ===== WORKFLOW NODES =====
    # Note: research_threats_node removed - Research Agent now runs as scheduled background job
    # See src/orchestration/scheduled_research.py
    
    async def _red_scan_node(self, state: OuroborosState) -> OuroborosState:
        """Node 1: RED Agent vulnerability discovery"""
        logger.info(f"Starting RED scan for {state['repo_url']}")
        
        result = await self.red_agent.execute({
            "repo_url": state["repo_url"],
            "commit_sha": state.get("commit_sha", "HEAD"),
            "branch": state.get("branch", "main"),
            "scan_profile": state.get("scan_profile", "standard")
        })
        
        state["vulnerabilities"] = result["vulnerabilities"]
        state["scan_complete"] = result["scan_complete"]
        state["scan_statistics"] = result["statistics"]
        state["current_phase"] = "scan_complete"
        
        return state
    
    async def _doc_initial_node(self, state: OuroborosState) -> OuroborosState:
        """Node 2: DOCUMENTATION Agent creates initial report"""
        logger.info("Creating initial documentation")
        
        result = await self.doc_agent.execute({
            "vulnerabilities": state["vulnerabilities"],
            "metadata": {
                "repo_url": state["repo_url"],
                "scan_id": state["scan_id"]
            },
            "report_type": "initial"
        })
        
        state["initial_report_url"] = result.get("doc_url", "")
        state["initial_report_id"] = result.get("doc_id", "")
        state["current_phase"] = "documentation_initial"
        
        return state
    
    async def _governance_node(self, state: OuroborosState) -> OuroborosState:
        """Node 3: GOVERNANCE Agent prioritizes vulnerabilities"""
        logger.info("Applying governance policies")
        
        result = await self.governance_agent.execute({
            "vulnerabilities": state["vulnerabilities"],
            "environment": "production"  # TODO: from state
        })
        
        state["prioritized_queue"] = result["prioritized_queue"]
        state["govern ance_decisions"] = result["decisions"]
        state["risk_scores"] = result["risk_scores"]
        state["current_phase"] = "governance_complete"
        
        return state
    
    async def _blue_fix_node(self, state: OuroborosState) -> OuroborosState:
        """Node 4: BLUE Agent generates fixes"""
        logger.info(f"Generating fixes (attempt {state.get('retry_count', 0) + 1})")
        
        # Process prioritized vulnerabilities
        fixes = []
        for vuln in state["prioritized_queue"]:
            result = await self.blue_agent.execute({
                "vulnerability": vuln
            })
            fixes.append(result)
        
        state["fixes"] = fixes
        state["current_phase"] = "fixes_generated"
        
        return state
    
    async def _red_verify_node(self, state: OuroborosState) -> OuroborosState:
        """
        Node 5: RED Agent verifies fixes using PoC exploits.
        
        Per 03_CRITICAL_DO_NOT: Must run in Docker sandbox
        Per VERIFICATION_LOOP: Max 10 retries
        """
        logger.info("Verifying fixes with RED Agent re-attack...")
        
        from src.verification.verification_engine import VerificationEngine
        from src.tools.docker_sandbox import docker_sandbox
        
        # Initialize verification engine
        engine = VerificationEngine()
        
        verification_results = []
        for fix in state["fixes"]:
            # Get the original vulnerability
            vuln = next(
                (v for v in state["vulnerabilities"] if v.get("id") == fix.get("vulnerability_id")),
                None
            )
            
            if not vuln:
                logger.error(f"Vulnerability not found for fix {fix.get('fix_id')}")
                verification_results.append({
                    "fix_id": fix.get("fix_id"),
                    "verified": False,
                    "error": "Original vulnerability not found"
                })
                continue
            
            # Verify fix
            try:
                result = await engine.verify_fix(
                    fix_code=fix.get("code_diff", {}).get("after", ""),
                    original_vulnerability=vuln,
                    sandbox=docker_sandbox
                )
                
                verification_results.append({
                    "fix_id": fix.get("fix_id"),
                    "vulnerability_id": vuln.get("id"),
                    "verified": result.get("verified", False),
                    "poc_failed": result.get("poc_failed", False),  # Good: exploit failed
                    "details": result
                })
                
                logger.info(
                    f"Fix {fix.get('fix_id')}: "
                    f"{'✅ VERIFIED' if result.get('verified') else '❌ FAILED'}"
                )
                
            except Exception as e:
                logger.error(f"Verification failed for {fix.get('fix_id')}: {e}")
                verification_results.append({
                    "fix_id": fix.get("fix_id"),
                    "verified": False,
                    "error": str(e)
                })
        
        state["verification_results"] = verification_results
        state["current_phase"] = "verification_complete"
        
        return state
    
    async def _check_verification_node(self, state: OuroborosState) -> OuroborosState:
        """Node 6: Check if all fixes verified"""
        verified_count = sum(
            1 for r in state["verification_results"] 
            if r.get("verified", False)
        )
        total_count = len(state["verification_results"])
        
        state["all_verified"] = (verified_count == total_count)
        state["retry_count"] = state.get("retry_count", 0) + 1
        
        logger.info(f"Verification: {verified_count}/{total_count} fixes verified")
        
        return state
    
    async def _doc_final_node(self, state: OuroborosState) -> OuroborosState:
        """Node 7: DOCUMENTATION Agent creates final report"""
        logger.info("Creating final documentation")
        
        result = await self.doc_agent.execute({
            "vulnerabilities": state["vulnerabilities"],
            "fixes": state["fixes"],
            "verification_results": state["verification_results"],
            "report_type": "final"
        })
        
        state["final_report_url"] = result.get("doc_url", "")
        state["final_report_id"] = result.get("doc_id", "")
        state["current_phase"] = "documentation_final"
        
        return state
    
    async def _create_pr_node(self, state: OuroborosState) -> OuroborosState:
        """Node 8: Create GitHub PR using real GitHub API."""
        logger.info("Creating GitHub PR")
        
        try:
            from src.integrations.github_api import github_client
            
            # Extract repo info from state
            repo_url = state.get("repo_url", "")
            # Parse owner/repo from URL
            if "github.com" in repo_url:
                parts = repo_url.rstrip("/").split("/")
                repo_full_name = f"{parts[-2]}/{parts[-1]}"
            else:
                repo_full_name = repo_url
            
            # Create branch name
            branch_name = f"ouroboros/security-fix-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Prepare PR body with vulnerability summary
            vulns = state.get("vulnerabilities", [])
            fixes = state.get("fixes", [])
            
            pr_body = f"""## Ouroboros AI Security Fix

### Vulnerabilities Fixed: {len(fixes)}

| Vulnerability | Severity | Status |
|---------------|----------|--------|
"""
            for fix in fixes[:10]:  # Limit to 10 in PR description
                vuln_id = fix.get("vulnerability_id", "N/A")
                severity = fix.get("severity", "N/A")
                status = "✅ Fixed" if fix.get("verified") else "⚠️ Needs Review"
                pr_body += f"| {vuln_id} | {severity} | {status} |\n"
            
            pr_body += f"""
### Automated Security Report
- Full Report: {state.get('final_report_url', 'N/A')}
- Initial Scan: {state.get('report_url', 'N/A')}

### Compliance
This PR addresses security vulnerabilities per SOC2 CC6.1, ISO27001 A.14.2.1

**⚠️ REQUIRES 2x HUMAN REVIEW BEFORE MERGE (Per V1 Policy)**
"""
            
            # Create the PR
            pr_result = github_client.create_pull_request(
                repo_full_name=repo_full_name,
                title=f"[Ouroboros] Security Fix: {len(fixes)} vulnerabilities",
                body=pr_body,
                head_branch=branch_name,
                base_branch=state.get("branch", "main"),
                reviewers=state.get("reviewers", [])
            )
            
            state["pr_url"] = pr_result.get("pr_url", "")
            state["pr_number"] = pr_result.get("pr_number", 0)
            state["current_phase"] = "pr_created"
            
            logger.info(f"Created PR: {state['pr_url']}")
            
        except Exception as e:
            logger.error(f"GitHub PR creation failed: {e}")
            state["pr_url"] = ""
            state["pr_number"] = 0
            state["pr_error"] = str(e)
            state["current_phase"] = "pr_failed"
        
        return state
    
    async def _audit_node(self, state: OuroborosState) -> OuroborosState:
        """Node 9: AUDIT Agent logs everything"""
        logger.info("Logging audit trail")
        
        result = await self.audit_agent.execute({
            "workflow_state": state,
            "event_type": "workflow_complete"
        })
        
        state["audit_entries"] = result.get("audit_ids", [])
        state["current_phase"] = "complete"
        state["workflow_end_time"] = datetime.now().isoformat()
        
        return state
    
    # ===== CONDITIONAL ROUTING =====
    
    def _route_after_verification(self, state: OuroborosState) -> str:
        """
        Route after verification: retry or proceed.
        Max 10 retries (per 03_CRITICAL_DO_NOT_FILE).
        """
        MAX_RETRIES = 10
        
        if state["all_verified"]:
            return "proceed"
        
        if state.get("retry_count", 0) >= MAX_RETRIES:
            logger.warning(f"Max retries ({MAX_RETRIES}) reached. Proceeding with partial fixes.")
            return "proceed"
        
        logger.info(f"Retrying fixes (attempt {state.get('retry_count', 0) + 1})")
        return "retry"
    
    def _route_after_doc_final(self, state: OuroborosState) -> str:
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
            "scan_id": f"SCAN-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "user_id": input_data.get("user_id", "anonymous"),
            "scan_profile": input_data.get("scan_profile", "standard"),
            "commit_sha": input_data.get("commit_sha", "HEAD"),
            "branch": input_data.get("branch", "main"),
            "create_pr": input_data.get("create_pr", True),
            "workflow_start_time": datetime.now().isoformat(),
            "retry_count": 0,
            "vulnerabilities": [],
            "fixes": [],
            "verification_results": [],
            "errors": []
        }
        
        logger.info(f"Starting workflow for {input_data['repo_url']}")
        
        # Execute workflow
        final_state = await self.workflow.ainvoke(initial_state)
        
        logger.info(f"Workflow complete: {final_state.get('scan_id')}")
        
        return final_state


# Global workflow instance
workflow = OuroborosWorkflow()
