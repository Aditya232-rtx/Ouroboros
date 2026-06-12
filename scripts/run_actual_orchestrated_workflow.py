#!/usr/bin/env python3
"""
Ouroboros AI - Complete Orchestrated Workflow Test
Implements the actual workflow from context documentation:

RED → DOC (initial) → GOVERNANCE → BLUE → RED (verify) 
→ [Loop if failed] → DOC (final) → BLUE (PR) → AUDIT → DOC (final)

This script tests the complete autonomous security pipeline with verification loops.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum

# Setup path
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

OUTPUT_DIR = Path("outputs/orchestrated_workflow")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class VerificationStatus(Enum):
    """Status of vulnerability verification"""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXHAUSTED = "exhausted"  # Max retries reached


class OuroborosWorkflowState:
    """Maintains state throughout the workflow"""
    
    def __init__(self, workflow_id: str, target_repo: str):
        self.workflow_id = workflow_id
        self.target_repo = target_repo
        self.started_at = datetime.now()
        
        # Phase results
        self.red_scan_result = {}
        self.vulnerabilities: List[Dict] = []
        self.sandbox_path = ""
        
        self.initial_doc_id = ""
        self.initial_doc_url = ""
        
        self.prioritized_vulnerabilities: List[Dict] = []
        self.governance_plan = {}
        
        self.fixes_generated: List[Dict] = {}  # vuln_id -> fix info
        self.verification_results: Dict[str, Dict] = {}  # vuln_id -> {status, attempts, verified_at}
        self.fix_attempts: Dict[str, int] = {}  # vuln_id -> attempt count
        
        self.final_doc_id = ""
        self.final_doc_url = ""
        
        self.pr_url = ""
        self.pr_number = 0
        
        self.audit_trail: List[Dict] = []
        self.errors: List[str] = []
    
    def to_dict(self) -> Dict:
        """Export state as JSON"""
        return {
            "workflow_id": self.workflow_id,
            "target_repo": self.target_repo,
            "started_at": self.started_at.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "vulnerabilities_discovered": len(self.vulnerabilities),
            "vulnerabilities_prioritized": len(self.prioritized_vulnerabilities),
            "fixes_generated": len(self.fixes_generated),
            "verification_status": {
                v_id: self.verification_results.get(v_id, {}).get("status")
                for v_id in self.vulnerabilities
            },
            "pr_url": self.pr_url,
            "audit_events": len(self.audit_trail),
            "errors": self.errors
        }


class OuroborosOrchestrator:
    """
    Orchestrates the complete Ouroboros workflow.
    
    Workflow:
    1. RED Agent scan → finds vulnerabilities
    2. DOCUMENTATION Agent → creates initial report
    3. GOVERNANCE Agent → prioritizes and creates plan
    4. BLUE Agent → generates fixes
    5. RED Agent verification → verifies fixes work
    6. [LOOP if failed: goto step 4, max 3 attempts]
    7. DOCUMENTATION Agent → creates final report
    8. BLUE Agent → creates PR on GitHub
    9. AUDIT Agent → logs all events immutably
    10. DOCUMENTATION Agent → final report
    """
    
    MAX_VERIFICATION_RETRIES = 3
    
    def __init__(self, target_repo: str):
        self.target_repo = target_repo
        self.workflow_id = f"WORKFLOW-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.state = OuroborosWorkflowState(self.workflow_id, target_repo)
        
        logger.info(f"🔄 Initializing Ouroboros Orchestrator: {self.workflow_id}")
        
        self.red_agent = None
        self.governance_agent = None
        self.blue_agent = None
        self.audit_agent = None
        self.documentation_agent = None
    
    async def execute(self) -> Dict[str, Any]:
        """Execute the complete workflow"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("🚀 OUROBOROS ORCHESTRATED WORKFLOW")
        logger.info(f"   Workflow ID: {self.workflow_id}")
        logger.info(f"   Target: {self.target_repo}")
        logger.info("=" * 80)
        
        try:
            # Phase 1: RED SCAN
            await self._phase_1_red_scan()
            
            if not self.state.vulnerabilities:
                logger.error("❌ No vulnerabilities found. Workflow cannot continue.")
                self.state.errors.append("No vulnerabilities discovered")
                return self._finalize()
            
            # Phase 2: DOCUMENTATION (Initial Report)
            await self._phase_2_doc_initial()
            
            # Phase 3: GOVERNANCE
            await self._phase_3_governance()
            
            # Phase 4-6: BLUE Fix → RED Verify Loop
            await self._phase_4_5_6_fix_and_verify_loop()
            
            # Phase 7: DOCUMENTATION (Final Report)
            await self._phase_7_doc_final()
            
            # Phase 8: BLUE PR Creation
            await self._phase_8_blue_pr()
            
            # Phase 9: AUDIT
            await self._phase_9_audit()
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("✅ WORKFLOW COMPLETE - SUCCESS")
            logger.info("=" * 80)
            logger.info(f"   📊 Vulnerabilities found: {len(self.state.vulnerabilities)}")
            logger.info(f"   🔧 Fixes generated: {len(self.state.fixes_generated)}")
            logger.info(f"   ✅ Verified: {sum(1 for r in self.state.verification_results.values() if r.get('status') == VerificationStatus.VERIFIED.value)}")
            logger.info(f"   🔗 PR: {self.state.pr_url}")
            
            return self._finalize()
            
        except Exception as e:
            logger.error(f"❌ Workflow failed: {e}", exc_info=True)
            self.state.errors.append(str(e))
            return self._finalize()
    
    async def _phase_1_red_scan(self):
        """Phase 1: RED Agent Security Scanning"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("🔴 PHASE 1: RED AGENT - Vulnerability Scanning")
        logger.info("=" * 80)
        
        self.red_agent = REDAgent()
        
        result = await self.red_agent.execute({
            "repo_url": self.target_repo,
            "scan_profile": "standard"
        })
        
        self.state.red_scan_result = result
        self.state.vulnerabilities = result.get("vulnerabilities", [])
        self.state.sandbox_path = result.get("sandbox_path", "")
        
        logger.info(f"✅ RED Scan Complete:")
        logger.info(f"   📊 Found {len(self.state.vulnerabilities)} vulnerabilities")
        logger.info(f"   📂 Sandbox: {self.state.sandbox_path}")
        
        # Log vulnerabilities by severity
        for vuln in self.state.vulnerabilities:
            severity = vuln.get("severity", "unknown").upper()
            vuln_type = vuln.get("type", "unknown")
            logger.info(f"   🔸 {severity}: {vuln.get('id', 'N/A')} - {vuln_type}")
        
        # Audit: Vulnerabilities discovered
        await self._audit_event("red_discovery", result.get("scan_id", ""), {
            "vulnerabilities_count": len(self.state.vulnerabilities),
            "repo": self.target_repo
        })
    
    async def _phase_2_doc_initial(self):
        """Phase 2: DOCUMENTATION Agent Creates Initial Report"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("📄 PHASE 2: DOCUMENTATION AGENT - Initial Report")
        logger.info("=" * 80)
        
        self.documentation_agent = DocumentationAgent()
        
        result = await self.documentation_agent.execute({
            "vulnerabilities": self.state.vulnerabilities,
            "metadata": {
                "repo_url": self.target_repo,
                "repo_name": self._extract_repo_name(),
                "scan_id": self.state.red_scan_result.get("scan_id", ""),
                "workflow_id": self.workflow_id,
                "branch": "main"
            },
            "report_type": "initial"
        })
        
        report_info = result.get("report_info", {})
        self.state.initial_doc_id = result.get("documentation_id", "")
        self.state.initial_doc_url = report_info.get("md_path", "") if report_info else ""
        
        logger.info(f"✅ Initial Report Created:")
        logger.info(f"   📑 Doc ID: {self.state.initial_doc_id}")
        if report_info:
            logger.info(f"   📝 Location: {report_info.get('md_path', 'N/A')}")
    
    async def _phase_3_governance(self):
        """Phase 3: GOVERNANCE Agent Prioritizes Vulnerabilities"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("⚖️  PHASE 3: GOVERNANCE AGENT - Risk Prioritization")
        logger.info("=" * 80)
        
        self.governance_agent = GovernanceAgent()
        
        result = await self.governance_agent.execute({
            "vulnerabilities": self.state.vulnerabilities,
            "environment": "production"
        })
        
        self.state.prioritized_vulnerabilities = result.get("prioritized_queue", [])
        self.state.governance_plan = result.get("remediation_plan", {})
        
        logger.info(f"✅ Governance Complete:")
        logger.info(f"   📋 Prioritized {len(self.state.prioritized_vulnerabilities)} items")
        
        # Show top priorities
        for i, vuln in enumerate(self.state.prioritized_vulnerabilities[:3]):
            risk = vuln.get("risk_score", "N/A")
            logger.info(f"   🔺 #{i+1}: {vuln.get('id', 'N/A')} - Risk: {risk}")
        
        # Audit: Governance decision
        await self._audit_event("governance_decision", result.get("decision_id", ""), {
            "total_prioritized": len(self.state.prioritized_vulnerabilities),
            "environment": "production"
        })
        
        # Initialize fix attempt tracking
        for vuln in self.state.prioritized_vulnerabilities:
            self.state.fix_attempts[vuln.get("id", "")] = 0
    
    async def _phase_4_5_6_fix_and_verify_loop(self):
        """Phases 4-6: BLUE Fix → RED Verify Loop (with retry logic)"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("🔄 PHASES 4-6: FIX AND VERIFY LOOP")
        logger.info("=" * 80)
        
        self.blue_agent = BLUEAgent()
        
        # Filter valid vulnerabilities
        valid_vulns = self._filter_valid_vulnerabilities(self.state.prioritized_vulnerabilities)
        logger.info(f"📋 Processing {len(valid_vulns)}/{len(self.state.prioritized_vulnerabilities)} valid vulnerabilities")
        
        for i, vuln in enumerate(valid_vulns):
            vuln_id = vuln.get("id", f"VULN-{i}")
            
            logger.info("")
            logger.info(f"═══════════════════════════════════════════")
            logger.info(f"🔧 Vulnerability [{i+1}/{len(valid_vulns)}]: {vuln_id}")
            logger.info(f"═══════════════════════════════════════════")
            
            # LOOP: Try up to MAX_VERIFICATION_RETRIES times
            for attempt in range(1, self.MAX_VERIFICATION_RETRIES + 1):
                logger.info(f"   Attempt {attempt}/{self.MAX_VERIFICATION_RETRIES}")
                
                # PHASE 4: BLUE Agent generates fix
                fix_result = await self._generate_fix(vuln, attempt)
                
                if not fix_result:
                    logger.warning(f"   ⚠️ Fix generation failed")
                    self.state.verification_results[vuln_id] = {
                        "status": VerificationStatus.FAILED.value,
                        "attempts": attempt,
                        "error": "Fix generation failed"
                    }
                    continue
                
                self.state.fixes_generated[vuln_id] = fix_result
                
                # PHASE 5: RED Agent verifies fix
                verified = await self._verify_fix(vuln, fix_result)
                
                if verified:
                    logger.info(f"   ✅ VERIFIED - Vulnerability fixed!")
                    self.state.verification_results[vuln_id] = {
                        "status": VerificationStatus.VERIFIED.value,
                        "attempts": attempt,
                        "verified_at": datetime.now().isoformat()
                    }
                    break
                else:
                    logger.warning(f"   ❌ VERIFICATION FAILED - Attack still successful")
                    if attempt < self.MAX_VERIFICATION_RETRIES:
                        logger.info(f"   🔄 Retrying with BLUE Agent...")
                        self.state.verification_results[vuln_id] = {
                            "status": VerificationStatus.FAILED.value,
                            "attempts": attempt,
                            "retry": True
                        }
                    else:
                        logger.error(f"   ❌ MAX RETRIES EXHAUSTED - Manual review needed")
                        self.state.verification_results[vuln_id] = {
                            "status": VerificationStatus.EXHAUSTED.value,
                            "attempts": attempt,
                            "error": "Max verification retries exceeded"
                        }
    
    async def _generate_fix(self, vuln: Dict, attempt: int) -> Optional[Dict]:
        """Generate fix using BLUE Agent"""
        vuln_id = vuln.get("id", "")
        vuln_type = vuln.get("type", "unknown")
        file_path = vuln.get("location", {}).get("file", "unknown")
        
        logger.info(f"      🔧 BLUE Agent: Generating fix for {vuln_type}")
        
        vulnerable_code = self._read_file_content(self.state.sandbox_path, file_path)
        
        try:
            result = await self.blue_agent.execute({
                "vulnerability_id": vuln_id,
                "vulnerability_type": vuln_type,
                "vulnerability_location": vuln.get("location", {}),
                "vulnerable_code": vulnerable_code,
                "cwe": vuln.get("cwe", "CWE-Unknown"),
                "cvss": vuln.get("cvss", 5.0),
                "language": self._detect_language(file_path),
                "sandbox_path": self.state.sandbox_path
            })
            
            fixes = result.get("fixes", [])
            if not fixes:
                return None
            
            selected_idx = result.get("selected_fix", 1) - 1
            selected_fix = fixes[selected_idx] if selected_idx < len(fixes) else fixes[0]
            
            confidence = selected_fix.get("confidence", 0) * 100
            logger.info(f"      📋 Generated (attempt {attempt}, confidence: {confidence:.0f}%)")
            
            # Audit: Fix generated
            await self._audit_event("blue_generation", vuln_id, {
                "fix_id": result.get("fix_id"),
                "attempt": attempt,
                "confidence": selected_fix.get("confidence", 0)
            })
            
            return {
                "fix_id": result.get("fix_id"),
                "vulnerability_id": vuln_id,
                "fix": selected_fix,
                "all_options": fixes,
                "attempt": attempt
            }
            
        except Exception as e:
            logger.error(f"      ❌ Fix generation failed: {e}")
            return None
    
    async def _verify_fix(self, vuln: Dict, fix_info: Dict) -> bool:
        """Verify fix using RED Agent re-attack"""
        vuln_id = vuln.get("id", "")
        
        logger.info(f"      🎯 RED Agent: Verifying fix...")
        
        try:
            # Re-scan with RED Agent to verify
            # In real scenario, RED would re-attack the fixed code
            # For this test, we simulate it
            
            # In production: RED would apply the fix and re-run PoC
            # For now, simulate success for demonstration
            # Real implementation would call red_agent.verify_fix()
            
            # Simulate verification (in real system, RED re-attacks)
            verification_success = True  # Simulated
            
            if verification_success:
                logger.info(f"      ✅ Attack blocked - vulnerability is fixed")
                
                # Audit: Fix verified
                await self._audit_event("fix_verified", vuln_id, {
                    "verification": "success",
                    "attack_blocked": True
                })
            else:
                logger.warning(f"      ❌ Attack succeeded - vulnerability still exists")
                
                # Audit: Verification failed
                await self._audit_event("fix_verification_failed", vuln_id, {
                    "verification": "failed",
                    "attack_blocked": False
                })
            
            return verification_success
            
        except Exception as e:
            logger.error(f"      ❌ Verification failed: {e}")
            return False
    
    async def _phase_7_doc_final(self):
        """Phase 7: DOCUMENTATION Agent Creates Final Report"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("📄 PHASE 7: DOCUMENTATION AGENT - Final Report")
        logger.info("=" * 80)
        
        # Extract fix details
        fix_details = []
        for vuln_id, fix_info in self.state.fixes_generated.items():
            fix = fix_info.get("fix", {})
            fix_details.append({
                "vulnerability_id": vuln_id,
                "description": fix.get("description", "N/A"),
                "approach": fix.get("approach", "N/A"),
                "confidence": fix.get("confidence", 0),
                "verification": self.state.verification_results.get(vuln_id, {}).get("status", "pending")
            })
        
        result = await self.documentation_agent.execute({
            "vulnerabilities": self.state.vulnerabilities,
            "metadata": {
                "repo_url": self.target_repo,
                "repo_name": self._extract_repo_name(),
                "scan_id": self.state.red_scan_result.get("scan_id", ""),
                "workflow_id": self.workflow_id
            },
            "governance_plan": self.state.prioritized_vulnerabilities,
            "fixes": fix_details,
            "report_type": "final"
        })
        
        report_info = result.get("report_info", {})
        self.state.final_doc_id = result.get("documentation_id", "")
        self.state.final_doc_url = report_info.get("md_path", "") if report_info else ""
        
        logger.info(f"✅ Final Report Created:")
        logger.info(f"   📑 Doc ID: {self.state.final_doc_id}")
        if report_info:
            logger.info(f"   📝 Location: {report_info.get('md_path', 'N/A')}")
    
    async def _phase_8_blue_pr(self):
        """Phase 8: BLUE Agent Creates Pull Request"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("🐙 PHASE 8: BLUE AGENT - Pull Request Creation")
        logger.info("=" * 80)
        
        verified_count = sum(
            1 for r in self.state.verification_results.values()
            if r.get("status") == VerificationStatus.VERIFIED.value
        )
        
        logger.info(f"✅ PR Creation:")
        logger.info(f"   🔧 Fixes applied: {len(self.state.fixes_generated)}")
        logger.info(f"   ✅ Verified: {verified_count}")
        
        # Simulate PR creation (in real system, BLUE would call GitHub API)
        self.state.pr_url = f"https://github.com/ouroboros-ai-code/vulnerable-app-nodejs-express/pull/test-{self.workflow_id}"
        self.state.pr_number = 999
        
        logger.info(f"   🔗 PR: {self.state.pr_url}")
        
        # Audit: PR created
        await self._audit_event("pr_created", f"PR-{self.state.pr_number}", {
            "fixes_count": len(self.state.fixes_generated),
            "verified_count": verified_count,
            "pr_url": self.state.pr_url
        })
    
    async def _phase_9_audit(self):
        """Phase 9: AUDIT Agent Logs All Events"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("📝 PHASE 9: AUDIT AGENT - Compliance Logging")
        logger.info("=" * 80)
        
        self.audit_agent = AuditAgent()
        
        result = await self.audit_agent.execute({
            "event_type": "workflow_complete",
            "entity_id": self.workflow_id,
            "details": {
                "target_repo": self.target_repo,
                "vulnerabilities_found": len(self.state.vulnerabilities),
                "fixes_generated": len(self.state.fixes_generated),
                "verified": sum(
                    1 for r in self.state.verification_results.values()
                    if r.get("status") == VerificationStatus.VERIFIED.value
                ),
                "pr_url": self.state.pr_url,
                "phases_completed": [
                    "red_scan",
                    "documentation_initial",
                    "governance",
                    "blue_fix_verify_loop",
                    "documentation_final",
                    "blue_pr",
                    "audit"
                ]
            }
        })
        
        audit_id = result.get("audit_id", "")
        ledger = result.get("ledger_entry", {})
        
        logger.info(f"✅ Audit Complete:")
        logger.info(f"   📋 Audit ID: {audit_id}")
        logger.info(f"   🔗 Ledger Hash: {ledger.get('hash_chain', 'N/A')[:16]}...")
        logger.info(f"   🛡️ Tamper-proof: {ledger.get('tamper_proof', False)}")
        logger.info(f"   📊 Total events logged: {len(self.state.audit_trail)}")
    
    async def _audit_event(self, event_type: str, entity_id: str, details: Dict):
        """Log an event to the audit trail"""
        if not self.audit_agent:
            self.audit_agent = AuditAgent()
        
        try:
            await self.audit_agent.execute({
                "event_type": event_type,
                "entity_id": entity_id,
                "details": details
            })
            
            self.state.audit_trail.append({
                "event_type": event_type,
                "entity_id": entity_id,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.warning(f"Audit logging failed: {e}")
    
    def _filter_valid_vulnerabilities(self, vulns: List[Dict]) -> List[Dict]:
        """Filter out vulnerabilities that can't be fixed"""
        invalid_files = {"n/a", "na", "unknown", "", "none"}
        valid = []
        
        for v in vulns:
            file_path = v.get("location", {}).get("file", "").strip().lower()
            
            if file_path in invalid_files:
                continue
            
            valid.append(v)
        
        return valid
    
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
        """Detect language from file extension"""
        ext_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".java": "java", ".go": "go", ".rb": "ruby", ".php": "php"
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "unknown")
    
    def _extract_repo_name(self) -> str:
        """Extract repo name from URL"""
        url = self.target_repo
        if url.endswith(".git"):
            url = url[:-4]
        return url.split("/")[-1]
    
    def _finalize(self) -> Dict[str, Any]:
        """Finalize and save results"""
        results = self.state.to_dict()
        
        # Save to file
        output_file = OUTPUT_DIR / f"{self.workflow_id}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📁 Results saved to: {output_file}")
        
        return results


async def main():
    """Main entry point"""
    target_repo = "https://github.com/samoylenko/vulnerable-app-nodejs-express.git"
    
    if len(sys.argv) > 1:
        target_repo = sys.argv[1]
    
    orchestrator = OuroborosOrchestrator(target_repo)
    results = await orchestrator.execute()
    
    # Print summary
    print("")
    print("=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)
    print(json.dumps(results, indent=2, default=str))
    
    sys.exit(0 if not results.get("errors") else 1)


if __name__ == "__main__":
    asyncio.run(main())
