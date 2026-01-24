"""
Create PR Node - GitHub pull request creation
Orchestration node for PR creation
"""

import logging
from typing import Dict, Any
from src.orchestration.state import OuroborosState
from src.integrations.github_api import github_client

logger = logging.getLogger(__name__)

async def create_pr_node(state: OuroborosState) -> OuroborosState:
    """
    Node 8: Create GitHub PR with verified fixes
    
    Creates pull request containing all verified fixes.
    """
    logger.info("📤 Creating GitHub PR")
    
    try:
        # Generate PR title and description
        verified_count = sum(1 for r in state["verification_results"] if r.get("verified"))
        total_vulns = len(state["vulnerabilities"])
        
        pr_title = f"[Ouroboros] Security fixes: {verified_count} vulnerabilities resolved"
        pr_description = f"""## Ouroboros AI Security Scan Results

**Scan ID**: {state['scan_id']}
**Repository**: {state['repo_url']}
**Report**: {state.get('final_report_url', 'N/A')}

### Summary
- 🔍 Vulnerabilities found: {total_vulns}
- ✅ Fixes verified: {verified_count}
- 📊 Success rate: {(verified_count/total_vulns*100) if total_vulns > 0 else 0:.1f}%

### Verified Fixes
"""
        
        for result in state["verification_results"]:
            if result.get("verified"):
                vuln_id = result.get("vulnerability_id")
                pr_description += f"- ✅ {vuln_id}\n"
        
        pr_description += "\n\n*This PR was automatically generated and verified by Ouroboros AI*"
        
        # Create PR
        pr_data = github_client.create_pull_request(
            repo_url=state["repo_url"],
            title=pr_title,
            body=pr_description,
            branch=f"ouroboros-fixes-{state['scan_id']}",
            base=state.get("branch", "main")
        )
        
        state["pr_url"] = pr_data.get("url", "")
        state["pr_number"] = pr_data.get("number", 0)
        state["current_phase"] = "pr_created"
        
        logger.info(f"✅ PR created: {state.get('pr_url')}")
        
    except Exception as e:
        logger.error(f"PR creation failed: {e}")
        state["pr_url"] = ""
        state["pr_number"] = 0
        state["pr_error"] = str(e)
    
    return state
