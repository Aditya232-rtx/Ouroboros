"""
Create PR Node - GitHub pull request creation
Orchestration node for PR creation

Flow: Fork target repo → Clone the fork → Branch → Apply fixes → Commit → Push → Create cross-repo PR
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any
from src.orchestration.state import OuroborosState
from src.integrations.github_api import github_client

logger = logging.getLogger(__name__)


def _apply_fixes_to_repo(repo_path: Path, state: OuroborosState) -> int:
    """
    Write verified fix diffs into the cloned repo.
    Returns the number of files written.
    """
    files_written = 0

    for fix_result in state.get("fixes", []):
        # Each fix_result comes from BLUEAgent.execute() and contains a "fixes" list of FixOption dicts
        selected_idx = fix_result.get("selected_fix", 1) - 1  # 1-indexed → 0-indexed
        fix_options = fix_result.get("fixes", [])

        if not fix_options or selected_idx < 0 or selected_idx >= len(fix_options):
            continue

        selected_fix = fix_options[selected_idx]
        code_diff = selected_fix.get("code_diff", {})
        file_path = code_diff.get("file", "")
        after_code = code_diff.get("after", "")

        if not file_path or not after_code:
            logger.warning(f"Skipping fix with empty file/code: {fix_result.get('vulnerability_id')}")
            continue

        target = repo_path / file_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(after_code, encoding="utf-8")
        files_written += 1
        logger.info(f"  Applied fix to {file_path}")

    return files_written


async def create_pr_node(state: OuroborosState) -> OuroborosState:
    """
    Node 8: Create GitHub PR with verified fixes.

    Steps:
      1. Fork the target repository to our GitHub account
      2. Clone the fork locally (origin = our fork)
      3. Create a feature branch
      4. Apply verified fixes to files
      5. Commit changes
      6. Push branch to origin (the fork)
      7. Create cross-repo PR  (head = our_user:branch → base = original repo:main)
    """
    logger.info("📤 Creating GitHub PR")

    try:
        # ── Extract identifiers ──────────────────────────────────────
        repo_full_name = state["repo_url"].replace("https://github.com/", "").replace(".git", "")
        branch_name = f"ouroboros-fixes-{state['scan_id']}"
        base_branch = state.get("branch", "main")

        verified_count = sum(1 for r in state["verification_results"] if r.get("verified"))
        total_vulns = len(state["vulnerabilities"])

        # ── Step 1: Fork ─────────────────────────────────────────────
        logger.info(f"  Step 1/7: Forking {repo_full_name}")
        fork_clone_url = github_client.fork_repository(repo_full_name)

        # GitHub needs a moment to finish creating the fork
        time.sleep(5)

        # ── Step 2: Clone the fork ───────────────────────────────────
        logger.info("  Step 2/7: Cloning fork")
        repo_path = github_client.clone_repository(
            repo_url=fork_clone_url,
            branch=base_branch
        )

        # ── Step 3: Create branch ───────────────────────────────────
        logger.info(f"  Step 3/7: Creating branch {branch_name}")
        github_client.create_branch(repo_path, branch_name)

        # ── Step 4: Apply fixes ─────────────────────────────────────
        logger.info("  Step 4/7: Applying verified fixes")
        files_written = _apply_fixes_to_repo(repo_path, state)

        if files_written == 0:
            logger.warning("No fix files were written — skipping PR creation")
            state["pr_url"] = ""
            state["pr_number"] = 0
            state["pr_error"] = "No verified fix files to commit"
            return state

        # ── Step 5: Commit ──────────────────────────────────────────
        logger.info(f"  Step 5/7: Committing {files_written} file(s)")
        commit_msg = (
            f"[Ouroboros] Fix {verified_count} verified vulnerabilities\n\n"
            f"Scan ID: {state['scan_id']}\n"
            f"Vulnerabilities found: {total_vulns}\n"
            f"Fixes verified: {verified_count}"
        )
        github_client.commit_changes(repo_path, commit_msg)

        # ── Step 6: Push to origin (the fork) ───────────────────────
        logger.info("  Step 6/7: Pushing to fork")
        github_client.push_branch(repo_path, branch_name)  # default remote="origin"

        # ── Step 7: Create cross-repo PR ────────────────────────────
        logger.info(f"  Step 7/7: Creating PR on {repo_full_name}")

        # Cross-repo PRs require head in "user:branch" format
        fork_owner = github_client.get_authenticated_user()
        head_ref = f"{fork_owner}:{branch_name}"

        pr_title = f"[Ouroboros] Security fixes: {verified_count} vulnerabilities resolved"
        pr_description = f"""## Ouroboros AI Security Scan Results

**Scan ID**: {state['scan_id']}
**Repository**: {state['repo_url']}
**Report**: {state.get('final_report_url', 'Pending (Generated after PR)')}

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

        pr_data = github_client.create_pull_request(
            repo_full_name=repo_full_name,
            title=pr_title,
            body=pr_description,
            head_branch=head_ref,         # "our_user:ouroboros-fixes-SCAN-xxx"
            base_branch=base_branch
        )

        state["pr_url"] = pr_data.get("pr_url", "")
        state["pr_number"] = pr_data.get("pr_number", 0)
        state["current_phase"] = "pr_created"

        logger.info(f"✅ PR created: {state.get('pr_url')}")

    except Exception as e:
        logger.error(f"PR creation failed: {e}")
        state["pr_url"] = ""
        state["pr_number"] = 0
        state["pr_error"] = str(e)

    return state
