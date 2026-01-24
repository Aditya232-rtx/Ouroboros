"""
Error Handler - Error recovery routing
Handles errors and determines recovery path
"""

import logging
from typing import Dict, Any
from src.orchestration.state import OuroborosState

logger = logging.getLogger(__name__)

def handle_error(state: OuroborosState, error: Exception) -> str:
    """
    Handle workflow errors and determine recovery path.
    
    Args:
        state: Current workflow state
        error: Exception that occurred
        
    Returns:
        Recovery action: "retry"|"skip"|"abort"
    """
    error_type = type(error).__name__
    error_msg = str(error)
    current_phase = state.get("current_phase", "unknown")
    
    logger.error(f"Error in phase '{current_phase}': {error_type} - {error_msg}")
    
    # Add error to state
    if "errors" not in state:
        state["errors"] = []
    
    state["errors"].append({
        "phase": current_phase,
        "type": error_type,
        "message": error_msg
    })
    
    # Determine recovery action
    if "rate_limit" in error_msg.lower():
        logger.warning("Rate limit detected - retrying after backoff")
        return "retry"
    
    elif "timeout" in error_msg.lower():
        logger.warning("Timeout detected - retrying with longer timeout")
        return "retry"
    
    elif "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
        logger.error("Authentication error - cannot recover")
        return "abort"
    
    elif current_phase in ["scan_complete", "fixes_generated"]:
        # Critical phases - abort on error
        logger.error(f"Critical error in {current_phase} - aborting")
        return "abort"
    
    else:
        # Non-critical phases - skip and continue
        logger.warning(f"Non-critical error in {current_phase} - skipping")
        return "skip"
