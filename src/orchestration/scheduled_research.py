"""
Ouroboros AI - Scheduled Research Agent
Background job that runs independently from main workflow on a fixed schedule.
"""

import logging
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from src.agents.research_agent import research_app

logger = logging.getLogger(__name__)


async def run_scheduled_research() -> dict:
    """
    Execute scheduled research agent job.
    
    This runs independently from the main workflow, updating dynamic_exploits.py
    or exporting findings to markdown if file write fails.
    
    Schedule controlled by RESEARCH_CYCLE_HOURS environment variable (default: 0,8,16 UTC).
    
    Returns:
        dict: {
            "status": "success" | "error" | "skipped",
            "blueprints_found": int,
            "exploits_written": int,
            "export_path": str (if markdown fallback used)
        }
    """
    
    # Check if research agent is enabled
    if not os.getenv("OUROBOROS_RESEARCH_AGENT_ENABLED", "true").lower() == "true":
        logger.info("RESEARCH_OFFLINE: Research Agent disabled via env var")
        return {
            "status": "skipped",
            "reason": "disabled",
            "blueprints_found": 0,
            "exploits_written": 0
        }
    
    # Check if current hour matches the research cycle schedule
    cycle_hours_str = os.getenv("RESEARCH_CYCLE_HOURS", "0,8,16")
    cycle_hours = [int(h.strip()) for h in cycle_hours_str.split(",")]
    current_hour = datetime.now(timezone.utc).hour
    
    if current_hour not in cycle_hours:
        logger.info(
            f"RESEARCH_SKIPPED: Current hour {current_hour} UTC not in cycle schedule {cycle_hours}"
        )
        next_cycle = min([h for h in cycle_hours if h > current_hour], default=cycle_hours[0])
        return {
            "status": "skipped",
            "reason": f"not_scheduled (next at {next_cycle}:00 UTC)",
            "blueprints_found": 0,
            "exploits_written": 0
        }
    
    logger.info(f"Starting scheduled threat research (cycle: {current_hour}:00 UTC)...")
    
    try:
        # Use the new LangGraph-based research agent
        # Feed it a default NVD query URL for recent critical CVEs
        initial_state = {
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2021-44228",
            "raw_markdown": "",
            "extracted_json": {},
            "error_message": "",
            "retry_count": 0
        }
        
        final_state = await research_app.ainvoke(initial_state)
        
        extracted = final_state.get("extracted_json", {})
        dispatched = final_state.get("error_message") == "dispatched"
        
        if extracted:
            cve_id = extracted.get("id", "UNKNOWN")
            logger.info(f"Research complete: CVE {cve_id} analyzed and dispatched={dispatched}")
            return {
                "status": "success",
                "blueprints_found": 1,
                "exploits_written": 1 if dispatched else 0,
                "cve_id": cve_id
            }
        else:
            logger.info("Research complete: No new intelligence extracted (memory hit or parse failure)")
            return {
                "status": "success",
                "blueprints_found": 0,
                "exploits_written": 0,
                "message": "No new threats discovered or already researched"
            }
    
    except Exception as e:
        logger.error(f"RESEARCH_FAILED: Scheduled research failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "blueprints_found": 0,
            "exploits_written": 0
        }


def should_run_now() -> bool:
    """
    Check if research should run at the current time.
    
    Returns:
        bool: True if current hour matches RESEARCH_CYCLE_HOURS
    """
    if not os.getenv("OUROBOROS_RESEARCH_AGENT_ENABLED", "true").lower() == "true":
        return False
    
    cycle_hours_str = os.getenv("RESEARCH_CYCLE_HOURS", "0,8,16")
    cycle_hours = [int(h.strip()) for h in cycle_hours_str.split(",")]
    current_hour = datetime.now(timezone.utc).hour
    
    return current_hour in cycle_hours


async def get_next_run_time() -> str:
    """
    Get the next scheduled run time in human-readable format.
    
    Returns:
        str: Next run time (e.g., "16:00 UTC")
    """
    cycle_hours_str = os.getenv("RESEARCH_CYCLE_HOURS", "0,8,16")
    cycle_hours = [int(h.strip()) for h in cycle_hours_str.split(",")]
    current_hour = datetime.now(timezone.utc).hour
    
    next_hour = min([h for h in cycle_hours if h > current_hour], default=cycle_hours[0])
    
    return f"{next_hour:02d}:00 UTC"
