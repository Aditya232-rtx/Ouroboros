"""
Verification Router - Conditional edge after verification
Routes workflow based on verification results
"""

import logging
from src.orchestration.state import OuroborosState

logger = logging.getLogger(__name__)

MAX_RETRIES = 1  # User requirement: Single verification attempt only

def route_after_verification(state: OuroborosState) -> str:
    """
    Route after verification: retry failed fixes or abort.
    
    CRITICAL: Max 3 retry attempts. If verification fails 3 times,
    the workflow is ABORTED and proceeds to final documentation
    with partial fixes (if any).
    
    Returns:
        "retry" - Loop back to BLUE fix generation (if retries < 3)
        "proceed" - Continue to final documentation (success OR abort)
    """
    # Check if all fixes verified
    verified_count = sum(
        1 for r in state.get("verification_results", [])
        if r.get("verified", False)
    )
    total_count = len(state.get("verification_results", []))
    
    all_verified = (verified_count == total_count) and total_count > 0
    retry_count = state.get("retry_count", 0)
    
    
    # Logic is now simplified as state is updated in the previous node (check_verification)
    
    if all_verified:
        logger.info(f"✅ All {verified_count} fixes verified - proceeding to final documentation")
        return "proceed"
    
    # Check if we have exceeded max retries
    # Note: retry_count was already incremented in check_verification_node
    if retry_count > MAX_RETRIES:
        logger.error(
            f"❌ WORKFLOW ABORTED - Max retries ({MAX_RETRIES}) exhausted. "
            f"{verified_count}/{total_count} fixes verified. "
            f"Proceeding to final documentation with partial results."
        )
        # Note: We cannot easily set state['workflow_aborted'] here if we want to be pure.
        # Ideally, check_verification_node should have set it if count > max.
        # But for routing purposes, "proceed" is correct. 
        # The 'doc_final' node can check retry_count to know if it was an abort or success.
        return "proceed"
    
    # Attempts remain
    failed_count = total_count - verified_count
    logger.warning(
        f"⚠️  {failed_count}/{total_count} fixes failed verification. "
        f"Retry attempt {retry_count}/{MAX_RETRIES} - looping back to BLUE fix."
    )
    
    return "retry"
