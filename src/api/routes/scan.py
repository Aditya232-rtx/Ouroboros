# src/api/routes/scan.py
"""Scan endpoint for initiating security scans."""

import logging
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, HTTPException, BackgroundTasks

from src.api.schemas import (
    ScanRequest,
    ScanResponse,
    ScanStatus,
    ErrorResponse,
)
from src.orchestration.workflow import OuroborosWorkflow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["scan"])

# In-memory scan tracking (production would use database)
_active_scans: dict = {}


async def _run_scan(scan_id: str, request: ScanRequest):
    """Background task to run the security scan."""
    try:
        _active_scans[scan_id]["status"] = ScanStatus.RUNNING
        _active_scans[scan_id]["current_phase"] = "initializing"
        
        # Initialize workflow
        workflow = OuroborosWorkflow()
        
        # Build input for workflow
        workflow_input = {
            "repo_url": request.repo_url,
            "branch": request.branch,
            "commit_sha": request.commit_sha or "HEAD",
            "scan_profile": request.scan_profile,
            "auto_fix": request.auto_fix,
            "create_pr": request.create_pr,
        }
        
        # Run the workflow
        result = await workflow.run(workflow_input)
        
        # Update scan status
        _active_scans[scan_id]["status"] = ScanStatus.COMPLETED
        _active_scans[scan_id]["completed_at"] = datetime.utcnow()
        _active_scans[scan_id]["result"] = result
        _active_scans[scan_id]["vulnerabilities_found"] = len(result.get("vulnerabilities", []))
        _active_scans[scan_id]["fixes_applied"] = len(result.get("fixes", []))
        _active_scans[scan_id]["pr_url"] = result.get("pr_url")
        
        logger.info(f"Scan {scan_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {e}", exc_info=True)
        _active_scans[scan_id]["status"] = ScanStatus.FAILED
        _active_scans[scan_id]["error_message"] = str(e)
        _active_scans[scan_id]["completed_at"] = datetime.utcnow()


@router.post(
    "",
    response_model=ScanResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Initiate a security scan",
    description="Start a new security scan on the specified repository. The scan runs asynchronously.",
)
async def create_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
) -> ScanResponse:
    """
    Initiate a security scan on a GitHub repository.
    
    The scan will:
    1. Clone the repository
    2. Run security tools (Semgrep, Checkov, Nuclei, CodeQL based on profile)
    3. Analyze findings with AI agents
    4. Optionally generate and apply fixes
    5. Optionally create a pull request
    """
    scan_id = f"SCAN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    
    logger.info(f"Creating scan {scan_id} for {request.repo_url}")
    
    # Validate PR creation requires auto_fix
    if request.create_pr and not request.auto_fix:
        raise HTTPException(
            status_code=400,
            detail="create_pr requires auto_fix to be enabled"
        )
    
    # Initialize scan tracking
    _active_scans[scan_id] = {
        "scan_id": scan_id,
        "status": ScanStatus.PENDING,
        "request": request.model_dump(),
        "started_at": datetime.utcnow(),
        "completed_at": None,
        "current_phase": "pending",
        "progress_percent": 0,
        "vulnerabilities_found": 0,
        "fixes_applied": 0,
        "error_message": None,
        "result": None,
        "pr_url": None,
    }
    
    # Queue the scan
    background_tasks.add_task(_run_scan, scan_id, request)
    
    return ScanResponse(
        scan_id=scan_id,
        status=ScanStatus.PENDING,
        message=f"Scan queued for {request.repo_url}",
        created_at=datetime.utcnow(),
    )


@router.get(
    "/{scan_id}",
    response_model=ScanResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get scan info",
)
async def get_scan(scan_id: str) -> ScanResponse:
    """Get basic scan information."""
    if scan_id not in _active_scans:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    
    scan_data = _active_scans[scan_id]
    return ScanResponse(
        scan_id=scan_id,
        status=scan_data["status"],
        message=f"Phase: {scan_data['current_phase']}",
        created_at=scan_data["started_at"],
    )


def get_scan_data(scan_id: str) -> dict:
    """Helper to get scan data for other routes."""
    return _active_scans.get(scan_id)
