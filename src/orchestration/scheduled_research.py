"""
Ouroboros AI - Scheduled Research Agent
Background job that runs independently from main workflow on a fixed schedule.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

from src.agents.research_agent import ResearchAgent

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
    current_hour = datetime.utcnow().hour
    
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
        # Initialize Research Agent
        research_agent = ResearchAgent()
        
        # Get tech stack from environment or use defaults
        tech_stack_str = os.getenv(
            "RESEARCH_TECH_STACK",
            "python,javascript,react,express,django,flask,fastapi,node,typescript"
        )
        tech_stack = [t.strip() for t in tech_stack_str.split(",")]
        
        # Execute research
        result = await research_agent.execute({
            "tech_stack": tech_stack,
            "freshness": "30d",
            "max_results_per_tech": 10
        })
        
        blueprints = result.get("blueprints", [])
        total_discovered = result.get("total_discovered", 0)
        
        logger.info(f"Research complete: {total_discovered} new threats discovered")
        
        if not blueprints:
            return {
                "status": "success",
                "blueprints_found": 0,
                "exploits_written": 0,
                "message": "No new threats discovered"
            }
        
        # Try to write dynamic exploits module
        try:
            exploits_written = await research_agent.write_dynamic_exploits_module(blueprints)
            
            logger.info(
                f"RESEARCH_SUCCESS: Generated {exploits_written} dynamic exploits",
                extra={
                    "event": "research_completed",
                    "blueprints_found": total_discovered,
                    "exploits_written": exploits_written,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "status": "success",
                "blueprints_found": total_discovered,
                "exploits_written": exploits_written,
                "module_path": "src/security/tools/dynamic_exploits.py"
            }
            
        except Exception as write_error:
            logger.warning(
                f"Failed to write dynamic_exploits.py: {write_error}. "
                "Falling back to markdown export."
            )
            
            # Fallback: Export to markdown
            export_dir = Path(os.getenv("RESEARCH_FINDINGS_DIR", "./research_findings"))
            export_dir.mkdir(parents=True, exist_ok=True)
            
            export_filename = f"research_findings_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.md"
            export_path = export_dir / export_filename
            
            await research_agent.export_to_markdown(blueprints, str(export_path))
            
            logger.info(
                f"RESEARCH_FALLBACK: Exported {total_discovered} findings to {export_path}",
                extra={
                    "event": "research_markdown_export",
                    "blueprints_found": total_discovered,
                    "export_path": str(export_path),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "status": "success_with_fallback",
                "blueprints_found": total_discovered,
                "exploits_written": 0,
                "export_path": str(export_path),
                "fallback_reason": str(write_error)
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
    current_hour = datetime.utcnow().hour
    
    return current_hour in cycle_hours


async def get_next_run_time() -> str:
    """
    Get the next scheduled run time in human-readable format.
    
    Returns:
        str: Next run time (e.g., "16:00 UTC")
    """
    cycle_hours_str = os.getenv("RESEARCH_CYCLE_HOURS", "0,8,16")
    cycle_hours = [int(h.strip()) for h in cycle_hours_str.split(",")]
    current_hour = datetime.utcnow().hour
    
    next_hour = min([h for h in cycle_hours if h > current_hour], default=cycle_hours[0])
    
    return f"{next_hour:02d}:00 UTC"
