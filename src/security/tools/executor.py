#!/usr/bin/env python3
"""
Pentest Executor - Executes real pentest tools and captures outputs for PoC generation
Ported from NeuroSploit for Ouroboros Red Agent.
"""

import subprocess
import shutil
import json
import re
import os
import logging
import socket
import urllib.parse
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import asdict

from src.security.models import Vulnerability, ScanResult
from src.security.tools.runner import SandboxRunner

# Assuming 'context_builder' is not directly imported here but data is passed in

logger = logging.getLogger(__name__)

class PentestExecutor:
    """Executes real pentest tools and captures outputs"""

    def __init__(self, target: str, config: Dict = None, recon_context: Dict = None):
        self.target = self._normalize_target(target)
        self.config = config or {}
        self.recon_context = recon_context
        self.scan_result = ScanResult(
            target=self.target,
            scan_started=datetime.now().isoformat()
        )
        self.timeout = 300  # 5 minutes default timeout

        if self.recon_context:
            self._load_from_recon_context()

    def setup_sandbox(self, repo_url: str) -> str:
        """
        Clones compliance-ready sandbox for white-box testing.
        Returns absolute path to sandbox.
        """
        sandbox_base = "/tmp/ouroboros_sandbox"
        # Use simple ID if scan result doesn't help make it unique enough
        scan_id = self.scan_result.scan_started.replace(":", "-").replace(".", "-")
        sandbox_path = os.path.join(sandbox_base, scan_id)
        
        if os.path.exists(sandbox_path):
            shutil.rmtree(sandbox_path)
            
        try:
            logger.info(f"Cloning {repo_url} to sandbox: {sandbox_path}")
            # Use subprocess to avoid gitpython dependency if possible, or assume git is installed
            subprocess.run(["git", "clone", "--depth", "1", repo_url, sandbox_path], 
                         check=True, capture_output=True, timeout=120)
            return sandbox_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Clone failed: {e.stderr}")
            if os.path.exists(sandbox_path):
                shutil.rmtree(sandbox_path) # Cleanup on fail
            return ""
        except Exception as e:
            logger.error(f"Sandbox setup failed: {e}")
            return ""

    def run_dynamic_analysis(self, repo_url: str) -> Dict:
        """
        Orchestrates a comprehensive Dynamic Application Security Testing (DAST) workflow.
        1. Clones the repository.
        2. Starts the application in a sandbox.
        3. Runs DAST tools (Nmap, Nuclei) against the running instance.
        4. (Optional) SAST scan on the source code.
        5. Teardowns the sandbox.
        """
        self.logger = logger # Ensure logger is available
        logger.info(f"Starting Dynamic Analysis for {repo_url}")
        
        # 1. Clone
        sandbox_path = self.setup_sandbox(repo_url)
        if not sandbox_path:
            return {"success": False, "error": "Failed to clone repository"}

        runner = SandboxRunner(sandbox_path)
        success, app_url = runner.start()
        
        if not success:
            logger.error(f"Failed to start sandbox app: {app_url}")
            # Even if it failed to start, we can still do SAST
            self.run_static_analysis(sandbox_path)
            return {"success": False, "error": f"Failed to start app: {app_url}"}

        logger.info(f"Sandbox application running at {app_url}")
        
        # Update target to local instance for DAST
        original_target = self.target
        self.target = app_url
        
        try:
            # 2. Run DAST tools
            self.run_full_scan() # Nmap, Nuclei
            
            # 3. Run SAST tools (on the source code)
            self.run_static_analysis(sandbox_path)
            
        finally:
            logger.info("Stopping sandbox...")
            runner.stop()
            self.target = original_target # Restore original target
            
        return {"success": True, "scan_result": self.scan_result}

    def run_static_analysis(self, target_path: str):
        """Run all SAST/SCA/Secret tools"""
        logger.info("Running Static Analysis...")
        self.run_semgrep_scan(target_path)
        self.run_gitleaks_scan(target_path)
        self.run_trivy_scan(target_path)
        self.run_checkov_scan(target_path)

    def run_semgrep_scan(self, target_path: str) -> Dict:
        """Run Semgrep SAST scan on sandbox"""
        if not target_path or not os.path.exists(target_path):
            return {"success": False, "stderr": "Invalid target path"}
            
        # Using built-in rules for now + basic security
        cmd = ["semgrep", "--config", "p/security-audit", "--json", target_path]
        
        result = self._run_command(cmd, timeout=600)
        
        if result["success"] and result["stdout"]:
            self._parse_semgrep_output(result["stdout"], target_path)
            
        return result

    def _parse_semgrep_output(self, output: str, base_path: str):
        """Parse Semgrep JSON output"""
        try:
            data = json.loads(output)
            results = data.get("results", [])
            for res in results:
                path = res.get("path", "").replace(base_path + "/", "")
                severity = res.get("extra", {}).get("severity", "medium").capitalize()
                
                vuln = Vulnerability(
                    title=f"Code: {res.get('check_id', 'Unknown Issue')}",
                    severity=severity,
                    cvss_score=0.0, # Semgrep logic needed
                    cvss_vector="",
                    description=res.get("extra", {}).get("message", ""),
                    affected_endpoint=f"{path}:{res.get('start', {}).get('line', 0)}",
                    impact=f"Potential insecure code pattern in {path}",
                    poc_request="N/A (Static Analysis)",
                    poc_response=f"Found in: {res.get('extra', {}).get('lines', '')}",
                    poc_payload="N/A",
                    remediation="Review code and apply secure patterns",
                    references=res.get("extra", {}).get("metadata", {}).get("references", []),
                    cwe_id=res.get("extra", {}).get("metadata", {}).get("cwe", ["Unknown"])[0],
                    tool_output=json.dumps(res, indent=2)
                )
                self.scan_result.vulnerabilities.append(vuln)
        except json.JSONDecodeError:
            logger.error("Failed to parse Semgrep JSON")

    def run_gitleaks_scan(self, target_path: str) -> Dict:
        """Run Gitleaks scan for secrets"""
        if not shutil.which("gitleaks"):
             logger.warning("Gitleaks not installed.")
             return {}
             
        cmd = ["gitleaks", "detect", "--source", target_path, "--report-format", "json", "--report-path", "/dev/stdout", "--no-git"]
        result = self._run_command(cmd)
        
        if result["success"] and result["stdout"]:
             try:
                 findings = json.loads(result["stdout"])
                 for finding in findings:
                     vuln = Vulnerability(
                         title=f"Secret: {finding.get('Description', 'Potential Secret')}",
                         severity="High",
                         cvss_score=7.5,
                         description=f"Found potential secret in {finding.get('File')}",
                         affected_endpoint=f"{finding.get('File')}:{finding.get('StartLine')}",
                         impact="Credentials exposure could lead to unauthorized access",
                         poc_response=f"Match: {finding.get('Match')}",
                         remediation="Rotate secret and remove from history",
                         tool_output=json.dumps(finding, indent=2)
                     )
                     self.scan_result.vulnerabilities.append(vuln)
             except json.JSONDecodeError:
                 pass
        return result

    def run_trivy_scan(self, target_path: str) -> Dict:
        """Run Trivy scan for dependencies (fs mode)"""
        if not shutil.which("trivy"):
             logger.warning("Trivy not installed.")
             return {}
        
        # Scans filesystem for vulnerabilities in deps
        cmd = ["trivy", "fs", target_path, "--format", "json", "--scanners", "vuln,config", "--quiet"]
        result = self._run_command(cmd)
        
        if result["success"] and result["stdout"]:
             try:
                 data = json.loads(result["stdout"])
                 for res in data.get("Results", []):
                     target = res.get("Target", "Unknown")
                     for finding in res.get("Vulnerabilities", []):
                         vuln = Vulnerability(
                             title=f"Dependency: {finding.get('PkgName')} {finding.get('VulnerabilityID')}",
                             severity=finding.get("Severity", "Medium").capitalize(),
                             cvss_score=0.0,
                             description=finding.get("Description", ""),
                             affected_endpoint=f"{target} ({finding.get('PkgName')})",
                             impact="Vulnerable dependency component",
                             remediation=f"Upgrade to {finding.get('FixedVersion', 'latest')}",
                             references=finding.get("References", []),
                             tool_output=json.dumps(finding, indent=2)
                         )
                         self.scan_result.vulnerabilities.append(vuln)
                     
                     for finding in res.get("Misconfigurations", []):
                          vuln = Vulnerability(
                             title=f"Config: {finding.get('Title')}",
                             severity=finding.get("Severity", "Medium").capitalize(),
                             cvss_score=0.0,
                             description=finding.get("Description", ""),
                             affected_endpoint=f"{target}",
                             impact="Misconfiguration vulnerability",
                             remediation=finding.get("Resolution", ""),
                             tool_output=json.dumps(finding, indent=2)
                         )
                          self.scan_result.vulnerabilities.append(vuln)
             except json.JSONDecodeError:
                 pass
        return result

    def run_checkov_scan(self, target_path: str) -> Dict:
        """Run Checkov scan for IaC"""
        # Checkov is python pkg, might be runnable via python -m checkov or checkov bin
        cmd = ["checkov", "-d", target_path, "--output", "json", "--quiet"]
        
        # Might take longer
        result = self._run_command(cmd, timeout=300)
        
        if result["success"] and result["stdout"]:
             try:
                 # Checkov output structure varies if multiple checks
                 # Sometimes it returns a list of reports or a single obj
                 data = json.loads(result["stdout"])
                 
                 reports = data if isinstance(data, list) else [data]
                 
                 for report in reports:
                     check_type = report.get("check_type", "IaC")
                     for check in report.get("results", {}).get("failed_checks", []):
                         vuln = Vulnerability(
                             title=f"IaC ({check_type}): {check.get('check_id')} - {check.get('check_name')}",
                             severity="Medium", # Checkov doesn't always map standardized severity well
                             cvss_score=0.0,
                             description=check.get("check_name", ""),
                             affected_endpoint=check.get("file_path", ""),
                             impact="Infrastructure as Code misconfiguration",
                             remediation=check.get("guideline", ""),
                             tool_output=json.dumps(check, indent=2)
                         )
                         self.scan_result.vulnerabilities.append(vuln)
             except json.JSONDecodeError:
                 pass
        return result

    def _load_from_recon_context(self):
        """Loads data from the consolidated recon context."""
        if not self.recon_context:
            return

        data = self.recon_context.get('data', {})

        # Load technologies
        techs = data.get('technologies', [])
        self.scan_result.technologies.extend(techs)

        # Load open ports
        ports = data.get('open_ports', [])
        for port in ports:
            if port not in self.scan_result.open_ports:
                self.scan_result.open_ports.append(port)

        # Load existing vulns from context if any
        vulns = self.recon_context.get('vulnerabilities', {}).get('all', [])
        for v in vulns:
            vuln = Vulnerability(
                title=v.get('title', v.get('name', 'Unknown')),
                severity=v.get('severity', 'Info').capitalize(),
                cvss_score=0.0, # Placeholder
                cvss_vector="",
                description=v.get('description', ''),
                affected_endpoint=v.get('affected_endpoint', v.get('url', self.target)),
                impact=f"{v.get('severity', 'info')} severity finding",
                poc_request="",
                poc_response="",
                poc_payload="",
                remediation="Detailed in full report"
            )
            self.scan_result.vulnerabilities.append(vuln)

    def _normalize_target(self, target: str) -> str:
        """Normalize target URL/IP"""
        target = target.strip()
        if not target.startswith(('http://', 'https://')):
            try:
                socket.inet_aton(target.split('/')[0].split(':')[0])
                return target  # It's an IP
            except socket.error:
                return f"https://{target}"
        return target

    def _get_domain(self) -> str:
        """Extract domain from target"""
        parsed = urllib.parse.urlparse(self.target)
        return parsed.netloc or parsed.path.split('/')[0]

    def _run_command(self, cmd: List[str], timeout: int = None) -> Dict:
        """Run a command and capture output"""
        timeout = timeout or self.timeout
        tool_name = cmd[0] if cmd else "unknown"

        result = {
            "tool": tool_name,
            "command": " ".join(cmd),
            "success": False,
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "timestamp": datetime.now().isoformat()
        }

        # If it's python module (checkov), shutil.which might find it in path if activated
        # Otherwise for subprocess calls to system binaries
        if not shutil.which(cmd[0]):
             # Fallback check - maybe it's in a standard path not in env?
             pass

        try:
            logger.info(f"Executing: {' '.join(cmd)}")
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            result["stdout"] = proc.stdout
            result["stderr"] = proc.stderr
            result["exit_code"] = proc.returncode
            result["success"] = proc.returncode == 0

        except subprocess.TimeoutExpired:
            result["stderr"] = f"Command timed out after {timeout} seconds"
        except Exception as e:
            result["stderr"] = str(e)
            logger.error(f"Error executing {cmd[0]}: {e}")

        self.scan_result.tools_executed.append(result)
        self.scan_result.raw_outputs[tool_name] = result["stdout"]
        return result

    def run_nmap_scan(self, ports: str = "1-1000", extra_args: List[str] = None) -> Dict:
        """Run nmap port scan"""
        domain = self._get_domain()
        # Ensure we only scan domain/IP, not full URL
        target_host = domain.split(':')[0]
        
        cmd = ["nmap", "-sV", "-p", ports, "--open", target_host]
        if extra_args:
            cmd.extend(extra_args)

        result = self._run_command(cmd)

        if result["success"]:
            self._parse_nmap_output(result["stdout"])

        return result

    def _parse_nmap_output(self, output: str):
        """Parse nmap output for open ports"""
        port_pattern = r"(\d+)/(\w+)\s+open\s+(\S+)\s*(.*)"
        for match in re.finditer(port_pattern, output):
            port_info = {
                "port": int(match.group(1)),
                "protocol": match.group(2),
                "service": match.group(3),
                "version": match.group(4).strip()
            }
            self.scan_result.open_ports.append(port_info)
            logger.info(f"Found open port: {port_info}")

    def run_nuclei_scan(self, templates: str = None) -> Dict:
        """Run nuclei vulnerability scan"""
        cmd = ["nuclei", "-u", self.target, "-silent", "-nc", "-j"]
        if templates:
            cmd.extend(["-t", templates])

        result = self._run_command(cmd, timeout=600)

        if result["stdout"]:
            self._parse_nuclei_output(result["stdout"])

        return result

    def _parse_nuclei_output(self, output: str):
        """Parse nuclei JSON output for vulnerabilities"""
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
            try:
                finding = json.loads(line)
                severity = finding.get("info", {}).get("severity", "unknown").capitalize()

                vuln = Vulnerability(
                    title=finding.get("info", {}).get("name", "Unknown"),
                    severity=severity,
                    cvss_score=0.0, # Nuclei usually gives string severity
                    cvss_vector=finding.get("info", {}).get("classification", {}).get("cvss-metrics", ""),
                    description=finding.get("info", {}).get("description", ""),
                    affected_endpoint=finding.get("matched-at", self.target),
                    impact=finding.get("info", {}).get("impact", f"{severity} severity vulnerability"),
                    poc_request=finding.get("curl-command", f"curl -X GET '{finding.get('matched-at', self.target)}'"),
                    poc_response=finding.get("response", "")[:500] if finding.get("response") else "See tool output",
                    poc_payload=finding.get("matcher-name", "Template-based detection"),
                    remediation=finding.get("info", {}).get("remediation", "Apply vendor patches"),
                    references=finding.get("info", {}).get("reference", []),
                    cwe_id=str(finding.get("info", {}).get("classification", {}).get("cwe-id", "")),
                    tool_output=json.dumps(finding, indent=2)
                )
                self.scan_result.vulnerabilities.append(vuln)

            except json.JSONDecodeError:
                continue

    def run_full_scan(self) -> ScanResult:
        """Run nmap and nuclei"""
        self.run_nmap_scan()
        self.run_nuclei_scan()
        self.scan_result.scan_completed = datetime.now().isoformat()
        return self.scan_result

    def to_dict(self) -> Dict:
        """Convert scan results to dictionary"""
        return self.scan_result.to_dict()
