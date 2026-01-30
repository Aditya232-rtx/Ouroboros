#!/usr/bin/env python3
import asyncio
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
import sys
import os

# Setup path to import from src
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.red_agent import REDAgent
from src.agents.governance_agent import GovernanceAgent
from src.agents.blue_agent import BLUEAgent
from src.integrations.github_api import GitHubClient
from config.settings import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def read_file_content(sandbox_path: str, file_path: str) -> str:
    """Read actual file content from sandbox path."""
    if not sandbox_path or not file_path:
        return ""
    
    full_path = Path(sandbox_path) / file_path
    if full_path.exists():
        try:
            return full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Failed to read {full_path}: {e}")
    return ""


async def run_full_cycle():
    logger.info("🚀 Starting Full Cycle Test (Red -> Governance -> Blue -> PR)")
    
    # Target
    target_repo = "https://github.com/samoylenko/vulnerable-app-nodejs-express.git"
    
    # 1. RED AGENT
    logger.info(f"🔴 [Phase 1] Running Red Agent Scan against {target_repo}")
    red_agent = REDAgent()
    red_result = await red_agent.execute({
        "repo_url": target_repo,
        "scan_profile": "standard"
    })
    
    vulnerabilities = red_result.get("vulnerabilities", [])
    sandbox_path = red_result.get("sandbox_path", "")  # Get sandbox path from Red Agent
    logger.info(f"✅ Red Agent found {len(vulnerabilities)} vulnerabilities")
    if sandbox_path:
        logger.info(f"📂 Sandbox path: {sandbox_path}")
    
    if not vulnerabilities:
        logger.error("No vulnerabilities found! Aborting test.")
        return

    # 2. GOVERNANCE AGENT
    logger.info("⚖️ [Phase 2] Running Governance Agent")
    gov_agent = GovernanceAgent()
    gov_result = await gov_agent.execute({
        "vulnerabilities": vulnerabilities,
        "environment": "production"
    })
    
    prioritized_queue = gov_result.get("prioritized_queue", [])
    logger.info(f"✅ Governance prioritized {len(prioritized_queue)} items")
    
    # 3. BLUE AGENT - Fix ALL vulnerabilities
    logger.info("🔵 [Phase 3] Running Blue Agent (Fix Generation for ALL vulnerabilities)")
    blue_agent = BLUEAgent()
    
    # Filter out invalid vulnerabilities:
    # 1. N/A or empty file paths (can't fix without knowing the file)
    # 2. Dockerfile issues if we auto-generated the Dockerfile
    invalid_file_values = {"n/a", "na", "unknown", "", "none"}
    
    filtered_queue = []
    docker_filtered = 0
    invalid_filtered = 0
    
    for v in prioritized_queue:
        file_path = v.get("location", {}).get("file", "").strip()
        vuln_type = v.get("type", "").lower()
        vuln_id = v.get("id", "").lower()
        
        # Skip vulnerabilities with invalid/missing file paths
        if file_path.lower() in invalid_file_values:
            invalid_filtered += 1
            continue
        
        # Skip auto-generated Dockerfile issues (check if it was in original repo)
        # For now, skip all Docker-related issues from checkov/trivy (they scan our generated Dockerfile)
        if "dockerfile" in vuln_type or "docker" in vuln_id or file_path.lower() == "dockerfile":
            # Only skip if it's a common auto-generated issue
            if any(x in vuln_type for x in ["healthcheck", "root_user", "user_instruction"]):
                docker_filtered += 1
                continue
        
        filtered_queue.append(v)
    
    if docker_filtered > 0:
        logger.info(f"📋 Filtered out {docker_filtered} auto-generated Docker vulns")
    if invalid_filtered > 0:
        logger.info(f"📋 Filtered out {invalid_filtered} vulns with invalid/missing file paths")
    
    all_fixes = []  # Collect all fixes for all vulnerabilities
    
    for vuln_idx, vuln in enumerate(filtered_queue):
        vuln_id = vuln.get('id', f'VULN-{vuln_idx}')
        vuln_type = vuln.get('type', 'unknown')
        logger.info(f"\n{'='*60}")
        logger.info(f"🔧 [{vuln_idx + 1}/{len(filtered_queue)}] Fixing: {vuln_id} ({vuln_type})")
        logger.info(f"{'='*60}")
        
        # Get file path from location
        file_path = vuln.get("location", {}).get("file", "")
        
        # Read actual file content from sandbox if available
        vuln_code = vuln.get("vulnerable_code", "")
        if not vuln_code and sandbox_path and file_path:
            logger.info(f"📖 Reading file from sandbox: {file_path}")
            vuln_code = read_file_content(sandbox_path, file_path)
            if vuln_code:
                logger.info(f"✅ Read {len(vuln_code)} bytes")
            else:
                logger.warning(f"⚠️ Could not read file {file_path}")
        
        if not vuln_code:
            vuln_code = "# Vulnerable code could not be read"
        
        # Infer language from file extension
        language = "python"
        if file_path.endswith(".java"): language = "java"
        elif file_path.endswith(".js"): language = "javascript"
        elif file_path.endswith(".ts"): language = "typescript"
        elif file_path.endswith(".go"): language = "go"
        elif file_path.endswith(".php"): language = "php"
            
        blue_input = {
            "vulnerability_id": vuln_id,
            "vulnerability_type": vuln_type,
            "vulnerability_location": vuln.get("location", {}),
            "vulnerable_code": vuln_code,
            "cwe": vuln.get("cwe", "CWE-Unknown"),
            "cvss": vuln.get("cvss", 5.0),
            "language": language,
            "sandbox_path": sandbox_path
        }
        
        blue_result = await blue_agent.execute(blue_input)
        
        fixes = blue_result.get("fixes", [])
        if fixes:
            logger.info(f"✅ Generated {len(fixes)} fix options for {vuln_id}")
            for i, fix in enumerate(fixes):
                logger.info(f"   Option {i+1}: {fix.get('description', 'N/A')} (confidence: {fix.get('confidence', 0):.0%})")
            
            # Select the best fix (highest confidence)
            selected_idx = blue_result.get("selected_fix", 1) - 1
            if 0 <= selected_idx < len(fixes):
                selected_fix = fixes[selected_idx]
            else:
                selected_fix = fixes[0]
            
            all_fixes.append({
                "vulnerability": vuln,
                "selected_fix": selected_fix,
                "all_options": fixes
            })
            logger.info(f"✅ Selected: {selected_fix.get('description')}")
        else:
            logger.warning(f"⚠️ No fixes generated for {vuln_id}")
    
    if not all_fixes:
        logger.error("❌ No fixes were generated for any vulnerability!")
        return
    
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 SUMMARY: Generated fixes for {len(all_fixes)}/{len(prioritized_queue)} vulnerabilities")
    logger.info(f"{'='*60}")

    # 4. GITHUB PR (Integration) - Create a single PR with ALL fixes
    logger.info("\n🐙 [Phase 4] Creating Pull Request with ALL fixes")
    
    client = GitHubClient()
    if not client.client:
        logger.error("GitHub client not initialized. Skipping PR creation.")
        return

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    target_repo_name = target_repo.replace("https://github.com/", "").replace(".git", "")
    branch_name = f"security-fixes-{timestamp}"
    
    try:
        # Fork & Clone workflow
        logger.info(f"Forking {target_repo_name}...")
        fork_url = client.fork_repository(target_repo_name)
        
        # Clone Fork
        target_dir = Path("/tmp") / f"ouroboros_fix_{timestamp}"
        clean_url = fork_url.replace("https://", "")
        auth_url = f"https://{settings.github_token}@{clean_url}"
        
        # Helper to run git
        def run_git(args, cwd=None):
            subprocess.run(["git"] + args, cwd=str(cwd) if cwd else None, check=True)

        import subprocess
        logger.info(f"Cloning fork to {target_dir}")
        run_git(["clone", auth_url, str(target_dir)])
        
        # Configure git
        run_git(["-C", str(target_dir), "config", "user.email", "ouroboros@security.ai"])
        run_git(["-C", str(target_dir), "config", "user.name", "Ouroboros AI"])
        
        # Checkout Branch
        logger.info(f"Creating branch {branch_name}")
        run_git(["-C", str(target_dir), "checkout", "-b", branch_name])
        
        # Helper: Normalize whitespace for fuzzy matching
        def normalize_ws(s):
            import re
            return re.sub(r'\s+', ' ', s.strip())
        
        # Helper: Sanitize file paths from LLM output
        def sanitize_file_path(file_path: str, sandbox_path: str = "") -> str:
            """
            Clean up file paths that may have:
            - Absolute /tmp/... prefixes from sandbox
            - Fake /app/... prefixes from LLM hallucination
            - Leading slashes
            """
            if not file_path:
                return ""
            
            # Remove common LLM hallucination prefixes
            prefixes_to_strip = [
                "/path/to/", "path/to/",  # Common LLM placeholder
                "/actual/", "actual/",    # Another common placeholder
                "/app/", "/src/", "/code/", "/project/",
                "app/", "src/", "code/", "project/"
            ]
            
            # Also remove sandbox path prefix if present
            if sandbox_path and file_path.startswith(sandbox_path):
                file_path = file_path[len(sandbox_path):].lstrip("/")
            
            # Strip /tmp/ouroboros... prefixes
            if "/tmp/ouroboros" in file_path:
                parts = file_path.split("/tmp/ouroboros")
                if len(parts) > 1:
                    # Get everything after the sandbox directory
                    remaining = parts[-1]
                    # Remove the timestamp directory (e.g., /2026-01-30T.../rest)
                    if "/" in remaining:
                        remaining = "/".join(remaining.split("/")[2:])
                    file_path = remaining
            
            # Strip common prefixes
            for prefix in prefixes_to_strip:
                if file_path.startswith(prefix):
                    file_path = file_path[len(prefix):]
                    break
            
            # Remove leading slash
            file_path = file_path.lstrip("/")
            
            return file_path
        
        # Apply ALL fixes
        files_changed = set()
        fix_descriptions = []
        
        for fix_data in all_fixes:
            vuln = fix_data["vulnerability"]
            selected_fix = fix_data["selected_fix"]
            vuln_id = vuln.get("id", "unknown")
            
            logger.info(f"\n📝 Applying fix for {vuln_id}...")
            
            # Get file path from fix or vulnerability
            file_to_fix = selected_fix.get('code_diff', {}).get('file', '')
            
            # Sanitize the path (remove /tmp/..., /app/... prefixes)
            file_to_fix = sanitize_file_path(file_to_fix, sandbox_path)
            
            # Validate file path - reject placeholders
            invalid_paths = ["unknown", "N/A", "path/to/file", "/path/to/file", "/path", ""]
            if not file_to_fix or file_to_fix in invalid_paths or file_to_fix.startswith("/path"):
                # Fallback to vulnerability location
                vuln_file = vuln.get("location", {}).get("file", "")
                file_to_fix = sanitize_file_path(vuln_file, sandbox_path)
                
            if not file_to_fix or file_to_fix in invalid_paths:
                logger.warning(f"⚠️ Skipping {vuln_id} - no valid file path")
                continue
            
            logger.info(f"   Target file: {file_to_fix}")
                
            fix_path = target_dir / file_to_fix
            
            if not fix_path.exists():
                logger.warning(f"⚠️ File {file_to_fix} not found in repo, skipping")
                continue
            
            original_content = fix_path.read_text()
            before_code = selected_fix.get('code_diff', {}).get('before', '').strip()
            after_code = selected_fix.get('code_diff', {}).get('after', '').strip()
            
            if not after_code:
                logger.warning(f"⚠️ No fix code for {vuln_id}, skipping")
                continue
            
            # Get vulnerability line info for targeted replacement
            vuln_line = vuln.get('location', {}).get('line', 0)
            
            # Smart Replacement Logic
            applied = False
            
            # Method 1: Exact match replacement
            if before_code and before_code in original_content:
                logger.info(f"  ✅ Exact match found, applying patch to {file_to_fix}")
                new_content = original_content.replace(before_code, after_code, 1)
                fix_path.write_text(new_content)
                applied = True
                
            # Method 2: Normalized whitespace match
            elif before_code and normalize_ws(before_code) in normalize_ws(original_content):
                logger.info(f"  ✅ Normalized match found, applying patch to {file_to_fix}")
                new_content = original_content.replace(before_code.strip(), after_code, 1)
                fix_path.write_text(new_content)
                applied = True
                
            # Method 3: Line-based replacement (when we know the vulnerable line)
            elif vuln_line > 0:
                logger.info(f"  🎯 Using line-based fix at line {vuln_line}")
                lines = original_content.split('\n')
                if vuln_line <= len(lines):
                    # Replace the vulnerable line and surrounding context
                    # Insert the fix code at the vulnerable line
                    indent = len(lines[vuln_line - 1]) - len(lines[vuln_line - 1].lstrip())
                    indent_str = ' ' * indent
                    
                    # Format after_code with proper indentation
                    fixed_lines = []
                    for line in after_code.split('\n'):
                        if line.strip():
                            fixed_lines.append(indent_str + line.lstrip())
                        else:
                            fixed_lines.append('')
                    
                    # Replace the vulnerable line with the fix
                    lines[vuln_line - 1] = '\n'.join(fixed_lines)
                    new_content = '\n'.join(lines)
                    fix_path.write_text(new_content)
                    applied = True
                    logger.info(f"  ✅ Applied line-based fix at line {vuln_line}")
                else:
                    logger.warning(f"  ⚠️ Line {vuln_line} exceeds file length ({len(lines)} lines)")
            
            # Method 4: Skip if no matching strategy works (don't append garbage)
            if not applied:
                logger.warning(f"  ⚠️ Could not apply fix for {vuln_id} - no matching strategy")
                logger.warning(f"     Suggestion: Manual review required for {file_to_fix}")
                continue
            
            if applied:
                files_changed.add(file_to_fix)
                fix_descriptions.append(f"- **{vuln_id}** ({vuln.get('type', 'unknown')}): {selected_fix.get('description', 'Fixed')}")
        
        if not files_changed:
            logger.error("❌ No fixes could be applied!")
            return
        
        # Stage and commit all changes
        logger.info(f"\n📦 Committing {len(files_changed)} files...")
        for f in files_changed:
            run_git(["-C", str(target_dir), "add", f])
        
        commit_msg = f"fix: Resolve {len(all_fixes)} security vulnerabilities\n\nFixed by Ouroboros AI Security System"
        run_git(["-C", str(target_dir), "commit", "-m", commit_msg])
        
        # Push
        logger.info("🚀 Pushing to remote...")
        run_git(["-C", str(target_dir), "push", "-u", "origin", branch_name])
        
        # Create PR
        logger.info("📬 Creating Pull Request...")
        user = client.client.get_user().login
        head_ref = f"{user}:{branch_name}"
        
        # Get the default branch from the upstream repo
        target_repo_obj = client.client.get_repo(target_repo_name)
        default_branch = target_repo_obj.default_branch
        logger.info(f"📍 PR Details:")
        logger.info(f"   - Target Repo (upstream): {target_repo_name}")
        logger.info(f"   - Head Branch: {head_ref}")
        logger.info(f"   - Base Branch: {default_branch}")
        logger.info(f"   - Fork owner: {user}")
        
        # Build PR body with all fixes
        pr_body = f"""## 🛡️ Security Fixes by Ouroboros AI

This PR addresses **{len(all_fixes)} security vulnerabilities** detected during automated scanning.

### Vulnerabilities Fixed:
{chr(10).join(fix_descriptions)}

### Scan Details:
- **Scanner**: Ouroboros AI Security System
- **Date**: {datetime.now().isoformat()}
- **Files Changed**: {len(files_changed)}

### Note
Please review the changes carefully do not merge only raise a pull request with proper documenting.

---
*Automated security fix by [Ouroboros AI](https://github.com/ouroboros-ai-code)*
"""
        
        pr = client.create_pull_request(
            repo_full_name=target_repo_name,
            title=f"🔒 Security Fix: {len(all_fixes)} vulnerabilities addressed",
            body=pr_body,
            head_branch=head_ref,
            base_branch=default_branch
        )
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎉 SUCCESS! Full Cycle Complete!")
        logger.info(f"{'='*60}")
        logger.info(f"📊 Vulnerabilities found: {len(vulnerabilities)}")
        logger.info(f"🔧 Fixes generated: {len(all_fixes)}")
        logger.info(f"📁 Files modified: {len(files_changed)}")
        logger.info(f"🔗 PR URL: {pr.get('pr_url', 'N/A')}")
        
    except Exception as e:
        logger.error(f"❌ PR Creation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_full_cycle())
