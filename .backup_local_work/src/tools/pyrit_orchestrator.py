import asyncio
import logging
import subprocess
import shutil
import json
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class VulnerabilityFinding:
    tool: str
    type: str
    severity: str
    file_path: str
    line_number: int
    description: str
    metadata: Dict[str, Any]

class PyRITOrchestrator:
    """
    Orchestrates security scanning tools (Nuclei, Semgrep, Checkov) via command line.
    Simulates Microsoft PyRIT's orchestration capabilities for V1.
    """

    def __init__(self):
        self.tools = {
            "nuclei": self._run_nuclei,
            "semgrep": self._run_semgrep,
            "checkov": self._run_checkov
        }

    async def run_scan(self, target_path: str, tools: List[str] = None) -> List[Dict[str, Any]]:
        """
        Run selected scanning tools in parallel against the target path.
        """
        if tools is None:
            tools = ["semgrep", "checkov"] # Default set

        tasks = []
        for tool_name in tools:
            if tool_name in self.tools:
                tasks.append(self.tools[tool_name](target_path))
            else:
                logger.warning(f"Tool {tool_name} not supported.")

        # Run all selected tools concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        aggregated_findings = []
        for res in results:
            if isinstance(res, list):
                aggregated_findings.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"Tool execution failed: {res}")

        return [self._finding_to_dict(f) for f in aggregated_findings]

    async def _run_command(self, cmd: List[str]) -> str:
        """
        Securely run a subprocess command.
        """
        # Security: No shell=True
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0 and process.returncode != 1: # Some scanners return 1 for findings found
            logger.warning(f"Command failed: {' '.join(cmd)}\nStderr: {stderr.decode()}")
            # We don't raise here because we want other tools to continue
            return ""
            
        return stdout.decode()

    async def _run_semgrep(self, target_path: str) -> List[VulnerabilityFinding]:
        """
        Run Semgrep scan.
        """
        if not shutil.which("semgrep"):
            logger.warning("Semgrep not installed. Skipping.")
            return []

        # --json output for parsing
        cmd = ["semgrep", "--config=p/security-audit", "--json", target_path]
        output = await self._run_command(cmd)
        
        findings = []
        try:
            data = json.loads(output)
            for result in data.get("results", []):
                findings.append(VulnerabilityFinding(
                    tool="semgrep",
                    type=result.get("check_id"),
                    severity=result.get("extra", {}).get("severity", "MEDIUM"),
                    file_path=result.get("path"),
                    line_number=result.get("start", {}).get("line"),
                    description=result.get("extra", {}).get("message"),
                    metadata=result.get("extra", {})
                ))
        except json.JSONDecodeError:
            logger.error("Failed to parse Semgrep output.")
        
        return findings

    async def _run_checkov(self, target_path: str) -> List[VulnerabilityFinding]:
        """
        Run Checkov scan.
        """
        if not shutil.which("checkov"):
            logger.warning("Checkov not installed. Skipping.")
            return []

        cmd = ["checkov", "-d", target_path, "-o", "json"]
        output = await self._run_command(cmd)

        findings = []
        try:
            # Checkov can return single JSON or list of JSONs (if multiple frameworks)
            data = json.loads(output)
            if isinstance(data, dict):
                data = [data]
            
            for framework_result in data:
                for result in framework_result.get("results", {}).get("failed_checks", []):
                    findings.append(VulnerabilityFinding(
                        tool="checkov",
                        type=result.get("check_id"),
                        severity="HIGH", # Checkov usually doesn't output CVSS severity directly in simple JSON
                        file_path=result.get("file_path"),
                        line_number=result.get("file_line_range", [0])[0],
                        description=result.get("check_name"),
                        metadata={"guideline": result.get("guideline")}
                    ))
        except json.JSONDecodeError:
            logger.error("Failed to parse Checkov output.")

        return findings

    async def _run_nuclei(self, target_path: str) -> List[VulnerabilityFinding]:
        """
        Run Nuclei scan. Note: Nuclei usually targets URLs, not local files, 
        unless using file-based templates. V1 assumes mostly code scanning.
        """
        # For codebase scan, Nuclei might not be the primary tool unless we scan a locally deployed app.
        # This implementation assumes we might be skipping it for static code analysis phase
        # or scanning localhost if the app was spun up.
        # For V1 MVP static scan, we'll return empty or mock.
        return []

    def _finding_to_dict(self, finding: VulnerabilityFinding) -> Dict[str, Any]:
        return {
            "tool": finding.tool,
            "type": finding.type,
            "severity": finding.severity,
            "location": {
                "file": finding.file_path,
                "line": finding.line_number
            },
            "description": finding.description,
            "metadata": finding.metadata
        }
