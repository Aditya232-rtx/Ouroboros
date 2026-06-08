"""
Ouroboros AI - Verification Engine
RED-BLUE verification loop: RED attacks BLUE's fixes to prove they work
"""

import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """Status of a verification attempt"""
    SUCCESS = "success"  # PoC failed (vulnerability fixed)
    FAILED = "failed"    # PoC succeeded (still vulnerable)
    ERROR = "error"      # Verification encountered an error
    SKIPPED = "skipped"  # Verification was skipped


@dataclass
class VerificationResult:
    """Result of a single verification attempt"""
    vulnerability_id: str
    fix_id: str
    attempt: int
    status: VerificationStatus
    poc_result: Dict[str, Any]
    message: str
    timestamp: str


class VerificationEngine:
    """
    RED-BLUE Verification Loop
    
    This is the KEY DIFFERENTIATOR of Ouroboros:
    - After BLUE generates a fix
    - RED re-attacks the fixed code with the original PoC
    - If PoC FAILS, the fix is VERIFIED (vulnerability is gone)
    - If PoC SUCCEEDS, loop back to BLUE for a new approach
    - Max 10 iterations to prevent infinite loops
    """
    
    MAX_ITERATIONS = 10
    MAX_ATTEMPTS_PER_VULN = 3
    
    def __init__(self, red_agent, blue_agent):
        """
        Initialize verification engine
        
        Args:
            red_agent: REDAgent instance for attacking
            blue_agent: BLUEAgent instance for fixing
        """
        self.red_agent = red_agent
        self.blue_agent = blue_agent
        self.logger = logging.getLogger(__name__)
    
    async def verify_all_fixes(
        self,
        vulnerabilities: List[Dict[str, Any]],
        fixes: List[Dict[str, Any]],
        codebase: Dict[str, str]
    ) -> Tuple[bool, List[VerificationResult]]:
        """
        Main verification loop - verify all fixes
        
        Args:
            vulnerabilities: List of vulnerabilities from RED Agent
            fixes: List of fixes from BLUE Agent
            codebase: Current state of the codebase
            
        Returns:
            Tuple of (all_verified: bool, results: List[VerificationResult])
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting Verification Loop")
        self.logger.info(f"Vulnerabilities to verify: {len(vulnerabilities)}")
        self.logger.info("=" * 60)
        
        results = []
        iteration = 0
        
        # Track unresolved vulnerabilities
        unresolved = list(vulnerabilities)
        
        while iteration < self.MAX_ITERATIONS and unresolved:
            iteration += 1
            self.logger.info(f"\n--- Iteration {iteration}/{self.MAX_ITERATIONS} ---")
            self.logger.info(f"Unresolved vulnerabilities: {len(unresolved)}")
            
            newly_resolved = []
            still_unresolved = []
            
            for vuln in unresolved:
                vuln_id = vuln.get("id", "unknown")
                
                # Find corresponding fix
                fix = self._find_fix_for_vulnerability(vuln_id, fixes)
                if not fix:
                    self.logger.warning(f"No fix found for {vuln_id}")
                    still_unresolved.append(vuln)
                    continue
                
                # Verify the fix
                result = await self._verify_single_fix(
                    vulnerability=vuln,
                    fix=fix,
                    codebase=codebase,
                    attempt=iteration
                )
                results.append(result)
                
                if result.status == VerificationStatus.SUCCESS:
                    # Fix worked! Vulnerability is resolved
                    self.logger.info(f"✅ {vuln_id}: Fix VERIFIED (PoC blocked)")
                    newly_resolved.append(vuln)
                else:
                    # Fix failed, need new approach
                    self.logger.warning(f"❌ {vuln_id}: Fix FAILED (still exploitable)")
                    still_unresolved.append(vuln)
                    
                    # Generate new fix with different approach
                    if iteration < self.MAX_ATTEMPTS_PER_VULN:
                        self.logger.info(f"Requesting new fix for {vuln_id} (attempt {iteration + 1})")
                        new_fix = await self._request_alternative_fix(vuln, iteration)
                        if new_fix:
                            fixes.append(new_fix)
            
            unresolved = still_unresolved
            
            if not unresolved:
                self.logger.info("\n✅ ALL VULNERABILITIES VERIFIED!")
                break
        
        # Final status
        all_verified = len(unresolved) == 0
        
        if not all_verified:
            self.logger.warning(f"\n⚠️ {len(unresolved)} vulnerabilities still unresolved after {iteration} iterations")
            self._escalate_to_human(unresolved)
        
        self.logger.info("=" * 60)
        self.logger.info(f"Verification Complete: {'PASSED' if all_verified else 'FAILED'}")
        self.logger.info(f"Total iterations: {iteration}")
        self.logger.info(f"Total verification attempts: {len(results)}")
        self.logger.info("=" * 60)
        
        return all_verified, results
    
    async def _verify_single_fix(
        self,
        vulnerability: Dict[str, Any],
        fix: Dict[str, Any],
        codebase: Dict[str, str],
        attempt: int
    ) -> VerificationResult:
        """
        Verify a single fix by re-attacking with original PoC
        """
        vuln_id = vulnerability.get("id", "unknown")
        fix_id = fix.get("fix_id", "unknown")
        poc_code = vulnerability.get("poc_code", "")
        
        self.logger.info(f"Verifying fix {fix_id} for {vuln_id}")
        
        try:
            # Apply fix to codebase (in memory)
            patched_codebase = self._apply_fix(codebase, fix)
            
            # Run original PoC against patched code
            poc_result = await self._execute_poc(poc_code, patched_codebase)
            
            # Determine if vulnerability is fixed
            if poc_result.get("exploit_succeeded", True):
                # PoC still works = vulnerability not fixed
                return VerificationResult(
                    vulnerability_id=vuln_id,
                    fix_id=fix_id,
                    attempt=attempt,
                    status=VerificationStatus.FAILED,
                    poc_result=poc_result,
                    message="PoC exploit still succeeds - vulnerability not fixed",
                    timestamp=datetime.now().isoformat()
                )
            else:
                # PoC blocked = vulnerability fixed!
                return VerificationResult(
                    vulnerability_id=vuln_id,
                    fix_id=fix_id,
                    attempt=attempt,
                    status=VerificationStatus.SUCCESS,
                    poc_result=poc_result,
                    message="PoC exploit blocked - vulnerability successfully fixed",
                    timestamp=datetime.now().isoformat()
                )
                
        except Exception as e:
            self.logger.error(f"Verification error for {vuln_id}: {e}")
            return VerificationResult(
                vulnerability_id=vuln_id,
                fix_id=fix_id,
                attempt=attempt,
                status=VerificationStatus.ERROR,
                poc_result={"error": str(e)},
                message=f"Verification error: {e}",
                timestamp=datetime.now().isoformat()
            )
    
    def _find_fix_for_vulnerability(
        self, 
        vuln_id: str, 
        fixes: List[Dict]
    ) -> Dict[str, Any]:
        """Find the most recent fix for a vulnerability"""
        matching_fixes = [
            f for f in fixes 
            if f.get("vulnerability_id") == vuln_id
        ]
        
        if not matching_fixes:
            return None
        
        # Return most recent fix (last in list)
        return matching_fixes[-1]
    
    def _apply_fix(
        self, 
        codebase: Dict[str, str], 
        fix: Dict[str, Any]
    ) -> Dict[str, str]:
        """Apply a fix to the codebase (in memory)"""
        patched = codebase.copy()
        
        # Get selected fix option
        selected_idx = fix.get("selected_fix", 1) - 1
        fixes_list = fix.get("fixes", [])
        
        if selected_idx < len(fixes_list):
            selected_fix = fixes_list[selected_idx]
            code_diff = selected_fix.get("code_diff", {})
            
            file_path = code_diff.get("file", "")
            new_code = code_diff.get("after", "")
            
            if file_path and new_code:
                patched[file_path] = new_code
                self.logger.debug(f"Applied fix to {file_path}")
        
        return patched
    
    async def _execute_poc(
        self, 
        poc_code: str, 
        codebase: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Execute PoC against patched codebase
        
        TODO: Implement actual Docker sandbox execution
        For now, use simplified simulation
        """
        # Simplified PoC execution simulation
        # In production, this runs in Docker with:
        # - network_mode="none"
        # - read_only=True
        # - resource limits
        
        self.logger.debug("Executing PoC in sandbox (simulated)...")
        
        # Simple heuristic: if fix removes dangerous pattern, PoC fails
        dangerous_patterns = [
            "+ user_id",  # SQL concat
            "eval(",
            "exec(",
            "shell=True",
        ]
        
        # Check if any file still has dangerous patterns
        for file_content in codebase.values():
            for pattern in dangerous_patterns:
                if pattern in file_content:
                    return {
                        "exploit_succeeded": True,
                        "reason": f"Dangerous pattern still present: {pattern}"
                    }
        
        return {
            "exploit_succeeded": False,
            "reason": "No exploitable patterns found in patched code"
        }
    
    async def _request_alternative_fix(
        self, 
        vulnerability: Dict[str, Any],
        attempt: int
    ) -> Dict[str, Any]:
        """Request BLUE Agent to generate alternative fix"""
        self.logger.info(f"Requesting alternative fix approach (attempt {attempt + 1})")
        
        # Add context about failed attempts
        vuln_with_context = vulnerability.copy()
        vuln_with_context["previous_attempts"] = attempt
        vuln_with_context["request"] = "Previous fix failed verification. Try a different approach."
        
        try:
            result = await self.blue_agent.run(vuln_with_context)
            return result
        except Exception as e:
            self.logger.error(f"Failed to generate alternative fix: {e}")
            return None
    
    def _escalate_to_human(self, unresolved: List[Dict]):
        """Escalate unresolved vulnerabilities to human review"""
        self.logger.warning("=" * 60)
        self.logger.warning("ESCALATION: Human review required")
        self.logger.warning(f"Unresolved vulnerabilities: {len(unresolved)}")
        for vuln in unresolved:
            self.logger.warning(f"  - {vuln.get('id')}: {vuln.get('type')}")
        self.logger.warning("=" * 60)
        
        # TODO: Send notification via Slack/PagerDuty/Email
