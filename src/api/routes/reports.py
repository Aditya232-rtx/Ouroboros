# src/api/routes/reports.py
"""Reports endpoint for generating scan reports."""

import os
import json
import logging
import tempfile
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import APIRouter, HTTPException, BackgroundTasks

from src.api.schemas import (
    ReportRequest,
    ReportResponse,
    ReportExportResponse,
    ErrorResponse,
)
from src.api.routes.scan import get_scan_data
from src.integrations.google_drive import drive_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])

# In-memory report storage (production would use object storage)
_reports: dict = {}


@router.post(
    "",
    response_model=ReportResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Generate a scan report",
    description="Generate a downloadable report for a completed scan.",
)
async def create_report(request: ReportRequest) -> ReportResponse:
    """Generate a report for a completed scan."""
    scan_data = get_scan_data(request.scan_id)
    
    if not scan_data:
        raise HTTPException(status_code=404, detail=f"Scan {request.scan_id} not found")
    
    if scan_data["status"].value not in ("completed", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Scan {request.scan_id} is not yet complete"
        )
    
    report_id = f"RPT-{uuid4().hex[:12]}"
    generated_at = datetime.utcnow()
    expires_at = generated_at + timedelta(hours=24)
    
    # Generate report content based on format
    result = scan_data.get("result", {})
    
    if request.format == "json":
        report_content = _generate_json_report(result, request)
    elif request.format == "html":
        report_content = _generate_html_report(result, request)
    else:
        report_content = _generate_json_report(result, request)
    
    # Store report
    _reports[report_id] = {
        "report_id": report_id,
        "scan_id": request.scan_id,
        "format": request.format,
        "content": report_content,
        "generated_at": generated_at,
        "expires_at": expires_at,
    }
    
    logger.info(f"Generated report {report_id} for scan {request.scan_id}")
    
    return ReportResponse(
        report_id=report_id,
        scan_id=request.scan_id,
        format=request.format,
        download_url=f"/reports/{report_id}/download",
        generated_at=generated_at,
        expires_at=expires_at,
    )


@router.get(
    "/{report_id}/download",
    summary="Download a report",
    description="Download a previously generated report.",
)
async def download_report(report_id: str):
    """Download a generated report."""
    if report_id not in _reports:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    
    report = _reports[report_id]
    
    if datetime.utcnow() > report["expires_at"]:
        raise HTTPException(status_code=410, detail="Report has expired")
    
    from fastapi.responses import JSONResponse, HTMLResponse
    
    if report["format"] == "json":
        return JSONResponse(content=report["content"])
    elif report["format"] == "html":
        return HTMLResponse(content=report["content"])
    else:
        return JSONResponse(content=report["content"])


@router.post(
    "/{report_id}/export/drive",
    response_model=ReportExportResponse,
    summary="Export report to Google Drive",
    description="Uploads the report to the configured Google Drive folder.",
)
async def export_report_to_drive(report_id: str):
    """Export a generated report to Google Drive."""
    if report_id not in _reports:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    
    report = _reports[report_id]
    
    # Create valid temporary file
    suffix = ".json" if report["format"] == "json" else ".html"
    mime_type = "application/json" if report["format"] == "json" else "text/html"
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as tmp:
        if report["format"] == "json":
            json.dump(report["content"], tmp, indent=2)
        else:
            tmp.write(report["content"])
        tmp_path = tmp.name
    
    try:
        # Upload to Drive
        uploaded_file = drive_client.upload_file(tmp_path, mime_type=mime_type)
        
        if not uploaded_file:
            raise HTTPException(status_code=500, detail="Failed to upload report to Google Drive")
            
        return ReportExportResponse(
            report_id=report_id,
            file_id=uploaded_file.get("id"),
            web_view_link=uploaded_file.get("webViewLink")
        )
    finally:
        # Cleanup temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _generate_json_report(result: dict, request: ReportRequest) -> dict:
    """Generate JSON format report."""
    report = {
        "scan_id": request.scan_id,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_vulnerabilities": len(result.get("vulnerabilities", [])),
            "total_fixes": len(result.get("fixes", [])),
            "by_severity": _count_by_severity(result.get("vulnerabilities", [])),
        },
        "vulnerabilities": [],
    }
    
    for vuln in result.get("vulnerabilities", []):
        vuln_report = {
            "id": vuln.get("id"),
            "type": vuln.get("type"),
            "severity": vuln.get("severity"),
            "description": vuln.get("description"),
            "location": vuln.get("location"),
            "remediation_hint": vuln.get("remediation_hint"),
        }
        
        if request.include_poc:
            vuln_report["poc_code"] = vuln.get("poc_code")
        
        report["vulnerabilities"].append(vuln_report)
    
    if request.include_fixes:
        report["fixes"] = result.get("fixes", [])
    
    return report


def _generate_html_report(result: dict, request: ReportRequest) -> str:
    """Generate HTML format report."""
    vulnerabilities_html = ""
    for vuln in result.get("vulnerabilities", []):
        vulnerabilities_html += f"""
        <div class="vulnerability {vuln.get('severity', 'medium')}">
            <h3>{vuln.get('type', 'Unknown')} - {vuln.get('severity', 'medium').upper()}</h3>
            <p><strong>File:</strong> {vuln.get('location', {}).get('file', 'N/A')}</p>
            <p><strong>Line:</strong> {vuln.get('location', {}).get('line', 'N/A')}</p>
            <p>{vuln.get('description', '')}</p>
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Security Scan Report - {request.scan_id}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .vulnerability {{ border: 1px solid #ccc; padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .critical {{ border-color: #dc3545; background: #f8d7da; }}
            .high {{ border-color: #fd7e14; background: #fff3cd; }}
            .medium {{ border-color: #ffc107; background: #fffbeb; }}
            .low {{ border-color: #28a745; background: #d4edda; }}
        </style>
    </head>
    <body>
        <h1>Security Scan Report</h1>
        <p><strong>Scan ID:</strong> {request.scan_id}</p>
        <p><strong>Generated:</strong> {datetime.utcnow().isoformat()}</p>
        <h2>Vulnerabilities ({len(result.get('vulnerabilities', []))})</h2>
        {vulnerabilities_html or '<p>No vulnerabilities found.</p>'}
    </body>
    </html>
    """
    return html


def _count_by_severity(vulnerabilities: list) -> dict:
    """Count vulnerabilities by severity level."""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for vuln in vulnerabilities:
        sev = vuln.get("severity", "medium").lower()
        if sev in counts:
            counts[sev] += 1
    return counts
