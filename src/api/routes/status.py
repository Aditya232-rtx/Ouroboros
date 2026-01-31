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
    # Extract vulnerabilities from result or scan metadata
    vulnerabilities = []
    
    # Get metadata for governance info
    metadata = scan_data.get("scan_metadata", {}) or {}
    result = scan_data.get("result") or {}
    
    # Build governance map for O(1) lookup
    gov_map = {}
    governance_queue = metadata.get("governance_queue", [])
    
    # If queue exists, use it to populate gov_map
    for item in governance_queue:
        v_id = item.get("vulnerability_id")
        if v_id:
            gov_map[v_id] = item

    # Use result vulnerabilities if available (final state), otherwise check input vulnerabilities or metadata
    # The scan result usually contains the final list.
    raw_vulns = result.get("vulnerabilities", [])
    
    # If no result vulnerabilities (e.g. still running), try to use what we have in metadata from governance node
    if not raw_vulns and governance_queue:
        # Reconstruct vulnerabilities from the governance queue if original vuln is missing in result
        raw_vulns = [item.get("original_vulnerability") for item in governance_queue if item.get("original_vulnerability")]

    for vuln in raw_vulns:
        v_id = vuln.get("id", "unknown")
        gov_info = gov_map.get(v_id, {})
        
        # Determine status
        # If accessing the governance page, items in the queue are typically "pending" approval unless processed
        autonomy = gov_info.get("autonomy_level", "suggest")
        status = "pending" # Default for visualization
        
        # Map autonomy to rule
        rule = f"Risk Score > {gov_info.get('risk_score', 0)}"
        
        vulnerabilities.append(VulnerabilitySummary(
            id=v_id,
            type=vuln.get("type", "unknown"),
            severity=SeverityLevel(vuln.get("severity", "medium").lower()),
            file=vuln.get("location", {}).get("file", "unknown"),
            line=vuln.get("location", {}).get("line", 0),
            description=vuln.get("description", ""),
            confidence=vuln.get("confidence", 0.0),
            cvss=vuln.get("cvss", 0.0) or (gov_info.get("risk_score", 0.0) / 10.0), # Fallback to normalized risk score
            
            # Governance fields
            risk_score=gov_info.get("risk_score", 0.0),
            priority=gov_info.get("priority", 0),
            governance_status=status,
            policy_rule=rule,
            impact=gov_info.get("reasoning", "Pending evaluation")
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
