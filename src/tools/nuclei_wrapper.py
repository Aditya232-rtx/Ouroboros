# src/tools/nuclei_wrapper.py
"""Nuclei wrapper for web vulnerability scanning.

This module provides a thin Python wrapper around the `nuclei` CLI.
It runs Nuclei against a given target directory (or URL) and returns a list of findings
as Python dictionaries.

The implementation assumes that the `nuclei` binary is installed and available
on the system PATH. If it is not present, a clear `RuntimeError` is raised.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class NucleiWrapper:
    """Wrapper class for executing Nuclei scans.

    Parameters
    ----------
    templates_path: Optional[str]
        Path to a directory containing Nuclei templates. If ``None``, Nuclei's default
        template location is used.
    """

    def __init__(self, templates_path: Optional[str] = None):
        self.templates_path = Path(templates_path) if templates_path else None
        if self.templates_path and not self.templates_path.exists():
            logger.warning("Nuclei templates path %s does not exist; ignoring.", self.templates_path)
        logger.info("NucleiWrapper initialized with templates %s", self.templates_path)

    def run_scan(self, target_path: str) -> List[Dict]:
        """Run Nuclei against ``target_path``.

        The command executed is equivalent to:
        ``nuclei -target <target_path> -json``
        Optionally ``-templates`` is added if a custom templates directory is provided.

        Returns
        -------
        List[Dict]
            A list of finding dictionaries parsed from Nuclei's JSON output.
        """
        target = Path(target_path)
        if not target.exists():
            raise FileNotFoundError(f"Target path {target_path} does not exist.")

        cmd = ["nuclei", "-target", str(target), "-json"]
        if self.templates_path:
            cmd.extend(["-templates", str(self.templates_path)])

        logger.debug("Running Nuclei command: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as e:
            raise RuntimeError("Nuclei binary not found. Ensure it is installed and on PATH.") from e

        if result.returncode not in (0, 1):  # 0 = no findings, 1 = findings
            logger.error("Nuclei failed with code %s: %s", result.returncode, result.stderr)
            raise RuntimeError(f"Nuclei execution failed: {result.stderr}")

        # Nuclei outputs one JSON object per line
        findings: List[Dict] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                findings.append(obj)
            except json.JSONDecodeError:
                logger.warning("Failed to parse Nuclei output line as JSON: %s", line)
                continue
        logger.info("Nuclei returned %d findings.", len(findings))
        return findings
