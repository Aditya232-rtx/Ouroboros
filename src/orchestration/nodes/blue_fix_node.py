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
    On retry: only re-fixes failed vulnerabilities and passes verification feedback.
    """
    retry_count = state.get("retry_count", 0)
    logger.info(f"🔵 BLUE Fix generation (attempt {retry_count + 1})")
    
    blue_agent = BLUEAgent()
    
    # On retry: identify which vulnerabilities failed verification
    verification_results = state.get("verification_results", [])
    failed_vuln_ids = set()
    if retry_count > 0 and verification_results:
        failed_vuln_ids = {
            r.get("vulnerability_id") for r in verification_results
            if not r.get("verified", False)
        }
        logger.info(f"   Retry mode: re-fixing {len(failed_vuln_ids)} failed vulnerabilities")
    
    # Determine which vulnerabilities need fixes
    vulns_to_fix = state["prioritized_queue"]
    if failed_vuln_ids:
        vulns_to_fix = [v for v in vulns_to_fix if v.get("id") in failed_vuln_ids]
    
    # Resolve sandbox_path from state (allows BLUE to read actual source files)
    sandbox_path = ""
    sandbox_info = state.get("sandbox_info")
    if isinstance(sandbox_info, dict):
        sandbox_path = sandbox_info.get("working_dir", "") or sandbox_info.get("path", "")
    elif isinstance(sandbox_info, str):
        sandbox_path = sandbox_info
    
    # Keep previously verified fixes on retry
    fixes = []
    if retry_count > 0 and state.get("fixes"):
        fixes = [
            f for f in state["fixes"]
            if f.get("vulnerability_id") not in failed_vuln_ids
        ]
        logger.info(f"   Keeping {len(fixes)} previously verified fixes")
    
    for vuln in vulns_to_fix:
        vuln_id = vuln.get("id")
        logger.info(f"Generating fix for {vuln_id}: {vuln.get('type')}")
        
        exec_input = {
            "vulnerability_id": vuln_id,
            "vulnerability_type": vuln.get("type"),
            "vulnerability_location": vuln.get("location", {}),
            "vulnerable_code": vuln.get("code_snippet", ""),
            "cwe": vuln.get("cwe", ""),
            "cvss": vuln.get("cvss", 0.0),
            "sandbox_path": sandbox_path,
        }
        
        # On retry: pass feedback about why the previous fix failed
        if retry_count > 0:
            prev_result = next(
                (r for r in verification_results if r.get("vulnerability_id") == vuln_id),
                None
            )
            if prev_result:
                exec_input["retry_feedback"] = (
                    f"Previous fix attempt {retry_count} FAILED verification. "
                    f"Reason: {prev_result.get('details', {}).get('reason', 'unknown')}. "
                    f"Try a fundamentally different approach."
                )
        
        result = await blue_agent.execute(exec_input)
        fixes.append(result)
    
    state["fixes"] = fixes
    state["current_phase"] = "fixes_generated"
    
    logger.info(f"✅ Fix generation complete: {len(fixes)} fixes created")
    
    return state
