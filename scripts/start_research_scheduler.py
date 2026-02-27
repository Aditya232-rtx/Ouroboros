"""
Ouroboros AI - Research Scheduler
Background daemon that runs Research Agent on a fixed schedule (default: 0, 8, 16 UTC).
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.scheduled_research import run_scheduled_research, should_run_now, get_next_run_time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def scheduler_loop():
    """
    Main scheduler loop.
    
    Checks every 5 minutes if it's time to run research.
    Runs research at scheduled hours (configured via RESEARCH_CYCLE_HOURS).
    """
    logger.info("🔬 Research Scheduler started")
    logger.info(f"Next scheduled run: {await get_next_run_time()}")
    
    last_run_hour = None
    
    while True:
        try:
            current_hour = datetime.now(timezone.utc).hour
            
            # Check if we should run now AND haven't run this hour yet
            if should_run_now() and current_hour != last_run_hour:
                logger.info(f"⏰ Triggering scheduled research (hour: {current_hour}:00 UTC)")
                
                # Run research
                result = await run_scheduled_research()
                
                # Log result
                if result["status"] == "success":
                    logger.info(
                        f"✅ Research complete: "
                        f"{result['blueprints_found']} findings, "
                        f"{result['exploits_written']} exploits written"
                    )
                elif result["status"] == "success_with_fallback":
                    logger.warning(
                        f"⚠️ Research complete (fallback mode): "
                        f"{result['blueprints_found']} findings exported to {result['export_path']}"
                    )
                elif result["status"] == "skipped":
                    logger.info(f"⏭️ Research skipped: {result.get('reason', 'unknown')}")
                else:
                    logger.error(f"❌ Research failed: {result.get('error', 'unknown')}")
                
                # Mark this hour as completed
                last_run_hour = current_hour
                
                # Sleep until next hour to avoid duplicate runs
                logger.info(f"Next scheduled run: {await get_next_run_time()}")
                await asyncio.sleep(3600)  # 1 hour
            else:
                # Not time to run yet, check again in 5 minutes
                await asyncio.sleep(300)
                
        except KeyboardInterrupt:
            logger.info("🛑 Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Scheduler error: {e}", exc_info=True)
            # Wait 5 minutes before retrying
            await asyncio.sleep(300)


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("OUROBOROS AI - RESEARCH SCHEDULER")
    logger.info("=" * 60)
    
    try:
        asyncio.run(scheduler_loop())
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")
