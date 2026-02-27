"""
Ouroboros AI - Startup Utilities

Helper functions for application initialization and cleanup.
All functions here are best-effort: a failure never crashes the server.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def cleanup_incomplete_scans():
    """
    Mark all incomplete scans as failed/cancelled on server startup.
    Fully wrapped in try/except so postgres being unavailable won't prevent
    uvicorn from starting.
    """
    try:
        import subprocess
        from src.database.session import SessionLocal
        from src.database.models import Scan, ScanStatus

        # Kill orphaned scan worker processes
        try:
            result = subprocess.run(
                ["pkill", "-9", "-f", "scan_worker|OuroborosWorkflow|multiprocessing.*spawn"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                logger.info("[OK] Killed orphaned scan worker processes")
            else:
                logger.info("[OK] No orphaned scan worker processes found")
        except Exception as e:
            logger.warning(f"Process cleanup skipped: {e}")

        # Update database status for incomplete scans
        db = SessionLocal()
        try:
            incomplete_statuses = [
                ScanStatus.PENDING,
                ScanStatus.SCANNING,
                ScanStatus.GENERATING_FIXES,
                ScanStatus.VERIFYING,
                ScanStatus.CREATING_PR,
            ]
            incomplete_scans = db.query(Scan).filter(
                Scan.status.in_(incomplete_statuses)
            ).all()

            if incomplete_scans:
                logger.warning(f"Found {len(incomplete_scans)} incomplete scans from previous session")
                for scan in incomplete_scans:
                    scan.status = ScanStatus.FAILED
                    scan.error_message = "Server restarted - scan cancelled"
                    scan.completed_at = datetime.utcnow()
                    logger.info(f"  Cancelled scan {scan.scan_id}")
                db.commit()
                logger.info(f"[OK] Cleaned up {len(incomplete_scans)} incomplete scans")
            else:
                logger.info("[OK] No incomplete scans found - clean state")

        except Exception as e:
            logger.error(f"Error during scan cleanup: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

    except Exception as e:
        logger.warning(f"Startup scan cleanup skipped (DB unavailable): {e}")
