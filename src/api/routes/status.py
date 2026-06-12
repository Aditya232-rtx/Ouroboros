# src/api/routes/status.py
"""Status endpoint for checking scan progress."""

import logging
from typing import List
from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    ScanStatus,
    ScanStatusResponse,
    ScanDetailResponse,
    VulnerabilitySummary,
    FixSummary,
    SeverityLevel,
    ErrorResponse,
    LogEntry,  # Add this
)
from src.api.routes.scan import get_scan_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/status", tags=["status"])


@router.get(
    "/{scan_id}",
    response_model=ScanStatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get scan status",
    description="Get the current status and progress of a scan.",
)
async def get_status(scan_id: str) -> ScanStatusResponse:
    """Get the current status of a scan."""
    scan_data = get_scan_data(scan_id)
    
    if not scan_data:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    
    return ScanStatusResponse(
        scan_id=scan_id,
        repo_url=scan_data.get("repo_url"), # <--- Added
        status=scan_data["status"],
        progress_percent=scan_data.get("progress_percent", 0),
        current_phase=scan_data.get("current_phase", "unknown"),
        vulnerabilities_found=scan_data.get("vulnerabilities_found", 0),
        fixes_applied=scan_data.get("fixes_applied", 0),
        started_at=scan_data["started_at"],
        completed_at=scan_data.get("completed_at"),
        error_message=scan_data.get("error_message"),
    )


@router.get(
    "/{scan_id}/detail",
    response_model=ScanDetailResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get detailed scan status",
    description="Get detailed status including vulnerabilities and fixes.",
)
async def get_status_detail(scan_id: str) -> ScanDetailResponse:
    """Get detailed scan status with vulnerabilities and fixes."""
    scan_data = get_scan_data(scan_id)
    
    if not scan_data:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    
    # Extract vulnerabilities from result
    vulnerabilities = []
    result = scan_data.get("result") or {}
    for vuln in result.get("vulnerabilities", []):
        vulnerabilities.append(VulnerabilitySummary(
            id=vuln.get("id", "unknown"),
            type=vuln.get("type", "unknown"),
            severity=SeverityLevel(vuln.get("severity", "medium")),
            file=vuln.get("location", {}).get("file", "unknown"),
            line=vuln.get("location", {}).get("line", 0),
            description=vuln.get("description", ""),
            confidence=vuln.get("confidence", 0.0),
        ))
    
    # Extract fixes from result
    fixes = []
    for fix in result.get("fixes", []):
        fixes.append(FixSummary(
            vulnerability_id=fix.get("vulnerability_id", "unknown"),
            status=fix.get("status", "pending"),
            file=fix.get("file", "unknown"),
            lines_changed=fix.get("lines_changed", 0),
        ))
    
    return ScanDetailResponse(
        scan_id=scan_id,
        repo_url=scan_data.get("repo_url"), # <--- Added
        status=scan_data["status"],
        progress_percent=scan_data.get("progress_percent", 0),
        current_phase=scan_data.get("current_phase", "unknown"),
        vulnerabilities_found=len(vulnerabilities),
        fixes_applied=len([f for f in fixes if f.status == "applied"]),
        started_at=scan_data["started_at"],
        completed_at=scan_data.get("completed_at"),
        error_message=scan_data.get("error_message"),
        vulnerabilities=vulnerabilities,
        fixes=fixes,
        pr_url=scan_data.get("pr_url"),
        report_url=None,  # Generated on-demand via /reports
    )


@router.get(
    "/{scan_id}/logs",
    summary="Get scan logs",
)
async def get_scan_logs(scan_id: str):
    """Get logs for a specific scan."""
    scan_data = get_scan_data(scan_id)
    if not scan_data:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    
    logs = scan_data.get("logs") or []
    logger.info(f"Returning {len(logs)} log entries for scan {scan_id}")
    
    # Return logs wrapped in expected format for frontend
    return {"logs": logs}
