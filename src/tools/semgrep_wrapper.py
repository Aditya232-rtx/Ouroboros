# src/tools/semgrep_wrapper.py
"""Semgrep wrapper for code security scanning.

This module provides a thin Python wrapper around the `semgrep` CLI.
It runs Semgrep with the supplied configuration and returns a list of findings
as Python dictionaries.

The implementation assumes that the `semgrep` binary is installed and available
on the system PATH. If it is not present, an informative `RuntimeError` is raised.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class SemgrepWrapper:
    """Wrapper class for executing Semgrep scans.

    Parameters
    ----------
    config_path: str, optional
        Path to the Semgrep configuration directory or a specific rules file.
        Defaults to the project's ``semgrep`` directory if it exists.
    """

    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Default to None, let run_scan pick up settings
            self.config_path = None
            
        logger.info("SemgrepWrapper initialized")

    def run_scan(self, target_path: str) -> List[Dict]:
        """Run Semgrep against ``target_path``.

        The command executed is equivalent to:
        ``semgrep --config <config_path> --json <target_path>``

        Returns
        -------
        List[Dict]
            A list of finding dictionaries parsed from Semgrep's JSON output.
        """
        target = Path(target_path)
        if self.config_path and self.config_path.exists():
            config_arg = str(self.config_path)
        else:
            from config.settings import settings
            config_arg = settings.semgrep_rules
        
        # Build command with multiple --config flags
        cmd = ["semgrep"]
        for rule in config_arg.split(','):
            cmd.extend(["--config", rule.strip()])
            
        cmd.extend(["--json", str(target)])
        logger.debug("Running Semgrep command: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as e:
            raise RuntimeError("Semgrep binary not found. Ensure it is installed and on PATH.") from e

        if result.returncode not in (0, 1):  # 0 = no findings, 1 = findings
            logger.error("Semgrep failed with code %s: %s", result.returncode, result.stderr)
            raise RuntimeError(f"Semgrep execution failed: {result.stderr}")

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Semgrep JSON output.")
            raise RuntimeError("Invalid JSON output from Semgrep.") from e

        findings = output.get("results", [])
        logger.info("Semgrep returned %d findings.", len(findings))
        return findings
