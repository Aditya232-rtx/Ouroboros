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
    fixes = []
    verified_ids = set()
    
    try:
        # Get metadata for governance info
        metadata = scan_data.get("scan_metadata", {}) or {}
        result = scan_data.get("result") or {}
        
        # Build governance map for O(1) lookup
        gov_map = {}
        governance_queue = metadata.get("governance_queue", []) or []
        
        for item in governance_queue:
            if isinstance(item, dict):
                v_id = item.get("vulnerability_id")
                if v_id:
                    gov_map[v_id] = item

        # Build verified vulnerability set for accurate fix counting/status
        verification_results = result.get("verification_results", []) or []
        verified_ids = {
            item.get("vulnerability_id")
            for item in verification_results
            if isinstance(item, dict) and item.get("verified") and item.get("vulnerability_id")
        }

        # Use result vulnerabilities if available (final state)
        raw_vulns = result.get("vulnerabilities", []) or []
        
        # If no result vulnerabilities (e.g. still running), try governance queue
        if not raw_vulns and governance_queue:
            raw_vulns = [
                item.get("original_vulnerability")
                for item in governance_queue
                if isinstance(item, dict) and item.get("original_vulnerability")
            ]

        for vuln in raw_vulns:
            if not isinstance(vuln, dict):
                continue
            v_id = vuln.get("id", "unknown")
            gov_info = gov_map.get(v_id, {})
            
            severity_str = str(vuln.get("severity", "medium")).lower()
            try:
                severity = SeverityLevel(severity_str)
            except ValueError:
                severity = SeverityLevel("medium")
            
            location = vuln.get("location") or {}
            if not isinstance(location, dict):
                location = {}
            
            vulnerabilities.append(VulnerabilitySummary(
                id=v_id,
                type=vuln.get("type", "unknown"),
                severity=severity,
                file=location.get("file", "unknown"),
                line=location.get("line", 0),
                description=vuln.get("description", ""),
                confidence=float(vuln.get("confidence", 0.0) or 0.0),
                cvss=float(vuln.get("cvss", 0.0) or 0.0) or (float(gov_info.get("risk_score", 0.0) or 0.0) / 10.0),
                risk_score=float(gov_info.get("risk_score", 0.0) or 0.0),
                priority=int(gov_info.get("priority", 0) or 0),
                governance_status="pending",
                policy_rule=f"Risk Score > {gov_info.get('risk_score', 0)}",
                impact=gov_info.get("reasoning", "Pending evaluation")
            ))
        
        # Extract fixes from result
        for fix in (result.get("fixes", []) or []):
            if not isinstance(fix, dict):
                continue
            vulnerability_id = fix.get("vulnerability_id", "unknown")
            fix_status = fix.get("status", "pending")

            # If fix status wasn't materialized into "applied", infer from verification results
            if fix_status != "applied" and vulnerability_id in verified_ids:
                fix_status = "applied"

            fixes.append(FixSummary(
                vulnerability_id=vulnerability_id,
                status=fix_status,
                file=fix.get("file", "unknown"),
                lines_changed=fix.get("lines_changed", 0),
            ))
    except Exception as e:
        logger.error(f"Error building detail response for scan {scan_id}: {e}")
        # Continue with empty lists rather than crashing
    
    fixes_applied_count = len([f for f in fixes if f.status == "applied"])

    # Fallback for pipelines where fixes exist but explicit "applied" status is not emitted
    if fixes_applied_count == 0 and verified_ids:
        fixes_applied_count = len(verified_ids)

    return ScanDetailResponse(
        scan_id=scan_id,
        repo_url=scan_data.get("repo_url"), # <--- Added
        status=scan_data["status"],
        progress_percent=scan_data.get("progress_percent", 0),
        current_phase=scan_data.get("current_phase", "unknown"),
        vulnerabilities_found=len(vulnerabilities),
        fixes_applied=fixes_applied_count,
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
