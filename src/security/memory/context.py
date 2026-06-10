import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class SecurityContextBuilder:
    """
    Consolidates all reconnaissance data into a single context for LLM consumption.
    Ported from NeuroSploit ReconContextBuilder.
    """

    def __init__(self, output_dir: str = "results"):
        """Initialize the builder."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Collected data
        self.target_info: Dict[str, Any] = {}
        self.subdomains: Set[str] = set()
        self.live_hosts: Set[str] = set()
        self.urls: Set[str] = set()
        self.urls_with_params: Set[str] = set()
        self.open_ports: List[Dict] = []
        self.technologies: List[str] = []
        self.vulnerabilities: List[Dict] = []
        self.dns_records: List[str] = []
        self.js_files: Set[str] = set()
        self.api_endpoints: Set[str] = set()
        self.interesting_paths: Set[str] = set()
        self.secrets: List[str] = []
        self.raw_outputs: Dict[str, str] = {}
        self.tool_results: Dict[str, Dict] = {}

    def set_target(self, target: str, target_type: str = "domain"):
        """Set the primary target."""
        self.target_info = {
            "primary_target": target,
            "type": target_type,
            "timestamp": datetime.now().isoformat()
        }

        # Auto-add as in-scope
        if target_type == "domain":
            self.subdomains.add(target)
        elif target_type == "url":
            parsed = urlparse(target)
            if parsed.netloc:
                self.subdomains.add(parsed.netloc)
                self.live_hosts.add(target)

    def add_subdomains(self, subdomains: List[str]):
        """Add discovered subdomains."""
        for sub in subdomains:
            sub = sub.strip().lower()
            if sub and self._is_valid_domain(sub):
                self.subdomains.add(sub)

    def add_live_hosts(self, hosts: List[str]):
        """Add active HTTP hosts."""
        for host in hosts:
            host = host.strip()
            if host:
                self.live_hosts.add(host)

    def add_urls(self, urls: List[str]):
        """Add discovered URLs."""
        for url in urls:
            url = url.strip()
            if url and url.startswith(('http://', 'https://')):
                self.urls.add(url)
                # Separate URLs with parameters
                if '?' in url and '=' in url:
                    self.urls_with_params.add(url)

    def add_open_ports(self, ports: List[Dict]):
        """Add discovered open ports."""
        for port in ports:
            if port not in self.open_ports:
                self.open_ports.append(port)

    def add_technologies(self, techs: List[str]):
        """Add detected detected technologies."""
        for tech in techs:
            if tech and tech not in self.technologies:
                self.technologies.append(tech)

    def add_vulnerabilities(self, vulns: List[Dict]):
        """Add found vulnerabilities."""
        for vuln in vulns:
            if vuln not in self.vulnerabilities:
                self.vulnerabilities.append(vuln)

    def add_dns_records(self, records: List[str]):
        """Add DNS records."""
        for record in records:
            if record and record not in self.dns_records:
                self.dns_records.append(record)

    def add_js_files(self, js_urls: List[str]):
        """Add found JavaScript files."""
        for js in js_urls:
            if js and '.js' in js.lower():
                self.js_files.add(js)

    def add_api_endpoints(self, endpoints: List[str]):
        """Add API endpoints."""
        for ep in endpoints:
            if ep:
                self.api_endpoints.add(ep)

    def add_interesting_paths(self, paths: List[str]):
        """Add interesting paths."""
        keywords = ['admin', 'login', 'dashboard', 'api', 'config', 'backup', 
                   'debug', 'test', 'dev', 'staging', 'internal', 'upload', 
                   'console', 'panel', 'phpinfo', 'swagger', '.git', '.env']
        
        for path in paths:
            path_lower = path.lower()
            if any(kw in path_lower for kw in keywords):
                self.interesting_paths.add(path)

    def add_secrets(self, secrets: List[str]):
        """Add potential secrets found."""
        for secret in secrets:
            if secret and secret not in self.secrets:
                self.secrets.append(secret)

    def add_raw_output(self, tool_name: str, output: str):
        """Add raw output from a tool."""
        self.raw_outputs[tool_name] = output

    def add_tool_result(self, tool_name: str, result: Dict):
        """Add structured result from a tool."""
        self.tool_results[tool_name] = result

    def _is_valid_domain(self, domain: str) -> bool:
        """Check if it's a valid domain."""
        if not domain or '..' in domain or domain.startswith('.'):
            return False
        parts = domain.split('.')
        return len(parts) >= 2 and all(p for p in parts)

    def _extract_params_from_urls(self) -> Dict[str, List[str]]:
        """Extract unique parameters from URLs."""
        params = {}
        for url in self.urls_with_params:
            if '?' in url:
                query = url.split('?')[1]
                for pair in query.split('&'):
                    if '=' in pair:
                        param_name = pair.split('=')[0]
                        if param_name not in params:
                            params[param_name] = []
                        params[param_name].append(url)
        return params

    def _categorize_vulnerabilities(self) -> Dict[str, List[Dict]]:
        """Categorize vulnerabilities by severity."""
        categories = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': [],
            'info': []
        }

        for vuln in self.vulnerabilities:
            severity = vuln.get('severity', 'info').lower()
            if severity in categories:
                categories[severity].append(vuln)
        
        return categories

    def _build_attack_surface(self) -> Dict[str, Any]:
        """Build attack surface summary."""
        return {
            "total_subdomains": len(self.subdomains),
            "live_hosts": len(self.live_hosts),
            "total_urls": len(self.urls),
            "urls_with_params": len(self.urls_with_params),
            "open_ports": len(self.open_ports),
            "js_files": len(self.js_files),
            "api_endpoints": len(self.api_endpoints),
            "interesting_paths": len(self.interesting_paths),
            "technologies_detected": len(self.technologies),
            "vulnerabilities_found": len(self.vulnerabilities),
            "secrets_found": len(self.secrets)
        }

    def _build_recommendations(self) -> List[str]:
        """Generate recommendations based on findings."""
        recs = []
        
        vuln_cats = self._categorize_vulnerabilities()
        
        if vuln_cats['critical']:
            recs.append(f"CRITICAL: {len(vuln_cats['critical'])} critical vulnerabilities found - immediate action required!")
            
        if vuln_cats['high']:
            recs.append(f"HIGH: {len(vuln_cats['high'])} high severity vulnerabilities need attention.")
            
        if self.urls_with_params:
            recs.append(f"Test {len(self.urls_with_params)} URLs with parameters for SQLi, XSS, etc.")
            
        if self.api_endpoints:
            recs.append(f"Review {len(self.api_endpoints)} API endpoints for authentication/authorization issues.")
            
        if self.secrets:
            recs.append(f"SECRETS: {len(self.secrets)} potential secrets exposed - rotate credentials!")
            
        if self.interesting_paths:
            recs.append(f"Investigate {len(self.interesting_paths)} interesting paths found.")
            
        if len(self.live_hosts) > 50:
            recs.append("Large attack surface detected - consider network segmentation.")
            
        return recs

    def build(self) -> Dict[str, Any]:
        """Build the consolidated context."""
        context = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "generator": "Ouroboros Red Agent Context",
                "version": "2.0.0"
            },
            "target": self.target_info,
            "attack_surface": self._build_attack_surface(),
            "data": {
                "subdomains": sorted(list(self.subdomains)),
                "live_hosts": sorted(list(self.live_hosts)),
                "urls": {
                    "all": list(self.urls)[:500],
                    "with_params": list(self.urls_with_params),
                    "total_count": len(self.urls)
                },
                "open_ports": self.open_ports,
                "technologies": self.technologies,
                "dns_records": self.dns_records,
                "js_files": list(self.js_files),
                "api_endpoints": list(self.api_endpoints),
                "interesting_paths": list(self.interesting_paths),
                "unique_params": self._extract_params_from_urls(),
                "secrets": self.secrets[:50]
            },
            "vulnerabilities": {
                "total": len(self.vulnerabilities),
                "by_severity": self._categorize_vulnerabilities(),
                "all": self.vulnerabilities[:100]
            },
            "recommendations": self._build_recommendations(),
            "tool_results": self.tool_results
        }
        
        return context

    def build_text_context(self) -> str:
        """Build context in text format for LLM."""
        ctx = self.build()
        
        lines = [
            "=" * 80,
            "OUROBOROS RED AGENT - CONSOLIDATED CONTEXT",
            "=" * 80,
            "",
            f"Primary Target: {ctx['target'].get('primary_target', 'N/A')}",
            f"Generated at: {ctx['metadata']['generated_at']}",
            "",
            "-" * 40,
            "ATTACK SURFACE",
            "-" * 40,
        ]
        
        for key, value in ctx['attack_surface'].items():
            lines.append(f"  {key}: {value}")
            
        lines.extend([
            "",
            "-" * 40,
            "OPEN PORTS",
            "-" * 40,
        ])
        for port in ctx['data']['open_ports'][:30]:
            lines.append(f"  - {port.get('port', 'N/A')}/{port.get('protocol', 'tcp')} - {port.get('service', 'unknown')}")
            
        lines.extend([
            "",
            "-" * 40,
            "DETECTED TECHNOLOGIES",
            "-" * 40,
        ])
        for tech in ctx['data']['technologies'][:20]:
            lines.append(f"  - {tech}")
            
        lines.extend([
            "",
            "-" * 40,
            "VULNERABILITIES FOUND",
            "-" * 40,
            f"Total: {ctx['vulnerabilities']['total']}",
            ""
        ])
        
        for vuln in ctx['vulnerabilities']['all'][:30]:
            lines.append(f"  [{vuln.get('severity', 'INFO').upper()}] {vuln.get('title', 'N/A')}")
            lines.append(f"       Endpoint: {vuln.get('affected_endpoint', 'N/A')}")
            
        lines.extend([
            "",
            "=" * 80,
            "END OF CONTEXT",
            "=" * 80,
        ])
        
        return "\n".join(lines)

    def save(self, scan_id: str) -> str:
        """Save context to JSON file"""
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True)
            
        filename = self.output_dir / f"context_{scan_id}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.build(), f, indent=2, default=str)
            logger.info(f"Context saved to {filename}")
            return str(filename)
        except Exception as e:
            logger.error(f"Failed to save context: {e}")
            return ""
