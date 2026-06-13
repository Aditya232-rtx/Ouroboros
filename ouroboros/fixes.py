"""
ouroboros/fixes.py — Fix generation wrapper.

Delegates to the existing BLUE Agent + Safety Gates pipeline
for production use, and provides a lightweight template-based
fallback for quick patching.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("ouroboros.fixes")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class FixGenerator:
    """
    Generates production-safe code patches from vulnerability findings.

    Modes:
      1. **Full** (default) — delegates to ``src.agents.BLUEAgent`` with
         safety gates + LLM-generated fixes.
      2. **Template** — uses Jinja2 templates for quick deterministic patches.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True,
        )

    async def generate(
        self,
        repo_path: str,
        vulns: List[Dict],
        mode: str = "full",
    ) -> Dict[str, Any]:
        """
        Generate patches for a list of vulnerabilities.

        Args:
            repo_path: Local path to the cloned repository.
            vulns: List of vulnerability dicts from RED agent.
            mode: ``"full"`` (LLM + safety gates) or ``"template"`` (Jinja2).

        Returns::

            {
              "patches": [{"vuln_id", "file_path", "content", "severity"}, …],
              "verified": bool,
              "risk_reduction": int,   # percentage 0–100
            }
        """
        if mode == "full":
            patches = await self._generate_full(repo_path, vulns)
        else:
            patches = await self._generate_template(repo_path, vulns)

        verified = self._verify_patches(patches)
        risk_reduction = self._estimate_risk_reduction(vulns, patches)

        return {
            "patches": patches,
            "verified": verified,
            "risk_reduction": risk_reduction,
        }

    # ------------------------------------------------------------------
    # Full pipeline — BLUE Agent + Safety Gates
    # ------------------------------------------------------------------

    async def _generate_full(
        self, repo_path: str, vulns: List[Dict]
    ) -> List[Dict]:
        """Invoke the real BLUE agent for each vulnerability."""
        try:
            from src.agents import BLUEAgent
            from src.agents.blue_agent import BLUEAgentInput
        except ImportError:
            logger.warning(
                "BLUE Agent not available — falling back to template mode"
            )
            return await self._generate_template(repo_path, vulns)

        agent = BLUEAgent()
        patches: List[Dict] = []

        for vuln in vulns:
            try:
                blue_input = BLUEAgentInput(
                    vulnerability_id=vuln.get("id", "unknown"),
                    vulnerability_type=vuln.get(
                        "type", vuln.get("description", "")
                    ),
                    location=vuln.get("location", {}),
                    vulnerable_code=vuln.get("vulnerable_code", ""),
                    cwe=vuln.get("cwe", ""),
                    cvss=vuln.get("cvss", 0.0),
                    language=vuln.get("language", "python"),
                    sandbox_path=repo_path,
                )
                output = await agent.execute(blue_input)
                if output and output.fix_options:
                    best = max(
                        output.fix_options,
                        key=lambda o: o.confidence_score or 0,
                    )
                    for diff in best.diffs or []:
                        patches.append(
                            {
                                "vuln_id": vuln.get("id"),
                                "file_path": diff.file_path,
                                "content": diff.after,
                                "severity": vuln.get("severity", "MEDIUM"),
                            }
                        )
            except Exception as exc:
                logger.error("BLUE agent failed for %s: %s", vuln.get("id"), exc)

        return patches

    # ------------------------------------------------------------------
    # Template-based fallback
    # ------------------------------------------------------------------

    async def _generate_template(
        self, repo_path: str, vulns: List[Dict]
    ) -> List[Dict]:
        """Render Jinja2 templates for quick deterministic patches."""
        patches: List[Dict] = []
        for vuln in vulns:
            template_name = self._pick_template(vuln)
            if not template_name:
                continue
            try:
                tpl = self.jinja_env.get_template(template_name)
                content = tpl.render(
                    vuln=vuln,
                    file_path=vuln.get("file", "unknown"),
                    file_content=vuln.get("vulnerable_code", ""),
                )
                patches.append(
                    {
                        "vuln_id": vuln.get("id", "unknown"),
                        "file_path": vuln.get("file", "unknown"),
                        "content": content,
                        "severity": vuln.get("severity", "MEDIUM"),
                    }
                )
            except Exception as exc:
                logger.warning("Template render failed: %s", exc)

        return patches

    def _pick_template(self, vuln: Dict) -> str | None:
        """Map vulnerability type to a Jinja2 template file."""
        desc = (vuln.get("description", "") + vuln.get("type", "")).lower()
        if "docker" in desc or "container" in desc:
            return "docker-security.patch.j2"
        if "api" in desc or "auth" in desc or "injection" in desc:
            return "api-hardening.patch.j2"
        return None

    # ------------------------------------------------------------------
    # Verification helpers
    # ------------------------------------------------------------------

    def _verify_patches(self, patches: List[Dict]) -> bool:
        return all(p.get("content") for p in patches)

    def _estimate_risk_reduction(
        self, vulns: List[Dict], patches: List[Dict]
    ) -> int:
        if not vulns:
            return 0
        return int((len(patches) / len(vulns)) * 100)
