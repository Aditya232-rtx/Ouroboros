"""
Ouroboros AI - PyRIT Orchestrator
Orchestrates security scanning tools (Nuclei, Semgrep, Checkov, CodeQL)
"""

import asyncio
import logging
import subprocess
import shutil
import json
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class VulnerabilityFinding:
    """Individual finding from a security tool"""
    tool: str
    type: str
    severity: str
    file_path: str
    line_number: int
    description: str
    metadata: Dict[str, Any]


class PyRITOrchestrator:
    """
    Orchestrates security scanning tools via subprocess.
    Simulates Microsoft PyRIT's orchestration capabilities for V1.
    """

    def __init__(self):
        self.tools = {
            "nuclei": self._run_nuclei,
            "semgrep": self._run_semgrep,
            "checkov": self._run_checkov
        }

    async def run_scan(
        self, 
        target_path: str, 
        tools: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Run selected scanning tools in parallel against the target path.
        
        Args:
            target_path: Path to scan
            tools: List of tool names to run (default: semgrep, checkov)
        
        Returns:
            List of vulnerability findings
        """
        if tools is None:
            tools = ["semgrep", "checkov"]

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
        CRITICAL: No shell=True (per 03_CRITICAL_DO_NOT_FILE)
        """
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        # Some scanners return 1 for findings found
        if process.returncode != 0 and process.returncode != 1:
            logger.warning(
                f"Command failed: {' '.join(cmd)}\n"
                f"Stderr: {stderr.decode()}"
            )
            return ""
            
        return stdout.decode()

    async def _run_semgrep(self, target_path: str) -> List[VulnerabilityFinding]:
        """Run Semgrep SAST scan"""
        if not shutil.which("semgrep"):
            logger.warning("Semgrep not installed. Skipping.")
            return []

        cmd = [
            "semgrep",
            "--config=p/security-audit",
            "--config=p/owasp-top-10",
            "--json",
            target_path
        ]
        output = await self._run_command(cmd)
        
        findings = []
        try:
            data = json.loads(output) if output else {}
            for result in data.get("results", []):
                findings.append(VulnerabilityFinding(
                    tool="semgrep",
                    type=result.get("check_id", "unknown"),
                    severity=result.get("extra", {}).get("severity", "MEDIUM"),
                    file_path=result.get("path", ""),
                    line_number=result.get("start", {}).get("line", 0),
                    description=result.get("extra", {}).get("message", ""),
                    metadata=result.get("extra", {})
                ))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Semgrep output: {e}")
        
        return findings

    async def _run_checkov(self, target_path: str) -> List[VulnerabilityFinding]:
        """Run Checkov IaC scan"""
        if not shutil.which("checkov"):
            logger.warning("Checkov not installed. Skipping.")
            return []

        cmd = ["checkov", "-d", target_path, "-o", "json", "--quiet"]
        output = await self._run_command(cmd)

        findings = []
        try:
            data = json.loads(output) if output else []
            if isinstance(data, dict):
                data = [data]
            
            for framework_result in data:
                for result in framework_result.get("results", {}).get("failed_checks", []):
                    findings.append(VulnerabilityFinding(
                        tool="checkov",
                        type=result.get("check_id", "unknown"),
                        severity="HIGH",
                        file_path=result.get("file_path", ""),
                        line_number=result.get("file_line_range", [0])[0],
                        description=result.get("check_name", ""),
                        metadata={"guideline": result.get("guideline", "")}
                    ))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Checkov output: {e}")

        return findings

    async def _run_nuclei(self, target_path: str) -> List[VulnerabilityFinding]:
        """
        Run Nuclei scan.
        Note: Nuclei targets URLs, not local files.
        This is a placeholder for when local deployment is scanned.
        """
        # For V1 static code analysis, Nuclei is less applicable
        # It would be used if we spin up the application and scan it
        logger.info("Nuclei scan skipped for static code analysis")
        return []

    def _finding_to_dict(self, finding: VulnerabilityFinding) -> Dict[str, Any]:
        """Convert finding to dict format"""
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
