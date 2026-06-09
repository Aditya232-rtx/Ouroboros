# src/tools/checkov_wrapper.py
"""Checkov wrapper for infrastructure-as-code security scanning.

This module provides a thin Python wrapper around the `checkov` CLI.
It runs Checkov against a given target directory and returns a list of findings
as Python dictionaries.

The implementation assumes that the `checkov` binary is installed and available
on the system PATH. If it is not present, a clear `RuntimeError` is raised.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class CheckovWrapper:
    """Wrapper class for executing Checkov scans.

    Parameters
    ----------
    config_path: Optional[str]
        Path to a custom Checkov configuration file (e.g., `.checkov.yaml`).
        If ``None``, the default configuration is used.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else None
        if self.config_path and not self.config_path.exists():
            logger.warning("Checkov config path %s does not exist; ignoring.", self.config_path)
        logger.info("CheckovWrapper initialized with config %s", self.config_path)

    def run_scan(self, target_path: str) -> List[Dict]:
        """Run Checkov against ``target_path``.

        The command executed is equivalent to:
        ``checkov -d <target_path> -o json``
        Optionally ``--config-file`` is added if a config path is provided.

        Returns
        -------
        List[Dict]
            A list of finding dictionaries parsed from Checkov's JSON output.
        """
        target = Path(target_path)
        if not target.exists():
            raise FileNotFoundError(f"Target path {target_path} does not exist.")

        cmd = ["checkov", "-d", str(target), "-o", "json"]
        if self.config_path:
            cmd.extend(["--config-file", str(self.config_path)])

        logger.debug("Running Checkov command: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as e:
            raise RuntimeError("Checkov binary not found. Ensure it is installed and on PATH.") from e

        if result.returncode not in (0, 1):  # 0 = no findings, 1 = findings
            logger.error("Checkov failed with code %s: %s", result.returncode, result.stderr)
            raise RuntimeError(f"Checkov execution failed: {result.stderr}")

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Checkov JSON output.")
            raise RuntimeError("Invalid JSON output from Checkov.") from e

        findings = output.get("results", [])
        logger.info("Checkov returned %d findings.", len(findings))
        return findings
