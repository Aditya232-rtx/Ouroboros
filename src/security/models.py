from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import json

@dataclass
class Vulnerability:
    """Represents a discovered vulnerability with PoC"""
    title: str
    severity: str  # Critical, High, Medium, Low, Info
    cvss_score: float
    cvss_vector: str
    description: str
    affected_endpoint: str
    impact: str
    poc_request: str
    poc_response: str
    poc_payload: str
    remediation: str
    references: List[str] = field(default_factory=list)
    cwe_id: str = ""
    tool_output: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return {
            "title": self.title,
            "severity": self.severity,
            "cvss_score": self.cvss_score,
            "cvss_vector": self.cvss_vector,
            "description": self.description,
            "affected_endpoint": self.affected_endpoint,
            "impact": self.impact,
            "poc_request": self.poc_request,
            "poc_response": self.poc_response,
            "poc_payload": self.poc_payload,
            "remediation": self.remediation,
            "references": self.references,
            "cwe_id": self.cwe_id,
            "tool_output": self.tool_output,
            "timestamp": self.timestamp
        }

@dataclass
class ScanResult:
    """Contains all scan results and findings"""
    target: str
    scan_started: str
    scan_completed: str = ""
    tools_executed: List[Dict] = field(default_factory=list)
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    open_ports: List[Dict] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    raw_outputs: Dict[str, str] = field(default_factory=dict)
    summary: Dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "target": self.target,
            "scan_started": self.scan_started,
            "scan_completed": self.scan_completed,
            "tools_executed": self.tools_executed,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "open_ports": self.open_ports,
            "technologies": self.technologies,
            "summary": self.summary
        }
