#!/usr/bin/env python3
"""Check GitHub PRs and fork status."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.integrations.github_api import GitHubClient

def main():
    client = GitHubClient()
    if not client.client:
        print("GitHub client not initialized")
        return
    
    user = client.client.get_user()
    print(f"Authenticated as: {user.login}")
    
    # Check if fork exists
    try:
        fork = client.client.get_repo(f"{user.login}/vulnerable-app-nodejs-express")
        print(f"Fork exists: {fork.full_name}")
        print(f"Fork default branch: {fork.default_branch}")
        
        # List branches on fork
        print(f"\nBranches on your fork:")
        for branch in fork.get_branches():
            print(f"  - {branch.name}")
    except Exception as e:
        print(f"Fork not found: {e}")
    
    # Check upstream
    try:
        upstream = client.client.get_repo("samoylenko/vulnerable-app-nodejs-express")
        print(f"\nUpstream: {upstream.full_name}")
        print(f"Upstream default branch: {upstream.default_branch}")
        
        # List all PRs from your fork
        print(f"\nAll PRs on upstream (state=all):")
        for pr in upstream.get_pulls(state="all")[:10]:
            print(f"  #{pr.number}: {pr.title}")
            print(f"    State: {pr.state}")
            print(f"    Head: {pr.head.label} -> Base: {pr.base.label}")
            print(f"    URL: {pr.html_url}")
            print()
    except Exception as e:
        print(f"Error checking upstream: {e}")

if __name__ == "__main__":
    main()
