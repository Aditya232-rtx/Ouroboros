from typing import TypedDict, List, Dict, Any, Optional

class OuroborosState(TypedDict):
    """
    State schema for the Ouroboros orchestration workflow.
    Shared data structure passed between all graph nodes.
    """
    # Metadata
    repo_url: str
    scan_id: str
    user_id: str
    scan_profile: str
    commit_sha: str
    branch: str
    create_pr: bool
    working_dir: str
    
    # Workflow control
    current_phase: str
    retry_count: int
    workflow_start_time: str
    workflow_end_time: Optional[str]
    errors: List[str]
    
    # Data artifacts
    vulnerabilities: List[Dict[str, Any]]
    scan_complete: bool
    scan_statistics: Dict[str, Any]
    
    # Documentation
    initial_report_url: Optional[str]
    initial_report_id: Optional[str]
    final_report_url: Optional[str]
    final_report_id: Optional[str]
    
    # Governance
    prioritized_queue: List[Dict[str, Any]]
    governance_decisions: Dict[str, Any]
    risk_scores: Dict[str, float]
    
    # Remediation
    fixes: List[Dict[str, Any]]
    verification_results: List[Dict[str, Any]]
    all_verified: bool
    
    # PR & Audit
    pr_url: Optional[str]
    pr_number: Optional[int]
    pr_error: Optional[str]
    audit_entries: List[str]

__all__ = ["OuroborosState"]
