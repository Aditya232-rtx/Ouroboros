#!/usr/bin/env python3
"""
Ouroboros AI - Full Orchestrated Workflow Test
Tests the complete pipeline: RED -> GOVERNANCE -> BLUE -> AUDIT -> DOCUMENTATION

This script verifies the entire system works end-to-end with all 5 agents.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Setup path to import from src
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.red_agent import REDAgent
from src.agents.governance_agent import GovernanceAgent
from src.agents.blue_agent import BLUEAgent
from src.agents.audit_agent import AuditAgent
from src.agents.documentation_agent import DocumentationAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Output directory for test results
OUTPUT_DIR = Path("outputs/orchestrated_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class WorkflowOrchestrator:
    """
    Orchestrates the full Ouroboros security workflow.
    
    Pipeline:
    1. RED Agent    - Security scanning & vulnerability discovery
    2. GOVERNANCE   - Risk prioritization & remediation planning  
    3. BLUE Agent   - Secure fix generation
    4. AUDIT Agent  - Compliance logging & immutable trail
    5. DOCUMENTATION- Report generation (MD + PDF)
    """
    
    def __init__(self, target_repo: str):
        self.target_repo = target_repo
        self.workflow_id = f"WORKFLOW-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.results: Dict[str, Any] = {
            "workflow_id": self.workflow_id,
            "target": target_repo,
            "started_at": datetime.now().isoformat(),
            "phases": {}
        }
        
        # Initialize all agents
        logger.info(f"🔄 Initializing Ouroboros Workflow: {self.workflow_id}")
        self.red_agent: Optional[REDAgent] = None
        self.governance_agent: Optional[GovernanceAgent] = None
        self.blue_agent: Optional[BLUEAgent] = None
        self.audit_agent: Optional[AuditAgent] = None
        self.documentation_agent: Optional[DocumentationAgent] = None
    
    async def run(self) -> Dict[str, Any]:
        """Execute the full workflow"""
        logger.info("=" * 70)
        logger.info(f"🚀 OUROBOROS FULL WORKFLOW TEST")
        logger.info(f"   Target: {self.target_repo}")
        logger.info(f"   Workflow ID: {self.workflow_id}")
        logger.info("=" * 70)
        
        try:
            # Phase 1: RED Agent - Security Scanning
            vulnerabilities, sandbox_path = await self._phase1_red_scan()
            
            if not vulnerabilities:
                logger.error("❌ No vulnerabilities found. Workflow complete (nothing to fix).")
                self.results["status"] = "no_vulnerabilities"
                return self.results
            
            # Phase 2: GOVERNANCE - Prioritization
            prioritized_vulns = await self._phase2_governance(vulnerabilities)
            
            # Phase 3: BLUE Agent - Fix Generation
            fixes = await self._phase3_blue_fixes(prioritized_vulns, sandbox_path)
            
            # Phase 4: AUDIT Agent - Compliance Logging
            audit_trail = await self._phase4_audit(vulnerabilities, fixes)
            
            # Phase 5: DOCUMENTATION - Report Generation
            report = await self._phase5_documentation(vulnerabilities, prioritized_vulns, fixes)
            
            # Final Summary
            self.results["completed_at"] = datetime.now().isoformat()
            self.results["status"] = "success"
            self._print_summary()
            
            # Save results to file
            self._save_results()
            
            return self.results
            
        except Exception as e:
            logger.error(f"❌ Workflow failed: {e}", exc_info=True)
            self.results["status"] = "failed"
            self.results["error"] = str(e)
            return self.results
    
    async def _phase1_red_scan(self) -> tuple[List[Dict], str]:
        """Phase 1: RED Agent Security Scanning"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("🔴 PHASE 1: RED AGENT - Security Scanning")
        logger.info("=" * 70)
        
        self.red_agent = REDAgent()
        
        red_result = await self.red_agent.execute({
            "repo_url": self.target_repo,
            "scan_profile": "standard"
        })
        
        vulnerabilities = red_result.get("vulnerabilities", [])
        sandbox_path = red_result.get("sandbox_path", "")
        scan_id = red_result.get("scan_id", "")
        
        self.results["phases"]["red"] = {
            "scan_id": scan_id,
            "sandbox_path": sandbox_path,
            "vulnerabilities_found": len(vulnerabilities),
            "severity_breakdown": self._count_severities(vulnerabilities)
        }
        
        logger.info(f"✅ RED Agent Complete:")
        logger.info(f"   📊 Found {len(vulnerabilities)} vulnerabilities")
        logger.info(f"   📂 Sandbox: {sandbox_path}")
        
        # Log vulnerability breakdown
        for sev, count in self._count_severities(vulnerabilities).items():
            if count > 0:
                logger.info(f"   🔸 {sev}: {count}")
        
        # Audit this event
        await self._log_audit_event("red_discovery", scan_id, {
            "vulnerabilities_count": len(vulnerabilities),
            "scan_profile": "standard",
            "repo": self.target_repo
        })
        
        return vulnerabilities, sandbox_path
    
    async def _phase2_governance(self, vulnerabilities: List[Dict]) -> List[Dict]:
        """Phase 2: GOVERNANCE Agent - Risk Prioritization"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("⚖️ PHASE 2: GOVERNANCE AGENT - Risk Prioritization")
        logger.info("=" * 70)
        
        self.governance_agent = GovernanceAgent()
        
        gov_result = await self.governance_agent.execute({
            "vulnerabilities": vulnerabilities,
            "environment": "production"
        })
        
        prioritized = gov_result.get("prioritized_queue", [])
        decision_id = gov_result.get("decision_id", "")
        
        self.results["phases"]["governance"] = {
            "decision_id": decision_id,
            "prioritized_count": len(prioritized),
            "remediation_plan_generated": bool(gov_result.get("remediation_plan"))
        }
        
        logger.info(f"✅ GOVERNANCE Agent Complete:")
        logger.info(f"   📋 Prioritized {len(prioritized)} items")
        logger.info(f"   📑 Decision ID: {decision_id}")
        
        # Show top priorities
        for i, vuln in enumerate(prioritized[:3]):
            logger.info(f"   🔺 #{i+1}: {vuln.get('id', 'N/A')} - {vuln.get('type', 'unknown')}")
        
        # Audit this event
        await self._log_audit_event("governance_decision", decision_id, {
            "total_prioritized": len(prioritized),
            "environment": "production"
        })
        
        return prioritized
    
    async def _phase3_blue_fixes(self, prioritized_vulns: List[Dict], sandbox_path: str) -> List[Dict]:
        """Phase 3: BLUE Agent - Fix Generation"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("🔵 PHASE 3: BLUE AGENT - Fix Generation")
        logger.info("=" * 70)
        
        self.blue_agent = BLUEAgent()
        
        # Filter out invalid vulnerabilities
        valid_vulns = self._filter_valid_vulnerabilities(prioritized_vulns)
        logger.info(f"📋 Processing {len(valid_vulns)}/{len(prioritized_vulns)} valid vulnerabilities")
        
        all_fixes = []
        successful_fixes = 0
        failed_fixes = 0
        
        for i, vuln in enumerate(valid_vulns):
            vuln_id = vuln.get("id", f"VULN-{i}")
            vuln_type = vuln.get("type", "unknown")
            file_path = vuln.get("location", {}).get("file", "unknown")
            
            logger.info(f"")
            logger.info(f"   🔧 [{i+1}/{len(valid_vulns)}] Fixing: {vuln_id} ({vuln_type})")
            logger.info(f"      File: {file_path}")
            
            # Read actual file content
            vulnerable_code = self._read_file_content(sandbox_path, file_path)
            
            try:
                blue_result = await self.blue_agent.execute({
                    "vulnerability_id": vuln_id,
                    "vulnerability_type": vuln_type,
                    "vulnerability_location": vuln.get("location", {}),
                    "vulnerable_code": vulnerable_code,
                    "cwe": vuln.get("cwe", "CWE-Unknown"),
                    "cvss": vuln.get("cvss", 5.0),
                    "language": self._detect_language(file_path),
                    "sandbox_path": sandbox_path
                })
                
                fixes = blue_result.get("fixes", [])
                selected_idx = blue_result.get("selected_fix", 1) - 1
                
                if fixes:
                    selected_fix = fixes[selected_idx] if selected_idx < len(fixes) else fixes[0]
                    all_fixes.append({
                        "vulnerability_id": vuln_id,
                        "vulnerability": vuln,
                        "fix": selected_fix,
                        "all_options": fixes
                    })
                    successful_fixes += 1
                    confidence = selected_fix.get("confidence", 0) * 100
                    logger.info(f"      ✅ Fix generated (confidence: {confidence:.0f}%)")
                    
                    # Audit this event
                    await self._log_audit_event("blue_generation", vuln_id, {
                        "fix_id": blue_result.get("fix_id"),
                        "options_generated": len(fixes),
                        "confidence": selected_fix.get("confidence", 0)
                    })
                else:
                    failed_fixes += 1
                    logger.warning(f"      ⚠️ No fix generated")
                    
            except Exception as e:
                failed_fixes += 1
                logger.error(f"      ❌ Fix generation failed: {e}")
        
        self.results["phases"]["blue"] = {
            "total_processed": len(valid_vulns),
            "successful_fixes": successful_fixes,
            "failed_fixes": failed_fixes,
            "fix_rate": f"{(successful_fixes/len(valid_vulns)*100):.1f}%" if valid_vulns else "N/A"
        }
        
        logger.info(f"")
        logger.info(f"✅ BLUE Agent Complete:")
        logger.info(f"   🔧 Fixes generated: {successful_fixes}/{len(valid_vulns)}")
        logger.info(f"   📈 Success rate: {self.results['phases']['blue']['fix_rate']}")
        
        return all_fixes
    
    async def _phase4_audit(self, vulnerabilities: List[Dict], fixes: List[Dict]) -> Dict:
        """Phase 4: AUDIT Agent - Compliance Logging"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("📝 PHASE 4: AUDIT AGENT - Compliance Logging")
        logger.info("=" * 70)
        
        self.audit_agent = AuditAgent()
        
        # Log overall workflow event
        audit_result = await self.audit_agent.execute({
            "event_type": "workflow_complete",
            "entity_id": self.workflow_id,
            "details": {
                "target_repo": self.target_repo,
                "vulnerabilities_found": len(vulnerabilities),
                "fixes_generated": len(fixes),
                "phases_completed": list(self.results["phases"].keys())
            }
        })
        
        audit_id = audit_result.get("audit_id", "")
        ledger_entry = audit_result.get("ledger_entry", {})
        compliance = audit_result.get("compliance_mappings", {})
        
        self.results["phases"]["audit"] = {
            "audit_id": audit_id,
            "ledger_hash": ledger_entry.get("hash_chain", ""),
            "tamper_proof": ledger_entry.get("tamper_proof", False),
            "compliance_frameworks": list(compliance.keys()) if isinstance(compliance, dict) else []
        }
        
        logger.info(f"✅ AUDIT Agent Complete:")
        logger.info(f"   📋 Audit ID: {audit_id}")
        logger.info(f"   🔗 Ledger Hash: {ledger_entry.get('hash_chain', 'N/A')[:16]}...")
        logger.info(f"   🛡️ Tamper-proof: {ledger_entry.get('tamper_proof', False)}")
        
        return audit_result
    
    async def _phase5_documentation(self, vulnerabilities: List[Dict], 
                                     prioritized: List[Dict], fixes: List[Dict]) -> Dict:
        """Phase 5: DOCUMENTATION Agent - Report Generation"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("📄 PHASE 5: DOCUMENTATION AGENT - Report Generation")
        logger.info("=" * 70)
        
        self.documentation_agent = DocumentationAgent()
        
        # Extract fix details for report
        fix_details = []
        for fix_info in fixes:
            fix = fix_info.get("fix", {})
            fix_details.append({
                "vulnerability_id": fix_info.get("vulnerability_id"),
                "description": fix.get("description", "N/A"),
                "approach": fix.get("approach", "N/A"),
                "confidence": fix.get("confidence", 0)
            })
        
        doc_result = await self.documentation_agent.execute({
            "vulnerabilities": vulnerabilities,
            "metadata": {
                "repo_url": self.target_repo,
                "repo_name": self._extract_repo_name(),
                "scan_id": self.results["phases"].get("red", {}).get("scan_id", ""),
                "workflow_id": self.workflow_id,
                "branch": "main"
            },
            "governance_plan": prioritized,
            "fixes": fix_details,
            "report_type": "final"
        })
        
        report_info = doc_result.get("report_info", {})
        content_summary = doc_result.get("content_summary", {})
        
        self.results["phases"]["documentation"] = {
            "doc_id": doc_result.get("documentation_id", ""),
            "md_path": report_info.get("md_path", "") if report_info else "",
            "pdf_path": report_info.get("pdf_path", "") if report_info else "",
            "sections": doc_result.get("sections_generated", []),
            "pdf_generated": content_summary.get("pdf_generated", False) if content_summary else False
        }
        
        logger.info(f"✅ DOCUMENTATION Agent Complete:")
        logger.info(f"   📑 Doc ID: {doc_result.get('documentation_id', 'N/A')}")
        if report_info:
            logger.info(f"   📝 Markdown: {report_info.get('md_path', 'N/A')}")
            if report_info.get("pdf_path"):
                logger.info(f"   📄 PDF: {report_info.get('pdf_path')}")
        
        return doc_result
    
    async def _log_audit_event(self, event_type: str, entity_id: str, details: Dict):
        """Log an event to the audit trail"""
        if not self.audit_agent:
            self.audit_agent = AuditAgent()
        
        try:
            await self.audit_agent.execute({
                "event_type": event_type,
                "entity_id": entity_id,
                "details": details
            })
        except Exception as e:
            logger.warning(f"Audit logging failed for {event_type}: {e}")
    
    def _filter_valid_vulnerabilities(self, vulns: List[Dict]) -> List[Dict]:
        """Filter out vulnerabilities that can't be fixed"""
        invalid_files = {"n/a", "na", "unknown", "", "none"}
        valid = []
        
        for v in vulns:
            file_path = v.get("location", {}).get("file", "").strip().lower()
            vuln_type = v.get("type", "").lower()
            
            # Skip invalid file paths
            if file_path in invalid_files:
                continue
            
            # Skip auto-generated Dockerfile issues
            if file_path == "dockerfile" and any(x in vuln_type for x in ["healthcheck", "root_user"]):
                continue
            
            valid.append(v)
        
        return valid
    
    def _count_severities(self, vulns: List[Dict]) -> Dict[str, int]:
        """Count vulnerabilities by severity"""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for v in vulns:
            sev = v.get("severity", "medium").lower()
            if sev in counts:
                counts[sev] += 1
        return counts
    
    def _read_file_content(self, sandbox_path: str, file_path: str) -> str:
        """Read file content from sandbox"""
        if not sandbox_path or not file_path:
            return ""
        
        full_path = Path(sandbox_path) / file_path
        if full_path.exists():
            try:
                return full_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                logger.warning(f"Failed to read {full_path}: {e}")
        return ""
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".java": "java", ".go": "go", ".rb": "ruby", ".php": "php",
            ".c": "c", ".cpp": "cpp", ".cs": "csharp", ".rs": "rust"
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "unknown")
    
    def _extract_repo_name(self) -> str:
        """Extract repository name from URL"""
        url = self.target_repo
        if url.endswith(".git"):
            url = url[:-4]
        return url.split("/")[-1]
    
    def _print_summary(self):
        """Print final workflow summary"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("🎉 WORKFLOW COMPLETE - SUMMARY")
        logger.info("=" * 70)
        logger.info(f"   Workflow ID: {self.workflow_id}")
        logger.info(f"   Target: {self.target_repo}")
        logger.info("")
        
        phases = self.results.get("phases", {})
        
        # RED
        red = phases.get("red", {})
        logger.info(f"   🔴 RED:          {red.get('vulnerabilities_found', 0)} vulnerabilities found")
        
        # GOVERNANCE
        gov = phases.get("governance", {})
        logger.info(f"   ⚖️ GOVERNANCE:   {gov.get('prioritized_count', 0)} items prioritized")
        
        # BLUE
        blue = phases.get("blue", {})
        logger.info(f"   🔵 BLUE:         {blue.get('successful_fixes', 0)}/{blue.get('total_processed', 0)} fixes generated")
        
        # AUDIT
        audit = phases.get("audit", {})
        logger.info(f"   📝 AUDIT:        Logged to ledger (hash: {audit.get('ledger_hash', 'N/A')[:12]}...)")
        
        # DOCUMENTATION
        doc = phases.get("documentation", {})
        logger.info(f"   📄 DOCUMENTATION: Report generated ({doc.get('doc_id', 'N/A')})")
        
        logger.info("")
        logger.info("=" * 70)
    
    def _save_results(self):
        """Save workflow results to JSON file"""
        output_file = OUTPUT_DIR / f"{self.workflow_id}.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        logger.info(f"📁 Results saved to: {output_file}")


async def main():
    """Main entry point"""
    # Default test target
    target_repo = "https://github.com/samoylenko/vulnerable-app-nodejs-express.git"
    
    # Allow override via command line
    if len(sys.argv) > 1:
        target_repo = sys.argv[1]
    
    orchestrator = WorkflowOrchestrator(target_repo)
    results = await orchestrator.run()
    
    # Exit with appropriate code
    if results.get("status") == "success":
        logger.info("✅ All tests passed!")
        sys.exit(0)
    else:
        logger.error(f"❌ Workflow failed: {results.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
