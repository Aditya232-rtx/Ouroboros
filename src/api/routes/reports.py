# src/api/routes/reports.py
"""Reports endpoint for generating and downloading scan reports."""

import os
import json
import html as html_lib
import logging
import tempfile
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from io import BytesIO
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse

from src.api.schemas import (
    ReportRequest,
    ReportResponse,
    ErrorResponse,
)
from src.api.routes.scan import get_scan_data

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
    
    status_str = scan_data["status"]
    if hasattr(status_str, 'value'):
        status_str = status_str.value
    if str(status_str) not in ("completed", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Scan {request.scan_id} is not yet complete"
        )
    
    report_id = f"RPT-{uuid4().hex[:12]}"
    generated_at = datetime.now(timezone.utc)
    expires_at = generated_at + timedelta(hours=24)
    
    # Generate report content based on format
    result = scan_data.get("result") or {}
    
    if request.format == "json":
        report_content = _generate_json_report(result, request)
    elif request.format == "html":
        report_content = _generate_html_report(result, request)
    elif request.format == "pdf":
        report_content = _generate_pdf_report(result, request)
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
async def download_report(report_id: str) -> StreamingResponse:
    """Download a generated report."""
    if report_id not in _reports:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    
    report = _reports[report_id]
    
    if datetime.now(timezone.utc) > report["expires_at"]:
        raise HTTPException(status_code=410, detail="Report has expired")
    
    if report["format"] == "json":
        return JSONResponse(
            content=report["content"],
            headers={
                "Content-Disposition": f'attachment; filename="report_{report_id}.json"'
            }
        )
    elif report["format"] == "html":
        return HTMLResponse(
            content=report["content"],
            headers={
                "Content-Disposition": f'attachment; filename="report_{report_id}.html"'
            }
        )
    elif report["format"] == "pdf":
        # Return PDF as streaming binary
        return StreamingResponse(
            BytesIO(report["content"]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="report_{report_id}.pdf"'
            }
        )
    else:
        return JSONResponse(content=report["content"])


@router.get(
    "/{report_id}/download/pdf",
    summary="Download report as PDF",
    description="Download a report in PDF format.",
)
async def download_report_pdf(report_id: str) -> StreamingResponse:
    """Download a report as PDF."""
    if report_id not in _reports:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    
    report = _reports[report_id]
    
    if datetime.now(timezone.utc) > report["expires_at"]:
        raise HTTPException(status_code=410, detail="Report has expired")
    
    # Convert to PDF if needed
    if report["format"] == "pdf":
        pdf_content = report["content"]
    else:
        # Generate PDF from existing content
        result = report.get("content", {})
        pdf_content = _generate_pdf_from_data(result, report["scan_id"])
    
    return StreamingResponse(
        BytesIO(pdf_content),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="ouroboros_report_{report_id}.pdf"'
        }
    )


@router.get(
    "/scan/{scan_id}/pdf",
    summary="Generate and download PDF report for scan",
    description="Generate a PDF report for a scan and download it immediately.",
)
async def generate_and_download_pdf(scan_id: str) -> StreamingResponse:
    """Generate and download a PDF report for a scan."""
    scan_data = get_scan_data(scan_id)
    
    if not scan_data:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    
    # Use `or {}` because get() returns None when "result" key exists but is None
    result = scan_data.get("result") or {}
    pdf_content = _generate_pdf_from_data(result, scan_id)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"ouroboros_security_report_{scan_id}_{timestamp}.pdf"
    
    return StreamingResponse(
        BytesIO(pdf_content),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

@router.get(
    "/scan/{scan_id}/initial-report",
    summary="Download initial PDF report",
    description="Download the initial PDF report generated by the Documentation Agent.",
)
async def download_initial_report(scan_id: str) -> StreamingResponse:
    """Download the initial PDF report for a scan."""
    scan_data = get_scan_data(scan_id)
    
    if not scan_data:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    
    # Get path from metadata
    # The scan_data returned by get_scan_data flattens some metadata but let's check Result/Metadata
    # In scan.py: get_scan_data returns dict. "result" contains Result.
    # But initial_report_url was saved to State, which might be in scan_metadata.
    
    # We need to access the raw scan_metadata from DB or via get_scan_data logic
    # In scan.py get_scan_data: meta = scan.scan_metadata or {}
    # It returns "current_phase", "result", etc.
    # It does NOT explicitly return initial_report_url in the top level dict.
    
    # Let's fix get_scan_data in scan.py OR access DB here.
    # Accessing DB here is safer for robust metadata access.
    
    from src.database.session import SessionLocal
    from src.database.models import Scan
    
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.scan_id == scan_id).first()
        if not scan:
             raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
        
        meta = scan.scan_metadata or {}
        pdf_path = meta.get("initial_report_url")
        
        if not pdf_path or not os.path.exists(pdf_path):
            # Fallback: Try to find in outputs/reports
            # Filename pattern: ouroboros-initial-{repo}-{timestamp}.pdf
            # This is hard to guess.
            raise HTTPException(status_code=404, detail="Initial report not found")
        
        def _iter_file():
            with open(pdf_path, "rb") as f:
                yield from f
            
        return StreamingResponse(
            _iter_file(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="ouroboros_initial_report_{scan_id}.pdf"'
            }
        )
    finally:
        db.close()


@router.get(
    "/scan/{scan_id}/final-report",
    summary="Download final PDF report",
    description="Download the final PDF report generated at the end of the workflow.",
)
async def download_final_report(scan_id: str) -> StreamingResponse:
    """Download the final PDF report for a scan."""
    from src.database.session import SessionLocal
    from src.database.models import Scan

    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.scan_id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

        meta = scan.scan_metadata or {}
        pdf_path = scan.report_url or meta.get("final_report_url")

        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="Final report not found")

        def _iter_file():
            with open(pdf_path, "rb") as f:
                yield from f

        return StreamingResponse(
            _iter_file(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="ouroboros_final_report_{scan_id}.pdf"'
            }
        )
    finally:
        db.close()


def _generate_json_report(result: dict, request: ReportRequest) -> dict:
    """Generate JSON format report."""
    report = {
        "scan_id": request.scan_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
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
        sev = html_lib.escape(str(vuln.get('severity', 'medium')))
        vtype = html_lib.escape(str(vuln.get('type', 'Unknown')))
        loc = vuln.get('location', {})
        vfile = html_lib.escape(str(loc.get('file', 'N/A') if isinstance(loc, dict) else 'N/A'))
        vline = html_lib.escape(str(loc.get('line', 'N/A') if isinstance(loc, dict) else 'N/A'))
        vdesc = html_lib.escape(str(vuln.get('description', '')))
        vulnerabilities_html += f"""
        <div class="vulnerability {sev}">
            <h3>{vtype} - {sev.upper()}</h3>
            <p><strong>File:</strong> {vfile}</p>
            <p><strong>Line:</strong> {vline}</p>
            <p>{vdesc}</p>
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
        <p><strong>Generated:</strong> {datetime.now(timezone.utc).isoformat()}</p>
        <h2>Vulnerabilities ({len(result.get('vulnerabilities', []))})</h2>
        {vulnerabilities_html or '<p>No vulnerabilities found.</p>'}
    </body>
    </html>
    """
    return html


def _generate_pdf_report(result: dict, request: ReportRequest) -> bytes:
    """Generate PDF format report using reportlab."""
    return _generate_pdf_from_data(result, request.scan_id)


def _generate_pdf_from_data(result: dict, scan_id: str) -> bytes:
    """Generate a PDF report from scan data."""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
    except ImportError:
        # Fallback: return a simple text-based PDF placeholder
        logger.warning("reportlab not installed, generating basic PDF")
        return _generate_simple_pdf(result, scan_id)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#1e293b'),
        spaceAfter=20
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=HexColor('#334155'),
        spaceBefore=15,
        spaceAfter=10
    )
    
    elements = []
    
    # Title
    elements.append(Paragraph("Ouroboros Security Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Summary
    elements.append(Paragraph(f"<b>Scan ID:</b> {scan_id}", styles['Normal']))
    elements.append(Paragraph(f"<b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Vulnerability count
    vulns = result.get("vulnerabilities", [])
    fixes = result.get("fixes", [])
    
    elements.append(Paragraph("Executive Summary", heading_style))
    
    summary_data = [
        ["Metric", "Value"],
        ["Total Vulnerabilities", str(len(vulns))],
        ["Fixes Applied", str(len(fixes))],
        ["Critical", str(sum(1 for v in vulns if v.get('severity') == 'critical'))],
        ["High", str(sum(1 for v in vulns if v.get('severity') == 'high'))],
        ["Medium", str(sum(1 for v in vulns if v.get('severity') == 'medium'))],
        ["Low", str(sum(1 for v in vulns if v.get('severity') == 'low'))],
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Vulnerabilities detail
    if vulns:
        elements.append(Paragraph("Vulnerabilities Detected", heading_style))
        for i, vuln in enumerate(vulns[:20], 1):  # Limit to 20 for PDF size
            severity = vuln.get('severity', 'medium').upper()
            vuln_type = vuln.get('type', 'Unknown')
            location = vuln.get('location', {})
            file_path = location.get('file', 'N/A') if isinstance(location, dict) else 'N/A'
            line = location.get('line', 'N/A') if isinstance(location, dict) else 'N/A'
            
            elements.append(Paragraph(
                f"<b>{i}. [{severity}] {vuln_type}</b><br/>"
                f"File: {file_path} (Line {line})<br/>"
                f"{vuln.get('description', '')[:200]}",
                styles['Normal']
            ))
            elements.append(Spacer(1, 0.1*inch))
    
    # Build PDF
    doc.build(elements)
    return buffer.getvalue()


def _generate_simple_pdf(result: dict, scan_id: str) -> bytes:
    """Generate a simple PDF without reportlab (fallback)."""
    # Create a minimal PDF structure
    vulns = result.get("vulnerabilities", [])
    content = f"""Ouroboros Security Report
Scan ID: {scan_id}
Generated: {datetime.now(timezone.utc).isoformat()}

Vulnerabilities Found: {len(vulns)}
Fixes Applied: {len(result.get('fixes', []))}

---
"""
    for i, vuln in enumerate(vulns[:10], 1):
        content += f"\n{i}. [{vuln.get('severity', 'medium').upper()}] {vuln.get('type', 'Unknown')}\n"
    
    # Minimal PDF (not a real PDF, just text with PDF header for demo)
    # In production, install reportlab
    pdf_header = b"%PDF-1.4\n"
    pdf_content = content.encode('utf-8')
    return pdf_header + pdf_content


def _count_by_severity(vulnerabilities: list) -> dict:
    """Count vulnerabilities by severity level."""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for vuln in vulnerabilities:
        sev = vuln.get("severity", "medium").lower()
        if sev in counts:
            counts[sev] += 1
    return counts
