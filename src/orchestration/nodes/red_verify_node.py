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
    Node 5: RED Agent verifies fixes by re-attacking THE FIXED CODE
    
    CRITICAL: RED must attack the instance WHERE BLUE MADE FIXES,
    not the original vulnerable code. This verifies the fix actually works.
    
    Per 03_CRITICAL_DO_NOT: Must run in Docker sandbox
    Per USER REQUIREMENT: Max 3 retries, then abort
    """
    retry_attempt = state.get("retry_count", 0)
    logger.info(f"🔴 RED Verification starting (attempt {retry_attempt + 1}/3)...")
    logger.info("   ⚠️  Testing FIXED code instances (where BLUE made changes)")
    
    engine = VerificationEngine()
    
    verification_results = []
    for i, fix in enumerate(state["fixes"]):
        fix_id = fix.get("fix_id", f"FIX-{i}")
        vuln_id = fix.get("vulnerability_id", "UNKNOWN")
        
        logger.info(f"   [{i+1}/{len(state['fixes'])}] Verifying fix {fix_id} for {vuln_id}")
        
        # Get original vulnerability
        vuln = next(
            (v for v in state["vulnerabilities"] if v.get("id") == fix.get("vulnerability_id")),
            None
        )
        
        if not vuln:
            logger.error(f"   ❌ Original vulnerability not found for fix {fix_id}")
            verification_results.append({
                "fix_id": fix_id,
                "verified": False,
                "error": "Original vulnerability not found"
            })
            continue
        
        # Extract FIXED code from BLUE agent's output
        # This is the CODE AFTER BLUE MADE CHANGES
        fixed_code = fix.get("fixes", [{}])[0].get("code_diff", {}).get("after", "")
        
        if not fixed_code:
            logger.warning(f"   ⚠️  No fixed code found for {fix_id}, trying alternative path")
            fixed_code = fix.get("code_diff", {}).get("after", "")
        
        if not fixed_code:
            logger.error(f"   ❌ Cannot extract fixed code for {fix_id}")
            verification_results.append({
                "fix_id": fix_id,
                "verified": False,
                "error": "Fixed code not available"
            })
            continue
        
        # Verify fix in Docker sandbox - ATTACK THE FIXED CODE
        try:
            logger.info(f"   🎯 Attacking FIXED instance in Docker sandbox...")
            
            result = await engine.verify_fix(
                fix_code=fixed_code,  # ← FIXED code (BLUE's changes applied)
                original_vulnerability=vuln,
                sandbox=docker_sandbox
            )
            
            verification_results.append({
                "fix_id": fix_id,
                "vulnerability_id": vuln.get("id"),
                "verified": result.get("verified", False),
                "poc_failed": result.get("poc_failed", False),  # Good: exploit failed
                "details": result
            })
            
            if result.get("verified"):
                logger.info(f"   ✅ VERIFIED - Attack FAILED on fixed code (fix works!)")
            else:
                logger.warning(f"   ❌ FAILED - Attack SUCCEEDED on fixed code (fix ineffective)")
            
        except Exception as e:
            logger.error(f"   ❌ Verification exception for {fix_id}: {e}")
            verification_results.append({
                "fix_id": fix_id,
                "verified": False,
                "error": str(e)
            })
    
    state["verification_results"] = verification_results
    state["current_phase"] = "verification_complete"
    
    verified_count = sum(1 for r in verification_results if r.get("verified"))
    total = len(verification_results)
    
    logger.info(f"🏁 Verification round complete: {verified_count}/{total} fixes verified")
    
    if verified_count < total:
        logger.warning(f"   ⚠️  {total - verified_count} fixes still vulnerable - may retry")
    
    return state
