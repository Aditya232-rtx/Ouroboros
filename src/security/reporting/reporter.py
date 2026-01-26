#!/usr/bin/env python3
"""
Professional Pentest Report Generator
Generates detailed reports with PoCs, CVSS scores, requests/responses
Ported from NeuroSploit.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
import html
import logging

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generates professional penetration testing reports"""

    def __init__(self, scan_results: Dict, llm_analysis: str = ""):
        self.scan_results = scan_results
        self.llm_analysis = llm_analysis
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _get_severity_color(self, severity: str) -> str:
        colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#17a2b8",
            "info": "#6c757d"
        }
        return colors.get(severity.lower(), "#6c757d")

    def _get_severity_badge(self, severity: str) -> str:
        color = self._get_severity_color(severity)
        return f'<span class="badge" style="background-color: {color}; color: white; padding: 5px 10px; border-radius: 4px;">{severity.upper()}</span>'

    def _escape_html(self, text: str) -> str:
        if not text:
            return ""
        return html.escape(str(text))

    def _format_code_block(self, code: str, language: str = "") -> str:
        escaped = self._escape_html(code)
        return f'<pre><code class="language-{language}">{escaped}</code></pre>'

    def generate_html_report(self) -> str:
        """Generate complete HTML report"""
        vulnerabilities = self.scan_results.get("vulnerabilities", [])
        
        # HTML Template (Shortened for brevity but operational)
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Ouroboros Security Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <style>
        body {{ background-color: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', system-ui; }}
        .report-header {{ text-align: center; padding: 40px 0; border-bottom: 2px solid #00ff00; margin-bottom: 30px; }}
        .card {{ background-color: #161b22; border: 1px solid #30363d; margin-bottom: 20px; }}
        .card-header {{ background-color: rgba(0, 255, 0, 0.1); color: #00ff00; }}
        .vulnerability-card {{ background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; margin-bottom: 25px; }}
        .vuln-header {{ padding: 20px; background-color: rgba(0,0,0,0.3); border-left: 5px solid #6c757d; }}
        .vuln-body {{ padding: 20px; }}
        pre {{ background-color: #1e1e1e; padding: 15px; border-radius: 6px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="report-header">
            <h1>Ouroboros Red Agent</h1>
            <p>Security Assessment Report</p>
            <p class="text-muted">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="card">
            <div class="card-header"><h2>Executive Summary</h2></div>
            <div class="card-body">
                <p><strong>Target:</strong> {self._escape_html(self.scan_results.get('target', 'N/A'))}</p>
                <p><strong>Total Vulnerabilities:</strong> {len(vulnerabilities)}</p>
            </div>
        </div>

        <div class="card">
             <div class="card-header"><h2>Vulnerabilities</h2></div>
             <div class="card-body">
        """

        for idx, vuln in enumerate(vulnerabilities):
            severity = vuln.get('severity', 'Info')
            color = self._get_severity_color(severity)
            
            html_template += f"""
            <div class="vulnerability-card">
                <div class="vuln-header" style="border-left-color: {color}">
                    <h3>{self._escape_html(vuln.get('title'))}</h3>
                    {self._get_severity_badge(severity)}
                </div>
                <div class="vuln-body">
                    <p>{self._escape_html(vuln.get('description'))}</p>
                    <h5>Endpoint</h5>
                    <code>{self._escape_html(vuln.get('affected_endpoint'))}</code>
                    <br><br>
                    {f'<h5>PoC</h5>{self._format_code_block(vuln.get("poc_request", ""), "http")}' if vuln.get("poc_request") else ""}
                </div>
            </div>
            """

        html_template += """
             </div>
        </div>
    </div>
</body>
</html>
        """
        return html_template

    def save_report(self, output_dir: str = "reports") -> str:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"ouroboros_report_{self.timestamp}.html"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate_html_report())
            
        return filepath
