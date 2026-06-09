"""
RED Verify Node - Fix verification through re-attack
Orchestration node for RED agent verification
"""

import logging
from typing import Dict, Any
from src.orchestration.state import OuroborosState
from src.verification.verification_engine import VerificationEngine
from src.tools.docker_sandbox import docker_sandbox

logger = logging.getLogger(__name__)

async def red_verify_node(state: OuroborosState) -> OuroborosState:
    """
    Node 5: RED Agent verifies fixes by re-attacking
    
    Per 03_CRITICAL_DO_NOT: Must run in Docker sandbox
    Per VERIFICATION_LOOP: Max 10 retries
    """
    logger.info("🔴 RED Verification starting...")
    
    engine = VerificationEngine()
    
    verification_results = []
    for fix in state["fixes"]:
        # Get original vulnerability
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
        
        # Verify fix in Docker sandbox
        try:
            result = await engine.verify_fix(
                fix_code=fix.get("fixes", [{}])[0].get("code_diff", {}).get("after", ""),
                original_vulnerability=vuln,
                sandbox=docker_sandbox
            )
            
            verification_results.append({
                "fix_id": fix.get("fix_id"),
                "vulnerability_id": vuln.get("id"),
                "verified": result.get("verified", False),
                "poc_failed": result.get("poc_failed", False),
                "details": result
            })
            
            status = "✅ VERIFIED" if result.get("verified") else "❌ FAILED"
            logger.info(f"Fix {fix.get('fix_id')}: {status}")
            
        except Exception as e:
            logger.error(f"Verification failed for {fix.get('fix_id')}: {e}")
            verification_results.append({
                "fix_id": fix.get("fix_id"),
                "verified": False,
                "error": str(e)
            })
    
    state["verification_results"] = verification_results
    state["current_phase"] = "verification_complete"
    
    verified_count = sum(1 for r in verification_results if r.get("verified"))
    logger.info(f"✅ Verification complete: {verified_count}/{len(verification_results)} fixes verified")
    
    return state
