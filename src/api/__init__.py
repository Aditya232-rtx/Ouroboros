"""
Ouroboros AI - FastAPI Application
Main API interface for vulnerability scanning and workflow management
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from config.settings import settings
from src.orchestration.workflow import workflow

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Ouroboros AI",
    description="Autonomous Security System - Vulnerability Discovery & Remediation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== REQUEST/RESPONSE SCHEMAS =====

class ScanRequest(BaseModel):
    """Request schema for initiating a scan"""
    repo_url: str
    branch: str = "main"
    commit_sha: Optional[str] = None
    scan_profile: str = "standard"  # quick|standard|deep
    user_id: Optional[str] = None


class ScanResponse(BaseModel):
    """Response schema for scan initiation"""
    scan_id: str
    status: str
    message: str
    repo_url: str


class StatusResponse(BaseModel):
    """Response schema for scan status"""
    scan_id: str
    status: str
    current_phase: str
    vulnerabilities_found: int
    fixes_generated: int
    all_verified: bool
    pr_url: Optional[str] = None
    report_url: Optional[str] = None


# ===== GLOBAL STATE =====
# TODO: Replace with proper database
active_scans: Dict[str, Dict[str, Any]] = {}


# ===== API ROUTES =====

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/scan", response_model=ScanResponse)
async def create_scan(request: ScanRequest):
    """
    Initiate a new security scan.
    
    This endpoint:
    1. Validates the repository URL
    2. Starts the Ouroboros workflow
    3. Returns a scan ID for tracking
    """
    logger.info(f"Received scan request for {request.repo_url}")
    
    try:
        # Start workflow (async, non-blocking)
        # TODO: Use background tasks or Celery for production
        result = await workflow.run({
            "repo_url": request.repo_url,
            "branch": request.branch,
            "commit_sha": request.commit_sha,
            "scan_profile": request.scan_profile,
            "user_id": request.user_id or "anonymous"
        })
        
        scan_id = result["scan_id"]
        active_scans[scan_id] = result
        
        return ScanResponse(
            scan_id=scan_id,
            status="in_progress",
            message="Scan initiated successfully",
            repo_url=request.repo_url
        )
    
    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {str(e)}"
        )


@app.get("/api/scan/{scan_id}", response_model=StatusResponse)
async def get_scan_status(scan_id: str):
    """
    Get the status of a scan.
    
    Returns:
    - Current phase (scanning, fixing, verifying, etc.)
    - Vulnerabilities found
    - Fixes generated
    - Verification status
    - PR URL (if created)
    """
    if scan_id not in active_scans:
        raise HTTPException(
            status_code=404,
            detail=f"Scan {scan_id} not found"
        )
    
    scan_state = active_scans[scan_id]
    
    return StatusResponse(
        scan_id=scan_id,
        status="complete" if scan_state.get("current_phase") == "complete" else "in_progress",
        current_phase=scan_state.get("current_phase", "unknown"),
        vulnerabilities_found=len(scan_state.get("vulnerabilities", [])),
        fixes_generated=len(scan_state.get("fixes", [])),
        all_verified=scan_state.get("all_verified", False),
        pr_url=scan_state.get("pr_url"),
        report_url=scan_state.get("final_report_url")
    )


@app.get("/api/scans")
async def list_scans():
    """List all active scans"""
    return {
        "scans": [
            {
                "scan_id": scan_id,
                "repo_url": state.get("repo_url"),
                "status": state.get("current_phase", "unknown"),
                "started_at": state.get("workflow_start_time")
            }
            for scan_id, state in active_scans.items()
        ]
    }


# ===== APPLICATION STARTUP =====

@app.on_event("startup")
async def startup_event():
    """Application startup logic"""
    logger.info("Ouroboros AI starting up...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Models directory: {settings.models_dir}")
    
    # TODO: Initialize models, check dependencies


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown logic"""
    logger.info("Ouroboros AI shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
