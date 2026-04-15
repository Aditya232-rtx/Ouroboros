"""
Ouroboros AI - Scan Worker Module

Runs security scans in separate processes to avoid blocking the FastAPI event loop.
Uses ProcessPoolExecutor for complete isolation.
"""

import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from enum import Enum

from src.database.session import SessionLocal
from src.database.models import Scan, ScanLog, ScanStatus
from src.orchestration.workflow import OuroborosWorkflow
from src.utils.memory_logger import RedisScanLogHandler
from src.database.redis import get_redis_client


def _json_safe(obj):
    """Recursively convert non-serializable objects (Enums, dataclasses) to JSON-safe types."""
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(i) for i in obj]
    if hasattr(obj, '__dataclass_fields__'):
        return {k: _json_safe(getattr(obj, k)) for k in obj.__dataclass_fields__}
    return obj

logger = logging.getLogger(__name__)


def run_scan_in_process(scan_id: str, request_data: Dict[str, Any]) -> None:
    """
    Execute a security scan in a separate process.
    
    This function is designed to run in a ProcessPoolExecutor, completely
    isolated from the main FastAPI event loop. It handles its own database
    connections and logging.
    
    Args:
        scan_id: Unique scan identifier
        request_data: Dictionary containing scan configuration
            - repo_url: Repository URL to scan
            - branch: Git branch (optional)
            - commit_sha: Specific commit (optional)
            - scan_profile: "quick", "standard", or "deep"
            - auto_fix: Whether to auto-apply fixes
            - create_pr: Whether to create PR with fixes
    """
    # Create fresh DB session for this process
    db = SessionLocal()
    log_handler = None
    scan = None
    
    try:
        # Fetch scan record
        scan = db.query(Scan).filter(Scan.scan_id == scan_id).first()
        if not scan:
            logger.error(f"Scan {scan_id} not found in DB during execution")
            return

        # Update status to scanning
        scan.status = ScanStatus.SCANNING
        scan.started_at = datetime.now(timezone.utc)
        scan.scan_metadata = {"current_phase": "initializing"}
        db.commit()

        # Attach Redis Logger (Buffer logs)
        log_handler = RedisScanLogHandler(scan.scan_id)
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        
        logger.info(f"🚀 Starting scan {scan_id} for {request_data['repo_url']}")
        
        # Initialize workflow
        workflow = OuroborosWorkflow()
        
        # Prepare input data for workflow
        input_data = {
            "scan_id": scan_id,
            "repo_url": request_data["repo_url"],
            "branch": request_data.get("branch", "main"),
            "commit_sha": request_data.get("commit_sha", "HEAD"),
            "scan_profile": request_data.get("scan_profile", "standard"),
            "auto_fix": request_data.get("auto_fix", False),
            "create_pr": request_data.get("create_pr", False),
        }
        
        # Run workflow synchronously in this process
        # Use new event loop since we're in a separate process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(workflow.run(input_data))
        finally:
            # Cancel any pending tasks to avoid 'Future exception was never retrieved'
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
        
        # Update scan with results (sanitize enums/dataclasses for JSON)
        safe_result = _json_safe(result)
        vulnerabilities = safe_result.get("vulnerabilities", []) or []
        verification_results = safe_result.get("verification_results", []) or []
        verified_count = sum(
            1
            for item in verification_results
            if isinstance(item, dict) and item.get("verified")
        )

        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.now(timezone.utc)
        scan.vulnerabilities_found = len(vulnerabilities)
        scan.fixes_verified = verified_count
        scan.pr_url = safe_result.get("pr_url") or scan.pr_url
        scan.pr_number = safe_result.get("pr_number") or scan.pr_number
        scan.report_url = safe_result.get("final_report_url") or scan.report_url
        scan.scan_metadata = {
            "current_phase": "completed",
            "vulnerabilities_found": len(vulnerabilities),
            "fixes_applied": verified_count,
            "result": safe_result
        }
        db.commit()
        
        logger.info(f"✅ Scan {scan_id} completed successfully")

        
    except Exception as e:
        logger.error(f"❌ Scan {scan_id} failed: {e}", exc_info=True)
        scan = db.query(Scan).filter(Scan.scan_id == scan_id).first()
        if scan:
            scan.status = ScanStatus.FAILED
            scan.error_message = str(e)
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
    
    finally:
        # Remove log handler
        if log_handler:
            root_logger = logging.getLogger()
            root_logger.removeHandler(log_handler)
        
        # Persist Redis logs to DB
        if scan:
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
        logger.info(f"Scan worker process for {scan_id} finished")
