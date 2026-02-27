"""
Ouroboros AI - Startup Utilities

Helper functions for application initialization and cleanup.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def cleanup_incomplete_scans():
    """
    Mark all incomplete scans as failed/cancelled on server startup.
    
    This prevents orphaned scans from appearing as "in progress" when the
    server restarts. Any scan that was running when the server stopped will
    be marked as failed with an appropriate error message.
    
    Also kills any orphaned scan worker processes that may still be running.
    """
    import subprocess
    from src.database.session import SessionLocal
    from src.database.models import Scan, ScanStatus
    
    # Kill orphaned scan worker processes first
    try:
        # Kill any Python processes running scan_worker or OuroborosWorkflow
        result = subprocess.run(
            ["pkill", "-9", "-f", "scan_worker|OuroborosWorkflow|multiprocessing.*spawn"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("✅ Killed orphaned scan worker processes")
        else:
            logger.info("✅ No orphaned scan worker processes found")
    except Exception as e:
        logger.warning(f"Process cleanup skipped: {e}")
    
    # Update database status for incomplete scans
    db = SessionLocal()
    try:
        # Find scans that were running when server stopped
        incomplete_statuses = [
            ScanStatus.PENDING,
            ScanStatus.SCANNING,
            ScanStatus.GENERATING_FIXES,
            ScanStatus.VERIFYING,
            ScanStatus.CREATING_PR
        ]
        
        incomplete_scans = db.query(Scan).filter(
            Scan.status.in_(incomplete_statuses)
        ).all()
        
        if incomplete_scans:
            logger.warning(f"Found {len(incomplete_scans)} incomplete scans from previous session")
            
            for scan in incomplete_scans:
                scan.status = ScanStatus.FAILED
                scan.error_message = "Server restarted - scan cancelled"
                scan.completed_at = datetime.now(timezone.utc)
                logger.info(f"  ✗ Cancelled scan {scan.scan_id}")
            
            db.commit()
            logger.info(f"✅ Cleaned up {len(incomplete_scans)} incomplete scans")
        else:
            logger.info("✅ No incomplete scans found - clean state")
            
    except Exception as e:
        logger.error(f"❌ Error during scan cleanup: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
