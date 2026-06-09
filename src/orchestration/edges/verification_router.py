"""
Verification Router - Conditional edge after verification
Routes workflow based on verification results
"""

import logging
from src.orchestration.state import OuroborosState

logger = logging.getLogger(__name__)

MAX_RETRIES = 10  # Per 03_CRITICAL_DO_NOT_FILE

def route_after_verification(state: OuroborosState) -> str:
    """
    Route after verification: retry failed fixes or proceed to PR creation.
    
    Per spec: Max 10 retries to prevent infinite loops.
    
    Returns:
        "retry" - Loop back to BLUE fix generation
        "proceed" - Continue to documentation and PR creation
    """
    # Check if all fixes verified
    verified_count = sum(
        1 for r in state.get("verification_results", [])
        if r.get("verified", False)
    )
    total_count = len(state.get("verification_results", []))
    
    all_verified = (verified_count == total_count) and total_count > 0
    retry_count = state.get("retry_count", 0)
    
    if all_verified:
        logger.info(f"✅ All {verified_count} fixes verified - proceeding to PR creation")
        return "proceed"
    
    if retry_count >= MAX_RETRIES:
        logger.warning(
            f"⚠️  Max retries ({MAX_RETRIES}) reached. "
            f"{verified_count}/{total_count} verified. Proceeding with partial fixes."
        )
        return "proceed"
    
    # Not all verified, retry
    failed_count = total_count - verified_count
    logger.info(
        f"🔄 {failed_count} fixes failed verification. "
        f"Retrying (attempt {retry_count + 1}/{MAX_RETRIES})"
    )
    
    # Increment retry count
    state["retry_count"] = retry_count + 1
    
    return "retry"
