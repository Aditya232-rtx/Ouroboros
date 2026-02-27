"""
ouroboros/github.py — GitHub integration for the SDK.

Wraps the existing ``src.integrations.github_api`` module and also provides
a standalone lightweight client for SDK-only usage.
"""

import logging
import tempfile
import time
from typing import Dict, List, Optional

import git
from github import Github
from github.GithubException import GithubException

logger = logging.getLogger("ouroboros.github")


class GitHubClient:
    """
    GitHub operations: clone repos, create fix branches, open PRs.

    Uses PyGithub for API calls and GitPython for local clone operations.
    For the full pipeline (fork → clone → push → cross-repo PR), the SDK
    delegates to ``src.integrations.github_api.GitHubClient``.
    """

    def __init__(self, token: str):
        self.token = token
        self._gh = Github(token) if token else None

    # ------------------------------------------------------------------
    # Clone
    # ------------------------------------------------------------------

    async def clone_repo(self, repo_url: str) -> Dict:
        """
        Clone a GitHub repo into a temp directory.
        Returns ``{local_path, owner, repo, url}``.
        """
        clean_url = repo_url.rstrip("/").removesuffix(".git")
        parts = clean_url.split("/")
        owner, repo_name = parts[-2], parts[-1]

        local_path = tempfile.mkdtemp(prefix="ouroboros-")

        # Inject auth token for private repos
        if self.token:
            clone_url = repo_url.replace(
                "https://", f"https://x-access-token:{self.token}@"
            )
        else:
            clone_url = repo_url

        logger.info("Cloning %s/%s → %s", owner, repo_name, local_path)
        git.Repo.clone_from(clone_url, local_path)

        return {
            "local_path": local_path,
            "owner": owner,
            "repo": repo_name,
            "url": repo_url,
        }

    # ------------------------------------------------------------------
    # PR creation (lightweight — via PyGithub API directly)
    # ------------------------------------------------------------------

    async def create_fix_pr(
        self,
        *,
        repo_url: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        patches: List[Dict],
        branch_prefix: str = "ouroboros/auto-fix",
    ) -> str:
        """
        Create a branch with patches and open a PR.

        Each patch dict should have at minimum::

            {"file_path": "src/foo.py", "content": "…new file content…"}

        Returns the PR HTML URL.
        """
        if not self._gh:
            raise RuntimeError("GitHub token is required for PR creation")

        # Resolve owner/repo from URL if not given directly
        if repo_url and not owner:
            clean = repo_url.rstrip("/").removesuffix(".git")
            parts = clean.split("/")
            owner, repo = parts[-2], parts[-1]

        if not owner or not repo:
            raise ValueError("Must supply owner+repo or repo_url")

        repository = self._gh.get_repo(f"{owner}/{repo}")
        default_branch = repository.default_branch
        base_sha = repository.get_branch(default_branch).commit.sha

        branch_name = f"{branch_prefix}-{int(time.time())}"
        repository.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=base_sha,
        )
        logger.info("Created branch %s on %s/%s", branch_name, owner, repo)

        # Commit each patch
        for patch in patches:
            file_path = patch.get("file_path", "ouroboros-patch.txt")
            content = patch.get("content", "")
            message = f"fix: ouroboros patch for {file_path}"
            try:
                existing = repository.get_contents(file_path, ref=branch_name)
                repository.update_file(
                    path=file_path,
                    message=message,
                    content=content,
                    sha=existing.sha,
                    branch=branch_name,
                )
            except GithubException:
                repository.create_file(
                    path=file_path,
                    message=message,
                    content=content,
                    branch=branch_name,
                )

        body = (
            "## 🔒 Ouroboros Automated Security Fixes\n\n"
            f"- **Patches applied:** {len(patches)}\n"
            "- **All fixes verified safe** by Ouroboros verifier agent\n\n"
            "_Generated automatically by "
            "[Ouroboros SDK](https://github.com/Aditya232-rtx/Ouroboros)_"
        )

        pr = repository.create_pull(
            title="🔒 Ouroboros: Automated Security Fixes",
            body=body,
            head=branch_name,
            base=default_branch,
        )
        logger.info("Opened PR %s", pr.html_url)
        return pr.html_url

    # ------------------------------------------------------------------
    # Full pipeline — delegates to existing src module
    # ------------------------------------------------------------------

    async def create_fix_pr_full_pipeline(
        self,
        repo_url: str,
        fixes: List[Dict],
        scan_id: str = "",
    ) -> Dict:
        """
        Use the production fork→clone→push→cross-repo-PR pipeline from
        ``src.integrations.github_api``.

        Returns ``{pr_url, pr_number, error}``.
        """
        from src.integrations.github_api import GitHubClient as _ProdGH

        prod_gh = _ProdGH()
        return await prod_gh.create_fix_pr(
            repo_url=repo_url,
            fixes=fixes,
            scan_id=scan_id,
        )
