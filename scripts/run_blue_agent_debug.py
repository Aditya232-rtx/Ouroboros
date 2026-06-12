#!/usr/bin/env python3
"""
Ouroboros AI - Blue Agent Debug Test
Runs Blue Agent with detailed safety gate debugging for each vulnerability
Based on recent RED scan and Governance prioritization

Safety Gates:
1. Input Validation - No dangerous patterns (eval, exec, shell=True, etc.)
2. No New Vulnerabilities - Semgrep differential scan
3. Backward Compatibility - Tests pass 100%
4. Performance - <10% overhead
5. Test Coverage - >80% required
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.blue_agent import BLUEAgent, BLUEAgentInput
from src.security.safety_gates import SafetyGates, GateResult, GateStatus

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("BlueAgentDebug")


class SafetyGateDebugger(SafetyGates):
    """Extended SafetyGates with detailed debugging output"""
    
    def __init__(self):
        super().__init__()
        self.debug_results = []
    
    def _log_gate_header(self, gate_num: int, gate_name: str):
        print(f"\n{'='*70}")
        print(f"🔒 SAFETY GATE {gate_num}: {gate_name}")
        print('='*70)
    
    def _log_gate_result(self, result: GateResult):
        status_icon = {
            GateStatus.PASSED: "✅ PASSED",
            GateStatus.FAILED: "❌ FAILED",
            GateStatus.SKIPPED: "⏭️ SKIPPED"
        }
        
        print(f"\n  Status: {status_icon[result.status]}")
        print(f"  Reason: {result.reason}")
        
        if result.details:
            print(f"  Details:")
            for key, value in result.details.items():
                if isinstance(value, list) and len(value) > 3:
                    print(f"    • {key}: [{len(value)} items]")
                    for item in value[:3]:
                        print(f"      - {item}")
                    print(f"      ... and {len(value) - 3} more")
                else:
                    print(f"    • {key}: {value}")
        
        self.debug_results.append({
            "gate_name": result.gate_name,
            "status": result.status.value,
            "reason": result.reason,
            "details": result.details
        })
    
    async def validate_fix_with_debug(
        self,
        original_code: str,
        fixed_code: str,
        test_code: str = None,
        language: str = "python"
    ) -> tuple:
        """Run all 5 safety gates with detailed debugging output"""
        
        print("\n" + "🛡️ "*20)
        print("STARTING 5-LAYER SAFETY GATE VALIDATION")
        print("🛡️ "*20)
        
        results = []
        
        # Gate 1: Input Validation
        self._log_gate_header(1, "INPUT VALIDATION")
        print("  Checking for dangerous patterns...")
        print(f"  • eval(), exec(), __import__()")
        print(f"  • shell=True in subprocess")
        print(f"  • os.system() calls")
        print(f"  • Syntax validation for {language}")
        
        gate1 = await self.gate_1_input_validation(fixed_code, language)
        self._log_gate_result(gate1)
        results.append(gate1)
        
        # Gate 2: No New Vulnerabilities
        self._log_gate_header(2, "NO NEW VULNERABILITIES")
        print("  Running differential Semgrep scan...")
        print(f"  • Scanning original code ({len(original_code)} chars)")
        print(f"  • Scanning fixed code ({len(fixed_code)} chars)")
        print("  • Comparing for NEW vulnerabilities only")
        
        gate2 = await self.gate_2_no_new_vulnerabilities(original_code, fixed_code)
        self._log_gate_result(gate2)
        results.append(gate2)
        
        # Gate 3: Backward Compatibility
        self._log_gate_header(3, "BACKWARD COMPATIBILITY")
        if test_code:
            print(f"  Running pytest on test code ({len(test_code)} chars)...")
        else:
            print("  ⚠️ No test code provided - will be SKIPPED")
        
        gate3 = await self.gate_3_backward_compatibility(test_code, fixed_code)
        self._log_gate_result(gate3)
        results.append(gate3)
        
        # Gate 4: Performance
        self._log_gate_header(4, "PERFORMANCE")
        print("  Analyzing performance impact...")
        print(f"  • Checking for added loops")
        print(f"  • Checking for added database queries")
        print(f"  • Threshold: <10% overhead acceptable")
        
        gate4 = await self.gate_4_performance(original_code, fixed_code)
        self._log_gate_result(gate4)
        results.append(gate4)
        
        # Gate 5: Test Coverage
        self._log_gate_header(5, "TEST COVERAGE")
        if language.lower() in ["dockerfile", "yaml", "yml", "json", "xml", "shell", "bash"]:
            print(f"  Language: {language} (non-Python)")
            print(f"  • Using alternative validation for {language}")
        elif test_code:
            print(f"  Measuring coverage with coverage.py...")
            print(f"  • Required: >80% coverage")
        else:
            print("  ⚠️ No test code provided - will be FAILED")
        
        gate5 = await self.gate_5_test_coverage(fixed_code, test_code, language)
        self._log_gate_result(gate5)
        results.append(gate5)
        
        # Summary
        all_passed = all(r.status == GateStatus.PASSED for r in results)
        
        print("\n" + "="*70)
        print("📊 SAFETY GATE SUMMARY")
        print("="*70)
        
        for i, result in enumerate(results, 1):
            status_icon = "✅" if result.status == GateStatus.PASSED else ("❌" if result.status == GateStatus.FAILED else "⏭️")
            print(f"  Gate {i} - {result.gate_name}: {status_icon} {result.status.value.upper()}")
        
        print("-"*70)
        if all_passed:
            print("🎉 ALL GATES PASSED - Fix is APPROVED for deployment")
        else:
            failed = [r.gate_name for r in results if r.status == GateStatus.FAILED]
            skipped = [r.gate_name for r in results if r.status == GateStatus.SKIPPED]
            if failed:
                print(f"⚠️ FAILED GATES: {', '.join(failed)}")
            if skipped:
                print(f"⏭️ SKIPPED GATES: {', '.join(skipped)}")
            print("❌ Fix REJECTED - needs improvement")
        
        print("="*70 + "\n")
        
        return all_passed, results


async def run_blue_agent_debug():
    """Run Blue Agent with debug output for each safety gate"""
    
    print("\n" + "🔵 "*25)
    print("OUROBOROS BLUE AGENT - SAFETY GATE DEBUGGER")
    print("🔵 "*25)
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    
    # Vulnerabilities from the recent RED scan (V1-20260130-221623)
    # Based on the initial report: ouroboros-initial-vulnerable-app-nodejs-express-20260130-221950.md
    vulnerabilities = [
        {
            "id": "VULN-001",
            "vulnerability_type": "Configuration Misconfiguration",
            "cwe": "CWE-250",  # Execution with Unnecessary Privileges
            "cvss": 5.0,
            "severity": "High",
            "location": {
                "file": "Dockerfile",
                "line": 0
            },
            "description": "Running containers with 'root' user can lead to container escape. Add a 'USER' statement to run as non-root.",
            "vulnerable_code": """FROM node:14
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["node", "index.js"]""",
            "language": "dockerfile"
        },
        {
            "id": "VULN-002", 
            "vulnerability_type": "Configuration Misconfiguration",
            "cwe": "CWE-20",  # Improper Input Validation
            "cvss": 3.0,
            "severity": "Low",
            "location": {
                "file": "Dockerfile",
                "line": 0
            },
            "description": "No HEALTHCHECK defined. Add HEALTHCHECK instruction for container health monitoring.",
            "vulnerable_code": """FROM node:14
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["node", "index.js"]""",
            "language": "dockerfile"
        }
    ]
    
    print(f"\n📋 VULNERABILITIES TO FIX (from RED Agent scan):")
    print("-"*60)
    for v in vulnerabilities:
        print(f"  [{v['id']}] {v['vulnerability_type']}")
        print(f"       Severity: {v['severity']} | CWE: {v['cwe']} | CVSS: {v['cvss']}")
        print(f"       File: {v['location']['file']}")
        print()
    
    # Initialize Blue Agent
    print("\n🔧 Initializing BLUE Agent...")
    try:
        blue_agent = BLUEAgent()
        model_info = getattr(blue_agent, 'model_name', None) or getattr(blue_agent.model, 'model', 'ouroboros-blue')
        print(f"  ✅ Model loaded: {model_info}")
    except Exception as e:
        print(f"  ❌ Failed to initialize Blue Agent: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Initialize safety gate debugger
    safety_debugger = SafetyGateDebugger()
    
    all_results = []
    
    for vuln in vulnerabilities:
        print("\n" + "="*80)
        print(f"🔵 PROCESSING VULNERABILITY: {vuln['id']}")
        print(f"   Type: {vuln['vulnerability_type']}")
        print(f"   File: {vuln['location']['file']}")
        print("="*80)
        
        # Create Blue Agent input as dict (not object)
        blue_input = {
            "vulnerability_id": vuln["id"],
            "vulnerability_type": vuln["vulnerability_type"],
            "vulnerability_location": vuln["location"],
            "vulnerable_code": vuln["vulnerable_code"],
            "cwe": vuln["cwe"],
            "cvss": vuln["cvss"],
            "language": vuln["language"]
        }
        
        # Generate fix
        print("\n📝 Generating fix with BLUE Agent...")
        print("-"*50)
        
        try:
            result = await blue_agent.run(blue_input)
            
            # Handle both dict and object results
            if isinstance(result, dict):
                fixes = result.get("fixes", [])
                selected_fix = result.get("selected_fix", 0)
            else:
                fixes = getattr(result, "fixes", [])
                selected_fix = getattr(result, "selected_fix", 0)
            
            if fixes and len(fixes) > 0:
                fix = fixes[selected_fix] if selected_fix < len(fixes) else fixes[0]
                
                # Handle both dict and object fixes
                if isinstance(fix, dict):
                    fix_option = fix.get("option", 1)
                    fix_approach = fix.get("approach", "N/A")
                    fix_confidence = fix.get("confidence", 0.0)
                    fix_recommendation = fix.get("recommendation", "N/A")
                    code_diff = fix.get("code_diff", {})
                    fix_before = code_diff.get("before", "") if isinstance(code_diff, dict) else getattr(code_diff, "before", "")
                    fix_after = code_diff.get("after", "") if isinstance(code_diff, dict) else getattr(code_diff, "after", "")
                    fix_test_code = fix.get("test_code", "")
                else:
                    fix_option = getattr(fix, "option", 1)
                    fix_approach = getattr(fix, "approach", "N/A")
                    fix_confidence = getattr(fix, "confidence", 0.0)
                    fix_recommendation = getattr(fix, "recommendation", "N/A")
                    code_diff = getattr(fix, "code_diff", None)
                    fix_before = getattr(code_diff, "before", "") if code_diff else ""
                    fix_after = getattr(code_diff, "after", "") if code_diff else ""
                    fix_test_code = getattr(fix, "test_code", "")
                
                print(f"\n✅ Fix generated successfully!")
                print(f"   Option: {fix_option}")
                print(f"   Approach: {fix_approach}")
                print(f"   Confidence: {fix_confidence:.2%}")
                print(f"   Recommendation: {fix_recommendation}")
                
                print(f"\n📄 ORIGINAL CODE:")
                print("-"*40)
                print(fix_before[:500] if fix_before else "N/A")
                
                print(f"\n📄 FIXED CODE:")
                print("-"*40)
                print(fix_after[:500] if fix_after else "N/A")
                
                if fix_test_code:
                    print(f"\n🧪 TEST CODE:")
                    print("-"*40)
                    print(fix_test_code[:300])
                
                # Run safety gates with debug
                print("\n" + "🛡️ "*15)
                print("RUNNING DETAILED SAFETY GATE VALIDATION")
                print("🛡️ "*15)
                
                all_passed, gate_results = await safety_debugger.validate_fix_with_debug(
                    original_code=vuln["vulnerable_code"],
                    fixed_code=fix_after,
                    test_code=fix_test_code,
                    language=vuln["language"]
                )
                
                all_results.append({
                    "vulnerability_id": vuln["id"],
                    "vulnerability_type": vuln["vulnerability_type"],
                    "fix_generated": True,
                    "fix_approach": fix_approach,
                    "fix_confidence": fix_confidence,
                    "all_gates_passed": all_passed,
                    "gate_results": [
                        {
                            "gate": g.gate_name,
                            "status": g.status.value,
                            "reason": g.reason
                        }
                        for g in gate_results
                    ]
                })
                
            else:
                print(f"\n⚠️ No fixes generated for this vulnerability")
                all_results.append({
                    "vulnerability_id": vuln["id"],
                    "vulnerability_type": vuln["vulnerability_type"],
                    "fix_generated": False,
                    "all_gates_passed": False,
                    "gate_results": []
                })
                
        except Exception as e:
            logger.exception(f"Error processing vulnerability {vuln['id']}")
            print(f"\n❌ Error: {e}")
            all_results.append({
                "vulnerability_id": vuln["id"],
                "vulnerability_type": vuln["vulnerability_type"],
                "fix_generated": False,
                "error": str(e),
                "all_gates_passed": False,
                "gate_results": []
            })
    
    # Final summary
    print("\n" + "="*80)
    print("📊 BLUE AGENT DEBUG TEST - FINAL SUMMARY")
    print("="*80)
    
    total_vulns = len(vulnerabilities)
    fixed = sum(1 for r in all_results if r.get("fix_generated", False))
    all_passed = sum(1 for r in all_results if r.get("all_gates_passed", False))
    
    print(f"\n  Total Vulnerabilities: {total_vulns}")
    print(f"  Fixes Generated:       {fixed}/{total_vulns}")
    print(f"  All Gates Passed:      {all_passed}/{total_vulns}")
    
    print("\n  Per-Vulnerability Results:")
    print("  " + "-"*60)
    
    for r in all_results:
        status = "✅ APPROVED" if r.get("all_gates_passed") else "❌ REJECTED"
        print(f"  [{r['vulnerability_id']}] {r['vulnerability_type'][:30]}: {status}")
        
        if r.get("gate_results"):
            for g in r["gate_results"]:
                icon = "✅" if g["status"] == "passed" else ("❌" if g["status"] == "failed" else "⏭️")
                print(f"      {icon} {g['gate']}: {g['status']}")
    
    # Save results
    output_dir = Path("outputs/blue_agent_debug")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"debug-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "vulnerabilities_processed": total_vulns,
            "fixes_generated": fixed,
            "all_gates_passed": all_passed,
            "results": all_results,
            "safety_gate_debug": safety_debugger.debug_results
        }, f, indent=2, default=str)
    
    print(f"\n📁 Results saved to: {output_file}")
    print("\n" + "🔵 "*25 + "\n")
    
    return all_results


if __name__ == "__main__":
    results = asyncio.run(run_blue_agent_debug())
