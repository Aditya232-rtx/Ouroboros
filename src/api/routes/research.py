"""
Ouroboros AI - Research Agent API Routes
Serves vulnerability data discovered by the Research Agent
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/research", tags=["research"])


from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from src.agents import ResearchAgent

class ResearchStartRequest(BaseModel):
    tech_stack: List[str]
    freshness: str = "30d"

@router.post("/start")
async def start_research_scan(
    request: ResearchStartRequest, 
    background_tasks: BackgroundTasks
):
    """
    Trigger an autonomous Research Agent scan in the background.
    """
    agent = ResearchAgent()
    
    # Run in background
    background_tasks.add_task(agent.execute, request.dict())
    
    return {
        "status": "started",
        "message": f"Research started for {len(request.tech_stack)} technologies",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/vulnerabilities")
async def get_vulnerabilities(
    severity: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0
):
    """
    Get list of vulnerabilities discovered by Research Agent.
    
    Query parameters:
    - severity: Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)
    - limit: Maximum number of results
    - offset: Pagination offset
    """
    json_path = Path("research_findings/vulnerabilities.json")
    
    if not json_path.exists():
        return {
            "last_updated": datetime.now().isoformat(),
            "total_count": 0,
            "vulnerabilities": []
        }
    
    try:
        with json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        
        vulnerabilities = data.get("vulnerabilities", [])
        
        # Filter by severity if specified
        if severity:
            vulnerabilities = [
                v for v in vulnerabilities 
                if v.get("severity", "").upper() == severity.upper()
            ]
        
        # Apply pagination
        total = len(vulnerabilities)
        if limit:
            vulnerabilities = vulnerabilities[offset:offset+limit]
        else:
            vulnerabilities = vulnerabilities[offset:]
        
        return {
            "last_updated": data.get("last_updated"),
            "total_count": total,
            "returned_count": len(vulnerabilities),
            "vulnerabilities": vulnerabilities
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read vulnerabilities: {str(e)}")


@router.get("/vulnerabilities/{cve_id}")
async def get_vulnerability_details(cve_id: str):
    """
    Get detailed information about a specific vulnerability by CVE ID.
    """
    json_path = Path("research_findings/vulnerabilities.json")
    
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="No vulnerabilities found")
    
    try:
        with json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        
        for vuln in data.get("vulnerabilities", []):
            if vuln.get("cve_id") == cve_id:
                return vuln
        
        raise HTTPException(status_code=404, detail=f"CVE {cve_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read vulnerability: {str(e)}")


@router.get("/stats")
async def get_research_stats():
    """
    Get dashboard statistics for Research Agent.
    
    Returns:
    - total_vulnerabilities: Total count
    - new_last_3_days: Count discovered in last 3 days
    - by_severity: Breakdown by severity level
    """
    json_path = Path("research_findings/vulnerabilities.json")
    
    if not json_path.exists():
        return {
            "total_vulnerabilities": 0,
            "new_last_3_days": 0,
            "by_severity": {
                "CRITICAL": 0,
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0,
                "UNKNOWN": 0
            },
            "last_updated": None
        }
    
    try:
        with json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        
        vulnerabilities = data.get("vulnerabilities", [])
        total = len(vulnerabilities)
        
        # Count by severity
        by_severity = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "UNKNOWN": 0
        }
        
        # Count new in last 3 days
        three_days_ago = datetime.now().timestamp() - (3 * 24 * 60 * 60)
        new_count = 0
        
        for vuln in vulnerabilities:
            # Count severity
            severity = vuln.get("severity", "UNKNOWN").upper()
            if severity in by_severity:
                by_severity[severity] += 1
            
            # Count recency
            discovered_at = vuln.get("discovered_at")
            if discovered_at:
                try:
                    vuln_timestamp = datetime.fromisoformat(discovered_at.replace('Z', '+00:00')).timestamp()
                    if vuln_timestamp >= three_days_ago:
                        new_count += 1
                except:
                    pass
        
        return {
            "total_vulnerabilities": total,
            "new_last_3_days": new_count,
            "by_severity": by_severity,
            "last_updated": data.get("last_updated")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute stats: {str(e)}")
