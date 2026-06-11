"""
Ouroboros AI - GitHub API Integration
Repository cloning, branch creation, and PR management
"""

import logging
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile

from github import Github, GithubException
from config.settings import settings

logger = logging.getLogger(__name__)


class GitHubClient:
    """
    GitHub API client for repository operations.
    Per 03_CRITICAL_DO_NOT_FILE: All PRs require human review (V1).
    """
    
    def __init__(self):
        """Initialize GitHub client with token from settings"""
        if not settings.github_token:
            logger.warning("GitHub token not configured")
            self.client = None
        else:
            self.client = Github(settings.github_token)
    
    def clone_repository(
        self, 
        repo_url: str, 
        branch: str = "main",
        target_dir: Optional[Path] = None
    ) -> Path:
        """
        Clone a GitHub repository.
        
        Args:
            repo_url: GitHub repository URL
            branch: Branch to clone
            target_dir: Target directory (creates temp dir if None)
        
        Returns:
            Path to cloned repository
        """
        if target_dir is None:
            target_dir = Path(tempfile.mkdtemp(prefix="ouroboros_"))
        
        logger.info(f"Cloning {repo_url} branch {branch} to {target_dir}")
        
        # Security: No shell=True (per 03_CRITICAL_DO_NOT_FILE)
        cmd = [
            "git", "clone",
            "--branch", branch,
            "--single-branch",
            repo_url,
            str(target_dir)
        ]
        
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            logger.info(f"Successfully cloned {repo_url}")
            
            # Configure git identity for this repository
            logger.info("Configuring git identity for Ouroboros")
            subprocess.run(["git", "-C", str(target_dir), "config", "user.name", "ouroboros-ai-code"], check=True)
            subprocess.run(["git", "-C", str(target_dir), "config", "user.email", "ouroboros1679@gmail.com"], check=True)
            
            return target_dir
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository: {e.stderr}")
            raise
    
    def create_branch(
        self, 
        repo_path: Path, 
        branch_name: str
    ) -> str:
        """
        Create a new branch in the repository.
        
        Args:
            repo_path: Path to git repository
            branch_name: Name of new branch
        
        Returns:
            Branch name
        """
        logger.info(f"Creating branch {branch_name}")
        
        cmd = ["git", "-C", str(repo_path), "checkout", "-b", branch_name]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return branch_name
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create branch: {e.stderr}")
            raise
    
    def commit_changes(
        self,
        repo_path: Path,
        message: str,
        files: Optional[List[str]] = None
    ) -> str:
        """
        Commit changes to repository.
        
        Args:
            repo_path: Path to repository
            message: Commit message
            files: List of files to add (None = add all)
        
        Returns:
            Commit SHA
        """
        logger.info(f"Committing changes: {message}")
        
        # Add files
        if files:
            for file in files:
                cmd = ["git", "-C", str(repo_path), "add", file]
                subprocess.run(cmd, check=True)
        else:
            cmd = ["git", "-C", str(repo_path), "add", "-A"]
            subprocess.run(cmd, check=True)
        
        # Commit
        cmd = ["git", "-C", str(repo_path), "commit", "-m", message]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Get commit SHA
        cmd = ["git", "-C", str(repo_path), "rev-parse", "HEAD"]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        commit_sha = result.stdout.strip()
        
        logger.info(f"Created commit {commit_sha}")
        return commit_sha
    
    def fork_repository(self, repo_full_name: str) -> str:
        """
        Fork a repository to the authenticated user's account.
        
        Args:
            repo_full_name: "owner/repo" to fork
            
        Returns:
            Clone URL of the new fork (e.g. https://github.com/my-user/repo.git)
        """
        if not self.client:
            raise ValueError("GitHub client not initialized")
            
        logger.info(f"Forking {repo_full_name}...")
        try:
            user = self.client.get_user()
            original_repo = self.client.get_repo(repo_full_name)
            fork = user.create_fork(original_repo)
            
            logger.info(f"Forked to {fork.html_url}")
            return fork.clone_url
        except GithubException as e:
            logger.error(f"Failed to fork repository: {e}")
            raise
    
    def create_pull_request(
        self,
        repo_full_name: str,  # e.g., "owner/repo"
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        reviewers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a GitHub Pull Request.
        
        Per 03_CRITICAL_DO_NOT_FILE:
        - V1: NO auto-merge
        - Requires 2x human review minimum
        
        Args:
            repo_full_name: Repository in format "owner/repo"
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch
            reviewers: List of GitHub usernames to request review
        
        Returns:
            PR details {pr_number, pr_url, reviewers}
        """
        if not self.client:
            raise ValueError("GitHub client not initialized")
        
        logger.info(f"Creating PR: {title}")
        logger.info(f"  Target repo: {repo_full_name}")
        logger.info(f"  Head: {head_branch}")
        logger.info(f"  Base: {base_branch}")
        
        try:
            repo = self.client.get_repo(repo_full_name)
            logger.info(f"  Got repo: {repo.full_name} (default branch: {repo.default_branch})")
            
            # Create PR
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            
            logger.info(f"✅ PR API Response:")
            logger.info(f"   - PR Number: {pr.number}")
            logger.info(f"   - PR URL: {pr.html_url}")
            logger.info(f"   - PR State: {pr.state}")
            logger.info(f"   - PR Head: {pr.head.ref} (sha: {pr.head.sha[:7]})")
            logger.info(f"   - PR Base: {pr.base.ref}")
            
            # Request reviewers (minimum 2 for V1)
            if reviewers and len(reviewers) >= 2:
                pr.create_review_request(reviewers=reviewers)
            else:
                logger.warning("V1 requires minimum 2 reviewers. PR created without review requests.")
            
            logger.info(f"Created PR #{pr.number}: {pr.html_url}")
            
            return {
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "reviewers": reviewers or []
            }
        
        except GithubException as e:
            logger.error(f"Failed to create PR: {e}")
            logger.error(f"  Status: {e.status}")
            logger.error(f"  Data: {e.data}")
            raise


# Global instance
github_client = GitHubClient()
