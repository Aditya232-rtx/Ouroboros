"""
Ouroboros AI - Research Agent API Routes
Serves vulnerability intelligence discovered by the LangGraph Research Agent.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
import json
import os
import asyncio
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/research", tags=["research"])

# ─── Schemas ────────────────────────────────────────────────────────────────

class ResearchTriggerRequest(BaseModel):
    url: str

# ─── Background task ────────────────────────────────────────────────────────

def _run_agent_sync(url: str):
    """Run the LangGraph Research Agent in a brand-new event loop (safe for thread)."""
    try:
        from src.agents.research_agent import research_app
        initial_state = {
            "url": url,
            "raw_markdown": "",
            "extracted_json": {},
            "error_message": "",
            "retry_count": 0,
        }
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(research_app.ainvoke(initial_state))
        loop.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Research agent error: {e}")

# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/trigger")
async def trigger_research(request: ResearchTriggerRequest, background_tasks: BackgroundTasks):
    """
    Dispatch the LangGraph Research Agent in the background for a given CVE URL.
    Returns immediately; findings appear in /api/research/findings after the agent completes.
    """
    background_tasks.add_task(_run_agent_sync, request.url)
    return {"status": "Research Agent Dispatched", "target": request.url}


@router.get("/findings")
async def get_research_findings():
    """
    Aggregate all individual *_report.json files from research_findings/ and return them.
    This bridges the LangGraph agent's per-file output to the frontend polling endpoint.
    """
    findings: List[dict] = []
    target_dir = Path("research_findings")

    if not target_dir.exists():
        return {"findings": []}

    for filepath in sorted(target_dir.glob("*_report.json")):
        try:
            with filepath.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # Normalise field names so the frontend gets a consistent schema
            findings.append({
                "id":          filepath.stem,            # e.g. "CVE-2021-44228_report"
                "cve_id":      data.get("id", ""),
                "title":       data.get("title", "Unknown"),
                "severity":    data.get("severity", "unknown").upper(),
                "cvss_score":  data.get("cvss"),
                "cwe":         data.get("cwe", ""),
                "description": data.get("description", ""),
                "poc_code":    data.get("poc_code", ""),
                "discovered_at": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
                "affected_assets": [data.get("cwe", data.get("id", "unknown"))],
                "solution":    None,
            })
        except Exception:
            pass

    return {"findings": findings}


@router.get("/vulnerabilities")
async def get_vulnerabilities(
    severity: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
):
    """
    Alias of /findings that matches the frontend's original polling endpoint,
    returning data shaped as { vulnerabilities: [...], total_count, last_updated }.
    """
    raw = await get_research_findings()
    vulns = raw["findings"]

    if severity:
        vulns = [v for v in vulns if v.get("severity", "").upper() == severity.upper()]

    total = len(vulns)
    vulns = vulns[offset:offset + limit] if limit else vulns[offset:]

    return {
        "last_updated": datetime.now().isoformat(),
        "total_count": total,
        "returned_count": len(vulns),
        "vulnerabilities": vulns,
    }


@router.get("/stats")
async def get_research_stats():
    """Dashboard statistics aggregated from all research_findings files."""
    raw = await get_research_findings()
    vulns = raw["findings"]
    total = len(vulns)

    by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
    three_days_ago = datetime.now().timestamp() - (3 * 24 * 60 * 60)
    new_count = 0

    for v in vulns:
        sev = v.get("severity", "UNKNOWN").upper()
        by_severity[sev if sev in by_severity else "UNKNOWN"] += 1
        try:
            if datetime.fromisoformat(v["discovered_at"]).timestamp() >= three_days_ago:
                new_count += 1
        except Exception:
            pass

    return {
        "total_vulnerabilities": total,
        "new_last_3_days": new_count,
        "by_severity": by_severity,
        "last_updated": datetime.now().isoformat() if total else None,
    }


@router.get("/vulnerabilities/{cve_id}")
async def get_vulnerability_details(cve_id: str):
    """Get detailed information about a specific vulnerability by CVE ID."""
    raw = await get_research_findings()
    for v in raw["findings"]:
        if v.get("cve_id") == cve_id:
            return v
    raise HTTPException(status_code=404, detail=f"CVE {cve_id} not found")
