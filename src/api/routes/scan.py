# src/api/routes/scan.py
"""Scan endpoint for initiating security scans with non-blocking execution."""

import logging
import asyncio
from datetime import datetime
from uuid import uuid4
from concurrent.futures import ProcessPoolExecutor
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.api.schemas import (
    ScanRequest,
    ScanResponse,
    ScanStatus as API_ScanStatus,
    ErrorResponse,
)
from src.database.models import Scan, ScanStatus, ScanLog, Vulnerability, Fix
from src.database.session import get_db_session, SessionLocal
from src.api.workers import run_scan_in_process
from src.database.redis import get_redis_client
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["scan"])

# Process pool for running scans in isolated processes  
# Max 2 concurrent scans to avoid overwhelming system resources
scan_executor = ProcessPoolExecutor(max_workers=2)



@router.post(
    "",
    response_model=ScanResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Initiate a security scan",
)
async def create_scan(
    request: ScanRequest,
    db: Session = Depends(get_db_session),
) -> ScanResponse:
    """Initiate a security scan (Persisted)."""
    scan_id = f"SCAN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    
    logger.info(f"Creating scan {scan_id} for {request.repo_url}")
    
    # Create DB Record
    new_scan = Scan(
        scan_id=scan_id,
        repo_url=request.repo_url,
        branch=request.branch or "main",
        commit_sha=request.commit_sha,
        status=ScanStatus.PENDING,
        scan_profile=request.scan_profile,
        created_at=datetime.utcnow(),
        scan_metadata={"current_phase": "pending"}
    )
    db.add(new_scan)
    db.commit()
    db.refresh(new_scan)
    
    # Submit scan to process pool (non-blocking)
    loop = asyncio.get_event_loop()
    request_data = {
        "repo_url": request.repo_url,
        "branch": request.branch or "main",
        "commit_sha": request.commit_sha or "HEAD",
        "scan_profile": request.scan_profile,
        "auto_fix": request.auto_fix,
        "create_pr": request.create_pr,
    }
    
    loop.run_in_executor(scan_executor, run_scan_in_process, scan_id, request_data)
    
    logger.info(f"✅ Scan {scan_id} queued in separate process for {request.repo_url}")
    
    
    # Submit scan to process pool (non-blocking)
    loop = asyncio.get_event_loop()
    request_data = {
        "repo_url": request.repo_url,
        "branch": request.branch or "main",
        "commit_sha": request.commit_sha or "HEAD",
        "scan_profile": request.scan_profile,
        "auto_fix": request.auto_fix,
        "create_pr": request.create_pr,
    }
    
    loop.run_in_executor(scan_executor, run_scan_in_process, scan_id, request_data)
    
    logger.info(f"✅ Scan {scan_id} queued in separate process for {request.repo_url}")
    
    return ScanResponse(
        scan_id=scan_id,
        status=API_ScanStatus.PENDING,
        message=f"Scan queued for {request.repo_url}",
        created_at=new_scan.created_at,
    )
    return ScanResponse(
        scan_id=scan_id,
        status=API_ScanStatus.PENDING,
        message=f"Scan queued for {request.repo_url}",
        created_at=new_scan.created_at,
    )


@router.get(
    "/{scan_id}",
    response_model=ScanResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get scan info",
)
async def get_scan(scan_id: str, db: Session = Depends(get_db_session)) -> ScanResponse:
    """Get basic scan information."""
    scan = db.query(Scan).filter(Scan.scan_id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    
    status_str = scan.status.value if hasattr(scan.status, 'value') else str(scan.status)
    try:
        api_status = API_ScanStatus(status_str)
    except:
        api_status = API_ScanStatus.PENDING

    phase = scan.scan_metadata.get("current_phase", "unknown") if scan.scan_metadata else "unknown"

    return ScanResponse(
        scan_id=scan.scan_id,
        status=api_status,
        message=f"Phase: {phase}",
        created_at=scan.created_at,
    )


def get_scan_data(scan_id: str) -> dict:
    """
    Get scan data using Redis (hot logs) then DB (cold logs).
    """
    db = SessionLocal()
    try:
        if scan_id == "latest":
            scan = db.query(Scan).order_by(desc(Scan.created_at)).first()
        else:
            scan = db.query(Scan).filter(Scan.scan_id == scan_id).first()
            
        if not scan:
            return None
            
        status_val = scan.status.value if hasattr(scan.status, 'value') else str(scan.status)
        if status_val == "scanning": status_val = "running" 

        meta = scan.scan_metadata or {}
        
        # FETCH LOGS: Try Redis First
        logs_list = []
        try:
            redis_client = get_redis_client()
            redis_key = f"scan:{scan.scan_id}:logs"
            raw_logs = redis_client.lrange(redis_key, 0, -1)
            
            if raw_logs:
                logs_list = [json.loads(l) for l in raw_logs]
            else:
                # Fallback to DB if Redis empty (completed/expired)
                db_logs = db.query(ScanLog).filter(ScanLog.scan_id == scan.id).order_by(ScanLog.timestamp).all()
                logs_list = [{
                    "id": str(l.id),
                    "timestamp": l.timestamp.strftime('%H:%M:%S'),
                    "level": l.level.lower(),
                    "source": l.source,
                    "message": l.message
                } for l in db_logs]
        except Exception as e:
            logger.error(f"Error fetching logs: {e}")

        return {
            "scan_id": scan.scan_id,
            "repo_url": scan.repo_url, # <--- Added
            "status": status_val,
            "current_phase": meta.get("current_phase", "unknown"),
            "progress_percent": 0,
            "vulnerabilities_found": scan.vulnerabilities_found,
            "fixes_applied": scan.fixes_verified,
            "started_at": scan.started_at,
            "completed_at": scan.completed_at,
            "error_message": scan.error_message,
            "result": meta.get("result"),
            "scan_metadata": meta, # <--- Added this
            "pr_url": scan.pr_url,
            "logs": logs_list
        }
    finally:
        db.close()


@router.post(
    "/from-existing",
    response_model=ScanResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Run partial workflow from existing RED output",
)
async def create_scan_from_existing(
    red_output_path: str,
    repo_url: str,
    branch: str = "main",
    create_pr: bool = True,
    db: Session = Depends(get_db_session),
) -> ScanResponse:
    """
    Run partial workflow (GOVERNANCE → BLUE → VERIFY → DOC → PR) using existing RED output.
    Skips vulnerability detection phase.
    """
    from pathlib import Path
    
    scan_id = f"PARTIAL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    
    logger.info(f"Creating partial scan {scan_id} from {red_output_path}")
    
    # Validate RED output exists
    red_file = Path(red_output_path)
    if not red_file.exists():
        raise HTTPException(status_code=404, detail=f"RED output file not found: {red_output_path}")
    
    # Create DB Record
    new_scan = Scan(
        scan_id=scan_id,
        repo_url=repo_url,
        branch=branch,
        status=ScanStatus.GENERATING_FIXES,
        scan_profile="partial",
        created_at=datetime.utcnow(),
        scan_metadata={"current_phase": "governance", "partial": True, "red_output": red_output_path}
    )
    db.add(new_scan)
    db.commit()
    db.refresh(new_scan)
    
    # Submit to partial scan worker
    from src.api.workers.partial_scan_worker import run_partial_scan_in_process
    
    loop = asyncio.get_event_loop()
    request_data = {
        "red_output_path": red_output_path,
        "repo_url": repo_url,
        "branch": branch,
        "create_pr": create_pr,
    }
    
    loop.run_in_executor(scan_executor, run_partial_scan_in_process, scan_id, request_data)
    
    logger.info(f"✅ Partial scan {scan_id} queued for {repo_url}")
    
    return ScanResponse(
        scan_id=scan_id,
        status=API_ScanStatus.GENERATING_FIXES,
        message=f"Partial workflow queued (RED output: {red_file.name})",
        created_at=new_scan.created_at,
    )
