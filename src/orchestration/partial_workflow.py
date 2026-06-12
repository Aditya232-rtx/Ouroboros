"""
Partial Workflow - Start from BLUE agent using existing RED outputs

This workflow skips vulnerability detection and reuses existing scan results.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from src.orchestration.graphs.partial_graph import create_partial_workflow_graph
from src.orchestration.state import OuroborosState

logger = logging.getLogger(__name__)


class PartialOuroborosWorkflow:
    """
    Partial workflow execution starting from GOVERNANCE/BLUE.
    Reuses existing RED agent vulnerability outputs.
    """
    
    def __init__(self):
        """Initialize partial workflow with simplified graph."""
        self.workflow = create_partial_workflow_graph()
        logger.info("PartialOuroborosWorkflow initialized")
    
    async def run_from_blue(
        self,
        scan_id: str,
        red_output_path: str,
        repo_url: str,
        branch: str = "main",
        create_pr: bool = True
    ) -> Dict[str, Any]:
        """
        Start workflow from GOVERNANCE using existing RED output.
        
        Args:
            scan_id: Unique scan identifier
            red_output_path: Path to RED agent context JSON file
            repo_url: Repository URL for PR creation
            branch: Git branch (default: main)
            create_pr: Whether to create PR (default: True)
        
        Returns:
            Final workflow state with fixes, verification results, and PR info
        """
        logger.info(f"🔄 Starting partial workflow {scan_id}")
        logger.info(f"   Loading RED output from: {red_output_path}")
        
        # Load RED agent output
        red_output_file = Path(red_output_path)
        if not red_output_file.exists():
            raise FileNotFoundError(f"RED output not found: {red_output_path}")
        
        with open(red_output_file, 'r') as f:
            red_data = json.load(f)
        
        vulnerabilities = red_data.get("vulnerabilities", [])
        logger.info(f"   Loaded {len(vulnerabilities)} vulnerabilities")
        
        # Initialize state at GOVERNANCE entry point
        initial_state: OuroborosState = {
            "scan_id": scan_id,
            "repo_url": repo_url,
            "branch": branch,
            "commit_sha": "HEAD",
            "scan_profile": "partial",
            "create_pr": create_pr,
            "working_dir": "",  # Will be set if needed
            "workflow_start_time": datetime.now().isoformat(),
            "current_phase": "governance",
            "retry_count": 0,
            "workflow_aborted": False,
            "abort_reason": None,
            
            # Pre-populated from RED output
            "vulnerabilities": vulnerabilities,
            "scan_complete": True,  # RED already completed
            "scan_statistics": red_data.get("statistics", {}),
            "initial_report_url": red_data.get("report_url"),
            "initial_report_id": red_data.get("report_id"),
            
            # To be filled by workflow
            "prioritized_queue": [],
            "governance_decisions": {},
            "risk_scores": {},
            "fixes": [],
            "verification_results": [],
            "all_verified": False,
            "final_report_url": None,
            "final_report_id": None,
            "pr_url": None,
            "pr_number": None,
            "pr_error": None,
            "audit_entries": [],
            "workflow_end_time": None,
            "errors": []
        }
        
        logger.info(f"🚀 Executing partial workflow: GOVERNANCE → BLUE → VERIFY → DOC → PR")
        
        # Execute workflow starting from GOVERNANCE
        final_state = await self.workflow.ainvoke(initial_state)
        
        # Check results
        if final_state.get("workflow_aborted"):
            logger.warning(f"⚠️  Partial workflow aborted: {final_state.get('abort_reason')}")
        else:
            logger.info(f"✅ Partial workflow complete: {final_state.get('scan_id')}")
        
        pr_url = final_state.get("pr_url")
        if pr_url:
            logger.info(f"   📋 PR created: {pr_url}")
        
        return final_state
