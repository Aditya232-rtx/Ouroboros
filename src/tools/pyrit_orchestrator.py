"""PyRIT Orchestrator

This module provides the ``PyRITOrchestrator`` class which coordinates the execution
of various security scanning tool wrappers (Semgrep, Checkov, Nuclei, CodeQL).
It abstracts tool selection and aggregates findings into a single list.
"""

import asyncio
import logging
from typing import List, Dict

# Import the real wrapper classes
from src.tools.semgrep_wrapper import SemgrepWrapper
from src.tools.checkov_wrapper import CheckovWrapper
from src.tools.nuclei_wrapper import NucleiWrapper
from src.tools.codeql_wrapper import CodeQLWrapper

logger = logging.getLogger(__name__)


class PyRITOrchestrator:
    """Orchestrator to run selected security tools on a target repository.

    The ``run_scan`` method is asynchronous to match the existing RED agent
    implementation which uses ``await``. It accepts a ``target_path`` (the path to the
    cloned repository) and a list of tool identifiers (e.g., ``[\"semgrep\", \"checkov\"]``).
    It instantiates the corresponding wrapper classes, executes their scans, and
    returns a combined list of findings.
    """

    TOOL_MAP = {
        "semgrep": SemgrepWrapper,
        "checkov": CheckovWrapper,
        "nuclei": NucleiWrapper,
        "codeql": CodeQLWrapper,
    }

    def __init__(self):
        # No persistent state needed; wrappers are instantiated per run.
        logger.info("PyRITOrchestrator initialized")

    async def run_scan(self, target_path: str, tools: List[str]) -> List[Dict]:
        """Run the specified tools against ``target_path``.

        Parameters
        ----------
        target_path: str
            Path to the repository or codebase to scan.
        tools: List[str]
            List of tool identifiers. Supported identifiers are ``semgrep``, ``checkov``,
            ``nuclei`` and ``codeql``.

        Returns
        -------
        List[Dict]
            Aggregated findings from all executed tools.
        """
        findings: List[Dict] = []
        for tool_name in tools:
            wrapper_cls = self.TOOL_MAP.get(tool_name.lower())
            if not wrapper_cls:
                logger.warning("Unsupported tool requested: %s", tool_name)
                continue
            try:
                wrapper = wrapper_cls()
                logger.info("Running %s scan on %s", tool_name, target_path)
                # Wrappers expose a synchronous ``run_scan`` method. Execute it in a thread.
                tool_findings = await asyncio.to_thread(wrapper.run_scan, target_path)
                findings.extend(tool_findings)
                logger.info("%s returned %d findings", tool_name, len(tool_findings))
            except Exception as e:
                logger.error("Error running %s: %s", tool_name, e, exc_info=True)
        return findings

__all__ = ["PyRITOrchestrator"]
