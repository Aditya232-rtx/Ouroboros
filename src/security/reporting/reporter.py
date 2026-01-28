#!/usr/bin/env python3
"""
Ouroboros AI - Professional Security Reporter
Generates clean, detailed reports in a Google Docs aesthetic.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import html
import logging

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generates detailed, clean security reports inspired by Google Docs."""

    def __init__(self, scan_results: Dict, llm_analysis: str = ""):
        self.scan_results = scan_results
        self.llm_analysis = llm_analysis
        self.context = scan_results.get("context", {})
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _get_severity_color(self, severity: str) -> str:
        colors = {
            "critical": "#d93025", # Google Red
            "high": "#e67c73",     # Light Red
            "medium": "#f9ab00",   # Google Yellow/Orange
            "low": "#1a73e8",      # Google Blue
            "info": "#70757a"      # Google Grey
        }
        return colors.get(severity.lower(), "#70757a")

    def _escape(self, text: Any) -> str:
        if text is None: return ""
        return html.escape(str(text))

    def _generate_css(self) -> str:
        return """
        :root {
            --primary: #1a73e8;
            --primary-hover: #1765cc;
            --surface: #ffffff;
            --background: #f8f9fa;
            --text-main: #202124;
            --text-secondary: #5f6368;
            --border: #dadce0;
            --shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
            --critical: #d93025;
            --high: #e67c73;
            --medium: #f9ab00;
            --low: #1a73e8;
            --info: #70757a;
            --code-bg: #282c34;
        }

        body {
            background-color: var(--background);
            color: var(--text-main);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 40px 15px;
        }

        .paper {
            background-color: var(--surface);
            max-width: 850px;
            margin: 0 auto;
            padding: 60px 80px;
            box-shadow: var(--shadow);
            border-radius: 4px;
            min-height: 100vh;
        }

        header {
            border-bottom: 2px solid var(--primary);
            margin-bottom: 40px;
            padding-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }

        .header-left h1 {
            font-size: 32px;
            color: var(--primary);
            margin: 0 0 10px 0;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .meta-item { font-size: 14px; color: var(--text-secondary); margin-bottom: 4px; }
        .meta-item strong { color: var(--text-main); font-weight: 600; }

        h2 {
            font-size: 20px;
            margin-top: 50px;
            margin-bottom: 20px;
            color: var(--text-main);
            border-bottom: 1px solid var(--border);
            padding-bottom: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        h3 { font-size: 18px; margin-top: 30px; margin-bottom: 15px; font-weight: 600; }

        .toc-container { background: #f8f9fa; padding: 25px; border-radius: 8px; margin: 30px 0; border: 1px solid var(--border); }
        .toc-container h4 { margin: 0 0 15px 0; font-size: 14px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; }
        .toc-list { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .toc-list a { color: var(--primary); text-decoration: none; font-size: 13px; font-weight: 500; }
        .toc-list a:hover { text-decoration: underline; }

        .summary-box { display: flex; gap: 20px; margin: 30px 0; }
        .stat-card { flex: 1; background: #fff; border: 1px solid var(--border); padding: 20px; border-radius: 8px; text-align: center; }
        .stat-value { font-size: 32px; font-weight: 700; color: var(--primary); display: block; }
        .stat-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }

        table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }
        th { background: #f8f9fa; text-align: left; padding: 12px 15px; border-bottom: 2px solid var(--border); font-weight: 600; color: var(--text-secondary); }
        td { padding: 12px 15px; border-bottom: 1px solid var(--border); }

        .vulnerability { margin-bottom: 40px; padding-bottom: 40px; border-bottom: 1px solid var(--border); page-break-inside: avoid; }
        .vulnerability:last-child { border-bottom: none; }

        .vuln-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
        .vuln-title { font-size: 20px; font-weight: 700; margin: 5px 0 0 0; color: var(--text-main); }
        
        .badge { padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
        .badge-critical { background: #fce8e6; color: var(--critical); }
        .badge-high { background: #fce8e6; color: var(--high); }
        .badge-medium { background: #fef7e0; color: var(--medium); }
        .badge-low { background: #e8f0fe; color: var(--low); }
        .badge-info { background: #f1f3f4; color: var(--info); }

        .metadata-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid var(--border); }
        .metadata-box dt { font-size: 11px; text-transform: uppercase; color: var(--text-secondary); font-weight: 700; margin-bottom: 3px; }
        .metadata-box dd { margin: 0; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--text-main); word-break: break-all; }

        .section-label { font-size: 12px; font-weight: 700; color: var(--text-secondary); margin: 20px 0 8px 0; display: block; text-transform: uppercase; letter-spacing: 0.5px; }
        
        pre { background: var(--code-bg); color: #abb2bf; padding: 15px; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 12px; overflow-x: auto; margin: 10px 0; }
        .tech-pill { background: #e8f0fe; color: var(--primary); padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: 500; border: 1px solid #d2e3fc; }

        footer { margin-top: 60px; padding-top: 20px; border-top: 1px solid var(--border); text-align: center; color: var(--text-secondary); font-size: 12px; }
        """

    def generate_html_report(self) -> str:
        vulns = self.scan_results.get("vulnerabilities", [])
        recon = self.context.get("data", {})
        surface = self.context.get("attack_surface", {})
        
        html_out = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Audit - {self._escape(self.scan_results.get('target'))}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>{self._generate_css()}</style>
</head>
<body>
    <div class="paper">
        <header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1>Ouroboros Security Report</h1>
                    <div class="metadata">Target: <strong>{self._escape(self.scan_results.get('target'))}</strong></div>
                    <div class="metadata">Date: {self.timestamp}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 20px; font-weight: bold; color: #1a73e8;">Ouroboros AI</div>
                    <div style="font-size: 12px; color: #70757a;">Autonomous Offensive Security</div>
                </div>
            </div>
        </header>

        <section id="summary">
            <h2>Executive Summary</h2>
            <p>This document details the security assessment findings for <strong>{self._escape(self.scan_results.get('target'))}</strong> discovered by the Ouroboros Red Agent. The assessment involved automated scanning, dependency analysis, and active LLM-based code review.</p>
            
            <div class="summary-box">
                <div class="stat-card">
                    <div class="stat-value">{len(vulns)}</div>
                    <div class="stat-label">Total Findings</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{surface.get('open_ports', 0)}</div>
                    <div class="stat-label">Open Ports</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(recon.get('technologies', []))}</div>
                    <div class="stat-label">Tech Identified</div>
                </div>
            </div>
        </section>

        <section id="recon">
            <h2>Asset Discovery & Reconnaissance</h2>
            <h3>Network Services</h3>
            <table>
                <thead>
                    <tr><th>Port</th><th>Protocol</th><th>Service</th><th>Version</th></tr>
                </thead>
                <tbody>
        """
        
        open_ports = self.scan_results.get("open_ports", []) or recon.get("open_ports", [])
        if not open_ports:
            html_out += "<tr><td colspan='4'>No open ports detected.</td></tr>"
        else:
            for p in open_ports:
                html_out += f"<tr><td>{p.get('port')}</td><td>{p.get('protocol')}</td><td>{p.get('service')}</td><td>{self._escape(p.get('version', 'Unknown'))}</td></tr>"

        html_out += f"""
                </tbody>
            </table>

            <h3>Technology Stack</h3>
            <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px;">
        """
        
        techs = recon.get("technologies", []) or self.scan_results.get("technologies", [])
        if not techs:
            html_out += "<div class='metadata'>No technologies identified.</div>"
        else:
            for tech in techs:
                html_out += f"<span style='background: #e8f0fe; color: #1967d2; padding: 5px 15px; border-radius: 4px; font-size: 13px; border: 1px solid #d2e3fc;'>{self._escape(tech)}</span>"

        html_out += """
            </div>

            <h3>Domain Infrastructure</h3>
            <p class="metadata">Detected Subdomains:</p>
            <div style="font-size: 13px; color: #5f6368; column-count: 2;">
        """
        
        subdomains = recon.get("subdomains", [])
        if not subdomains:
            html_out += "None"
        else:
            for sub in subdomains:
                html_out += f"<div>• {self._escape(sub)}</div>"

        html_out += """
            </div>
        </section>

        <section id="vulnerabilities">
            <h2>Detailed Security Findings</h2>
            
            <div class="toc-container">
                <h4>Findings Index</h4>
                <ul class="toc-list">
        """
        
        for idx, vuln in enumerate(vulns):
            v_title = vuln.get('type') or vuln.get('title') or 'Unknown'
            v_severity = (vuln.get('severity', 'info')).lower()
            html_out += f"<li><a href='#vuln-{idx}'>{idx+1}. [{v_severity.upper()}] {self._escape(v_title)}</a></li>"

        html_out += """
                </ul>
            </div>

            <div class="vulnerabilities-list">
        """

        for idx, vuln in enumerate(vulns):
            severity = (vuln.get('severity', 'info')).lower()
            badge_class = f"badge-{severity}"
            
            html_out += f"""
                <div id="vuln-{idx}" class="vulnerability">
                    <div class="vuln-header">
                        <div class="vuln-id-type">
                            <span style="font-size: 11px; font-weight: 700; color: var(--text-secondary); letter-spacing: 1px;">FINDING #{idx+1}</span>
                            <h3 class="vuln-title">{self._escape(vuln.get('type') or vuln.get('title') or 'Unknown Vulnerability')}</h3>
                        </div>
                        <span class="badge {badge_class}">{severity}</span>
                    </div>
                    
                    <div class="description">
                        <span class="section-label">Executive Summary</span>
                        {self._escape(vuln.get('description'))}
                    </div>
                    
                    <div class="metadata-grid">
                        <div class="metadata-box">
                            <dt>Resource Location</dt>
                            <dd>{self._escape(vuln.get('location', {}).get('file') or vuln.get('affected_endpoint') or 'Repository Root')}
                            {f":{vuln['location']['line']}" if isinstance(vuln.get('location'), dict) and vuln['location'].get('line') else ""}</dd>
                        </div>
                        <div class="metadata-box">
                            <dt>Detection Vector</dt>
                            <dd>{self._escape(", ".join(vuln.get('tools_detected_by', [])) or ("Automated Scan" if vuln.get('title') else "Static Analysis"))}</dd>
                        </div>
                    </div>

                    {f"<div><span class='section-label'>Business Impact</span><p style='font-size:14px; margin-top:5px;'>{self._escape(vuln.get('impact'))}</p></div>" if vuln.get("impact") else ""}
                    
                    {f"<div><span class='section-label'>Technical Proof of Concept</span>{self._format_code_block(vuln.get('poc_code') or vuln.get('poc_request'), 'javascript' if vuln.get('poc_code') else 'http')}</div>" if (vuln.get("poc_code") or vuln.get("poc_request")) else ""}
                    
                    {f"<div><span class='section-label'>Remediation Guidance</span><p style='font-size:14px; margin-top:5px;'>{self._escape(vuln.get('remediation_hint') or vuln.get('remediation'))}</p></div>" if (vuln.get("remediation_hint") or vuln.get("remediation")) else ""}
                </div>
            """

        html_out += """
            </div>
        </section>

        <footer>
            <p>© 2026 Ouroboros AI - Confidential Security Audit Report</p>
            <p>This report was autonomously generated. For technical support, contact the Ouroboros support team.</p>
        </footer>
    </div>
</body>
</html>
        """
        return html_out

    def _format_code_block(self, code: str, language: str = "") -> str:
        if not code: return ""
        escaped = self._escape(code)
        return f'<pre><code>{escaped}</code></pre>'

    def save_report(self, output_dir: str = "reports") -> str:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"ouroboros_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate_html_report())
            
        return filepath
