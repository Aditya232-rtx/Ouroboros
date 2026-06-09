# src/tools/codeql_wrapper.py
"""CodeQL wrapper for code security scanning.

This module provides a thin Python wrapper around the `codeql` CLI.
It creates a CodeQL database for the target path (if not already present) and
runs a set of CodeQL queries, returning the results as a list of dictionaries.

The implementation assumes that the `codeql` binary is installed and available
on the system PATH. If it is not present, a clear `RuntimeError` is raised.
"""

import subprocess
import json
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class CodeQLWrapper:
    """Wrapper class for executing CodeQL scans.

    Parameters
    ----------
    language: str
        Programming language of the source code (e.g., "python").
    query_paths: Optional[List[str]]
        List of paths to CodeQL query files. If ``None``, the default CodeQL
        security queries for the language are used.
    """

    def __init__(self, language: str = "python", query_paths: Optional[List[str]] = None):
        self.language = language
        self.query_paths = query_paths
        logger.info("CodeQLWrapper initialized for language %s", self.language)

    def _ensure_database(self, target_path: str) -> Path:
        """Create a CodeQL database for ``target_path`` if it does not exist.

        Returns the path to the database directory.
        """
        target = Path(target_path).resolve()
        db_path = target / ".codeql-db"
        if db_path.is_dir():
            logger.debug("CodeQL database already exists at %s", db_path)
            return db_path

        cmd = [
            "codeql",
            "database",
            "create",
            str(db_path),
            "--language",
            self.language,
            "--source-root",
            str(target),
        ]
        logger.debug("Creating CodeQL database with command: %s", " ".join(cmd))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError as e:
            raise RuntimeError("CodeQL binary not found. Ensure it is installed and on PATH.") from e

        if result.returncode != 0:
            logger.error("CodeQL database creation failed: %s", result.stderr)
            raise RuntimeError(f"CodeQL database creation failed: {result.stderr}")
        logger.info("CodeQL database created at %s", db_path)
        return db_path

    def run_scan(self, target_path: str) -> List[Dict]:
        """Run CodeQL queries against ``target_path``.

        Returns a list of result dictionaries parsed from the JSON output.
        """
        db_path = self._ensure_database(target_path)
        # Determine queries to run
        if self.query_paths:
            queries = self.query_paths
        else:
            # Use built‑in CodeQL security queries for the language
            # This is a best‑effort default; users can customise via ``query_paths``.
            queries = [
                f"codeql/python-queries/security-extended.ql",
                f"codeql/python-queries/security.ql",
            ]

        findings: List[Dict] = []
        for query in queries:
            cmd = [
                "codeql",
                "query",
                "run",
                query,
                "--database",
                str(db_path),
                "--output",
                "-",
                "--format",
                "json",
            ]
            logger.debug("Running CodeQL query with command: %s", " ".join(cmd))
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            except FileNotFoundError as e:
                raise RuntimeError("CodeQL binary not found. Ensure it is installed and on PATH.") from e

            if result.returncode not in (0, 1):  # 0 = no results, 1 = results found
                logger.error("CodeQL query %s failed: %s", query, result.stderr)
                raise RuntimeError(f"CodeQL query failed: {result.stderr}")

            try:
                output = json.loads(result.stdout)
                # CodeQL returns a dict with a "results" key
                query_findings = output.get("results", [])
                findings.extend(query_findings)
            except json.JSONDecodeError:
                logger.warning("Failed to parse CodeQL JSON output for query %s", query)
                continue
        logger.info("CodeQL returned %d total findings", len(findings))
        return findings
