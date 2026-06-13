"""
ouroboros/core.py — Central SDK orchestrator.

Wraps the full Ouroboros LangGraph pipeline:
  clone → RED scan → governance → BLUE fix → verify → PR → audit → docs

Two modes:
  • Full pipeline  — ``await sdk.scan(repo_url)``
  • Watch mode     — ``await sdk.watch(repo_url, interval)``
"""

import asyncio
import logging
import os
import shutil
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ouroboros.core")

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so ``src.*`` imports work.
# This handles 3 install scenarios:
#   1. Running from cloned repo (src/ is sibling of ouroboros/)
#   2. pip install from wheel (src/ is installed as a package)
#   3. pip install -e . (editable — src/ in original location)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Also check if src/ is inside the installed package (wheel scenario)
_INSTALLED_SRC = Path(__file__).resolve().parent.parent
for _candidate in [_PROJECT_ROOT, _INSTALLED_SRC, Path.cwd()]:
    if (_candidate / "src" / "__init__.py").exists():
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
        break


class Ouroboros:
    """
    Main SDK entry-point.

    Usage::

        from ouroboros import Ouroboros

        ouro   = Ouroboros("config.yaml")
        result = await ouro.scan("https://github.com/owner/repo")
        print(result["pr_url"])
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self._apply_env_overrides()

        # Lazy-loaded heavy components
        self._workflow = None
        self._gh_client = None

    # ==================================================================
    # Public API
    # ==================================================================

    async def scan(self, repo_url: str, **kwargs) -> Dict[str, Any]:
        """
        Run the complete Ouroboros pipeline on *repo_url*.

        Keyword args forwarded to the workflow:
            scan_profile  — "quick" | "standard" | "deep"  (default: "standard")
            create_pr     — bool  (default: True)
            branch        — target branch  (default: "main")
            user_id       — audit trail user  (default: "sdk-user")

        Returns a summary dict::

            {
              "success": True,
              "repo_url": "…",
              "scan_id": "SCAN-…",
              "vulnerabilities_found": 5,
              "critical_count": 1,
              "fixes_generated": 4,
              "risk_reduction_pct": 80,
              "pr_url": "https://github.com/…/pull/42",
              "docs_path": "/tmp/…/ouroboros-security-report.pdf",
              "deploy_safe": True,
              "all_verified": True,
            }
        """
        workflow = self._get_workflow()

        scan_id = kwargs.get(
            "scan_id",
            f"SCAN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-sdk",
        )

        input_data = {
            "repo_url": repo_url,
            "scan_id": scan_id,
            "user_id": kwargs.get("user_id", "sdk-user"),
            "scan_profile": kwargs.get("scan_profile", "standard"),
            "create_pr": kwargs.get("create_pr", True),
            "branch": kwargs.get("branch", "main"),
            "commit_sha": kwargs.get("commit_sha", "HEAD"),
        }

        logger.info("🐍 Ouroboros SDK — starting scan for %s", repo_url)
        final_state = await workflow.run(input_data)

        return self._build_summary(repo_url, final_state)

    async def scan_quick(self, repo_url: str, **kw) -> Dict[str, Any]:
        """Convenience: quick profile, no PR."""
        kw.setdefault("scan_profile", "quick")
        kw.setdefault("create_pr", False)
        return await self.scan(repo_url, **kw)

    async def scan_deep(self, repo_url: str, **kw) -> Dict[str, Any]:
        """Convenience: deep profile with privesc + lateral movement."""
        kw.setdefault("scan_profile", "deep")
        return await self.scan(repo_url, **kw)

    async def watch(self, repo_url: str, interval_seconds: int = 300):
        """Continuous monitoring — re-scans every *interval_seconds*."""
        from .continuous import ContinuousScanner

        scanner = ContinuousScanner(self, repo_url, interval_seconds)
        await scanner.start()

    # ------------------------------------------------------------------
    # Standalone helpers (use without full pipeline)
    # ------------------------------------------------------------------

    async def detect_vulnerabilities(
        self, repo_url: str, profile: str = "standard"
    ) -> List[Dict]:
        """
        Run only the RED agent scan (no fixes / PR).
        Returns a list of vulnerability dicts.
        """
        from src.agents import REDAgent
        from src.agents.red_agent import REDAgentInput

        agent = REDAgent()
        agent_input = REDAgentInput(
            repo_url=repo_url,
            scan_profile=profile,
        )
        output = await agent.execute(agent_input)
        return output.vulnerabilities if output else []

    async def generate_fixes(
        self,
        vulnerabilities: List[Dict],
        repo_path: str,
    ) -> List[Dict]:
        """
        Run only the BLUE agent on pre-existing vulnerability findings.
        Returns a list of fix dicts.
        """
        from src.agents import BLUEAgent
        from src.agents.blue_agent import BLUEAgentInput

        agent = BLUEAgent()
        fixes = []
        for vuln in vulnerabilities:
            blue_input = BLUEAgentInput(
                vulnerability_id=vuln.get("id", "unknown"),
                vulnerability_type=vuln.get("type", vuln.get("description", "")),
                location=vuln.get("location", {}),
                vulnerable_code=vuln.get("vulnerable_code", ""),
                cwe=vuln.get("cwe", ""),
                cvss=vuln.get("cvss", 0.0),
                language=vuln.get("language", "python"),
                sandbox_path=repo_path,
            )
            output = await agent.execute(blue_input)
            if output and output.fix_options:
                fixes.extend(
                    [
                        {
                            "vuln_id": vuln.get("id"),
                            "option": opt.option_number,
                            "diffs": [d.__dict__ for d in (opt.diffs or [])],
                            "confidence": opt.confidence_score,
                            "verdict": opt.verdict,
                        }
                        for opt in output.fix_options
                    ]
                )
        return fixes

    async def create_pr(
        self,
        repo_url: str,
        patches: List[Dict],
        branch_prefix: str = "ouroboros/auto-fix",
    ) -> str:
        """
        Create a GitHub PR with the given patches.
        Returns the PR HTML URL.
        """
        gh = self._get_github_client()
        pr_url = await gh.create_fix_pr(
            repo_url=repo_url,
            patches=patches,
            branch_prefix=branch_prefix,
        )
        return pr_url

    # ==================================================================
    # Internals
    # ==================================================================

    def _get_workflow(self):
        """Lazy-init the full LangGraph workflow."""
        if self._workflow is None:
            from src.orchestration.workflow import OuroborosWorkflow

            self._workflow = OuroborosWorkflow()
        return self._workflow

    def _get_github_client(self):
        if self._gh_client is None:
            from .github import GitHubClient

            token = self.config.get("github", {}).get("token", "")
            self._gh_client = GitHubClient(token)
        return self._gh_client

    def _build_summary(
        self, repo_url: str, state: Dict[str, Any]
    ) -> Dict[str, Any]:
        vulns = state.get("vulnerabilities", [])
        fixes = state.get("fixes", [])
        verification = state.get("verification_results", [])
        verified_count = sum(
            1 for r in verification if r.get("verified", False)
        )

        return {
            "success": not state.get("workflow_aborted", False),
            "repo_url": repo_url,
            "scan_id": state.get("scan_id", ""),
            "vulnerabilities_found": len(vulns),
            "critical_count": sum(
                1
                for v in vulns
                if (v.get("severity") or v.get("cvss_score", 0))
                and (
                    str(v.get("severity", "")).upper() == "CRITICAL"
                    or v.get("cvss_score", 0) >= 9.0
                )
            ),
            "fixes_generated": len(fixes),
            "verified_count": verified_count,
            "all_verified": state.get("all_verified", False),
            "risk_reduction_pct": (
                int((verified_count / len(vulns)) * 100) if vulns else 0
            ),
            "pr_url": state.get("pr_url"),
            "pr_number": state.get("pr_number"),
            "docs_path": state.get("final_report_url"),
            "deploy_safe": state.get("all_verified", False),
            "governance_decisions": state.get("governance_decisions", {}),
            "risk_scores": state.get("risk_scores", {}),
            "errors": state.get("errors", []),
            "aborted": state.get("workflow_aborted", False),
            "abort_reason": state.get("abort_reason"),
        }

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def _load_config(self, path: str) -> Dict[str, Any]:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"Config not found: {path}\n"
                "Run:  cp config.example.yaml config.yaml"
            )
        with open(p) as fh:
            return yaml.safe_load(fh) or {}

    def _apply_env_overrides(self):
        """
        Push SDK config values into environment variables so the
        existing ``config.settings.Settings`` (Pydantic) picks them up.
        """
        mapping = {
            ("github", "token"): "GITHUB_TOKEN",
            ("ollama", "url"): "OLLAMA_BASE_URL",
            ("database", "url"): "DATABASE_URL",
            ("redis", "url"): "REDIS_URL",
        }
        for keys, env_var in mapping.items():
            val = self.config
            for k in keys:
                val = val.get(k, {}) if isinstance(val, dict) else None
                if val is None:
                    break
            if val and isinstance(val, str):
                os.environ.setdefault(env_var, val)
