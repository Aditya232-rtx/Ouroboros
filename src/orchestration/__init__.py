"""
Ouroboros AI - Workflow State Definition
TypedDict for LangGraph state management
"""

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime


class OuroborosState(TypedDict, total=False):
    """
    Complete state maintained across all workflow nodes.
    Per LangGraph best practices: MUST return full state from every node.
    """
    
    # ===== INPUT =====
    repo_url: str
    commit_sha: str
    branch: str
    scan_id: str
    user_id: str
    scan_profile: str  # quick|standard|deep
    
    # ===== RED AGENT OUTPUTS =====
    vulnerabilities: List[Dict[str, Any]]
    scan_complete: bool
    scan_statistics: Dict[str, Any]
    
    # ===== DOCUMENTATION AGENT OUTPUTS =====
    initial_report_url: str
    initial_report_id: str
    final_report_url: str
    final_report_id: str
    
    # ===== GOVERNANCE AGENT OUTPUTS =====
    prioritized_queue: List[Dict[str, Any]]
    governance_decisions: List[Dict[str, Any]]
    risk_scores: Dict[str, float]
    
    # ===== BLUE AGENT OUTPUTS =====
    fixes: List[Dict[str, Any]]
    fixes_applied: List[str]
    selected_fixes: List[Dict[str, Any]]
    
    # ===== VERIFICATION STATE =====
    verification_results: List[Dict[str, Any]]
    all_verified: bool
    retry_count: int
    unresolved_vulnerabilities: List[str]
    
    # ===== AUDIT OUTPUTS =====
    audit_entries: List[str]
    compliance_mappings: Dict[str, List[str]]
    
    # ===== GITHUB INTEGRATION =====
    pr_url: str
    pr_number: int
    branch_created: str
    
    # ===== METADATA =====
    workflow_start_time: str
    workflow_end_time: str
    context: Dict[str, Any]
    errors: List[Dict[str, Any]]
    current_phase: str  # scan|doc|governance|fix|verify|pr|audit
