# src/api/schemas/__init__.py
"""API request and response schemas for Ouroboros AI."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ScanStatus(str, Enum):
    """Status of a security scan."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SeverityLevel(str, Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============ Scan Request/Response Schemas ============

class ScanRequest(BaseModel):
    """Request body for initiating a security scan."""
    repo_url: str = Field(..., description="GitHub repository URL to scan")
    branch: str = Field(default="main", description="Branch to scan")
    commit_sha: Optional[str] = Field(default=None, description="Specific commit SHA (optional)")
    scan_profile: str = Field(default="standard", description="Scan profile: quick, standard, deep")
    timeout_seconds: int = Field(default=300, ge=60, le=3600, description="Scan timeout in seconds")
    auto_fix: bool = Field(default=False, description="Automatically generate fixes")
    create_pr: bool = Field(default=False, description="Create PR with fixes (requires auto_fix)")

    class Config:
        json_schema_extra = {
            "example": {
                "repo_url": "https://github.com/example/vulnerable-app",
                "branch": "main",
                "scan_profile": "standard",
                "auto_fix": True,
                "create_pr": True
            }
        }


class ScanResponse(BaseModel):
    """Response after initiating a scan."""
    scan_id: str = Field(..., description="Unique scan identifier")
    status: ScanStatus = Field(..., description="Current scan status")
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============ Status Schemas ============

class VulnerabilitySummary(BaseModel):
    """Summary of a vulnerability."""
    id: str
    type: str
    severity: SeverityLevel
    file: str
    line: int
    description: str
    confidence: float


class FixSummary(BaseModel):
    """Summary of a fix."""
    vulnerability_id: str
    status: str  # applied, pending, rejected
    file: str
    lines_changed: int


class ScanStatusResponse(BaseModel):
    """Response for scan status query."""
    scan_id: str
    status: ScanStatus
    progress_percent: int = Field(ge=0, le=100)
    current_phase: str
    vulnerabilities_found: int
    fixes_applied: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ScanDetailResponse(ScanStatusResponse):
    """Detailed scan status with vulnerability list."""
    vulnerabilities: List[VulnerabilitySummary] = []
    fixes: List[FixSummary] = []
    pr_url: Optional[str] = None
    report_url: Optional[str] = None


# ============ Report Schemas ============

class ReportRequest(BaseModel):
    """Request body for generating a report."""
    scan_id: str = Field(..., description="Scan ID to generate report for")
    format: str = Field(default="json", description="Report format: json, html, pdf")
    include_fixes: bool = Field(default=True)
    include_poc: bool = Field(default=False, description="Include PoC code (security-sensitive)")


class ReportResponse(BaseModel):
    """Response with report details."""
    report_id: str
    scan_id: str
    format: str
    download_url: str
    generated_at: datetime
    expires_at: datetime


# ============ Error Schemas ============

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============ Health Check ============

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    uptime_seconds: float
    components: Dict[str, str]


__all__ = [
    "ScanStatus",
    "SeverityLevel",
    "ScanRequest",
    "ScanResponse",
    "VulnerabilitySummary",
    "FixSummary",
    "ScanStatusResponse",
    "ScanDetailResponse",
    "ReportRequest",
    "ReportResponse",
    "ErrorResponse",
    "HealthResponse",
]
