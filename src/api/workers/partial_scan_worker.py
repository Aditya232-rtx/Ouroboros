"""
Partial Scan Worker - Execute partial workflow in separate process

Loads existing RED output and runs GOVERNANCE → BLUE → VERIFY → DOC → PR workflow.
"""

import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from src.database.session import SessionLocal
from src.database.models import Scan, ScanLog, ScanStatus
from src.orchestration.partial_workflow import PartialOuroborosWorkflow
from src.utils.memory_logger import RedisScanLogHandler
from src.database.redis import get_redis_client

logger = logging.getLogger(__name__)


def run_partial_scan_in_process(scan_id: str, request_data: Dict[str, Any]) -> None:
    """
    Execute partial security workflow in a separate process.
    
    This function runs GOVERNANCE+BLUE+VERIFY+DOC+PR workflow using existing
    RED agent vulnerability data, skipping the vulnerability detection phase.
    
    Args:
        scan_id: Unique scan identifier
        request_data: Dictionary containing:
            - red_output_path: Path to RED agent context JSON
            - repo_url: Repository URL
            - branch: Git branch (optional)
            - create_pr: Whether to create PR (optional)
    """
    # Create fresh DB session for this process
    db = SessionLocal()
    
    try:
        # Fetch scan record
        scan = db.query(Scan).filter(Scan.scan_id == scan_id).first()
        if not scan:
            logger.error(f"Scan {scan_id} not found in DB during execution")
            return

        # Update status to generating fixes
        scan.status = ScanStatus.GENERATING_FIXES
        scan.started_at = datetime.now(timezone.utc)
        scan.scan_metadata = {"current_phase": "governance", "partial": True}
        db.commit()

        # Attach Redis Logger
        log_handler = RedisScanLogHandler(scan.scan_id)
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        
        logger.info(f"🔄 Starting partial workflow {scan_id}")
        logger.info(f"   RED output: {request_data['red_output_path']}")
        
        # Initialize and run partial workflow
        workflow = PartialOuroborosWorkflow()
        
        # Prepare input data
        input_data = {
            "scan_id": scan_id,
            "red_output_path": request_data["red_output_path"],
            "repo_url": request_data["repo_url"],
            "branch": request_data.get("branch", "main"),
            "create_pr": request_data.get("create_pr", True)
        }
        
        # Run workflow in this process's event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(workflow.run_from_blue(**input_data))
        finally:
            loop.close()
        
        # Update scan with results (sanitize enums/dataclasses for JSON)
        from src.api.workers.scan_worker import _json_safe
        safe_result = _json_safe(result)
        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.now(timezone.utc)
        scan.scan_metadata = {
            "current_phase": "completed",
            "partial": True,
            "vulnerabilities_found": len(safe_result.get("vulnerabilities", [])),
            "fixes_applied": len(safe_result.get("fixes", [])),
            "pr_url": safe_result.get("pr_url"),
            "result": safe_result
        }
        db.commit()
        
        logger.info(f"✅ Partial workflow {scan_id} completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Partial workflow {scan_id} failed: {e}", exc_info=True)
        scan = db.query(Scan).filter(Scan.scan_id == scan_id).first()
        if scan:
            scan.status = ScanStatus.FAILED
            scan.error_message = str(e)
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
    
    finally:
        # Remove log handler (may not exist if exception before assignment)
        if 'log_handler' in dir():
            root_logger = logging.getLogger()
            root_logger.removeHandler(log_handler)
        
        # Persist Redis logs to DB
        if 'scan' in dir() and scan:
            try:
                redis_client = get_redis_client()
                redis_key = f"scan:{scan_id}:logs"
                raw_logs = redis_client.lrange(redis_key, 0, -1)
                
                if raw_logs:
                    new_db_logs = []
                    for raw in raw_logs:
                        log_data = json.loads(raw)
                        new_db_logs.append(ScanLog(
                            scan_id=scan.id,
                            timestamp=datetime.now(timezone.utc),
                            level=log_data.get("level", "info").upper(),
                            source=log_data.get("source", "SYSTEM"),
                            message=log_data.get("message", "")
                        ))
                    db.add_all(new_db_logs)
                    db.commit()
                    logger.info(f"Persisted {len(new_db_logs)} logs to DB for scan {scan_id}")
            except Exception as e:
                logger.error(f"Failed to persist logs to DB for {scan_id}: {e}")
        
        # Close database connection
        db.close()
        logger.info(f"Partial workflow worker for {scan_id} finished")
