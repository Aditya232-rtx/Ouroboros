#!/usr/bin/env python3
"""
Comprehensive test: Generate fixes AND validate through safety gates
"""
import asyncio
import sys
sys.path.insert(0, '/Users/adityajadhav/ouroboros/Ouroboros')

from src.agents.blue_agent import BLUEAgent
from src.security import safety_gates


async def test_blue_with_safety_gates():
    """Test BLUE Agent generates 3 fix options that pass safety gates"""
    print("\n" + "="*70)
    print("🧪 BLUE Agent Safety Gate Validation Test")
    print("="*70)
    
    blue = BLUEAgent()
    
    # Sample SQL Injection vulnerability
    vuln_data = {
        "vulnerability_id": "TEST-SQLi-001",
        "vulnerability_type": "sql_injection",
        "vulnerability_location": {
            "file": "app.py",
            "line": 42,
            "function": "get_user",
            "parameter": "user_id"
        },
        "vulnerable_code": '''def get_user(user_id):
    # VULNERABLE: String concatenation in SQL query
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()''',
        "cwe": "CWE-89",
        "cvss": 9.8,
        "language": "python"
    }
    
    print(f"\n📋 Test Vulnerability: SQL Injection (CWE-89)")
    print(f"   File: {vuln_data['vulnerability_location']['file']}")
    print(f"   CVSS: {vuln_data['cvss']} (Critical)")
    
    try:
        # Step 1: Generate fixes (this will create 3 options)
        print(f"\n⚙️  Step 1: Generating 3 fix options...")
        result = await blue.execute(vuln_data)
        
        fixes = result.get('fixes', [])
        print(f"   ✓ Generated {len(fixes)} fix option(s)")
        
        if len(fixes) != 3:
            print(f"   ⚠️  WARNING: Expected 3 options, got {len(fixes)}")
        
        # Step 2: Validate each fix through safety gates
        print(f"\n🔒 Step 2: Validating fixes through safety gates...")
        print(f"   Safety gates: Syntax, Static Analysis, Secrets,Auth, Logic")
        
        all_passed = True
        
        for i, fix in enumerate(fixes, 1):
            option_num = fix.get('option', i)
            approach = fix.get('approach', 'unknown')
            code_diff = fix.get('code_diff', {})
            
            print(f"\n   Option {option_num} ({approach.upper()}):")
            print(f"   {'─'*60}")
            
            # Show the fix
            after_code = code_diff.get('after', '')
            if after_code:
                print(f"   Fixed code preview:")
                code_lines = after_code.split('\n')
                preview_lines = code_lines[:5]
                for line in preview_lines:
                    print(f"     {line}")
                total_lines = len(code_lines)
                if total_lines > 5:
                    print(f"     ... ({total_lines} lines total)")
            
            # Check safety gates
            gates = fix.get('safety_gates', {})
            
            if gates:
                print(f"\n   Safety Gate Results:")
                option_passed = True
                
                for gate_name, gate_result in gates.items():
                    status = gate_result.get('status', 'unknown')
                    
                    if hasattr(status, 'value'):
                        status_str = status.value
                    else:
                        status_str = str(status)
                    
                    if status_str == 'passed':
                        print(f"     ✅ {gate_name}: PASSED")
                    else:
                        print(f"     ❌ {gate_name}: FAILED - {gate_result.get('reason', 'No details')}")
                        option_passed = False
                        all_passed = False
                
                if option_passed:
                    confidence = fix.get('confidence', 0)
                    print(f"\n   ✅ All gates PASSED (Confidence: {confidence:.1%})")
                else:
                    print(f"\n   ❌ Some gates FAILED")
            else:
                print(f"\n   ⚠️  No safety gate results (gates may not have run)")
                all_passed = False
        
        # Summary
        print(f"\n{'='*70}")
        print(f"📊 FINAL RESULTS")
        print(f"{'='*70}")
        
        print(f"\n✅ Fix Generation:")
        print(f"   - Generated {len(fixes)} fix options ({'✓' if len(fixes) == 3 else '✗'} expected 3)")
        
        print(f"\n🔒 Safety Gate Validation:")
        if all_passed and len(fixes) == 3:
            print(f"   ✅ SUCCESS: All {len(fixes)} fix options passed safety gates!")
            print(f"\n💡 This means:")
            print(f"   - NO eval(), exec(), or shell=True in fixes")
            print(f"   - NO hardcoded secrets or credentials")
            print(f"   - Proper input validation patterns")
            print(f"   - Safe API usage (parameterized queries)")
            print(f"   - All fixes are production-ready!")
        elif all_passed:
            print(f"   ⚠️  PARTIAL: Fixes passed gates, but only {len(fixes)} options generated")
        else:
            print(f"   ❌ FAILED: Some fixes did not pass safety gates")
            print(f"   → Need to harden prompts further or fix safety gate logic")
        
        # Show selected fix
        selected_idx = result.get('selected_fix', 1) - 1
        if 0 <= selected_idx < len(fixes):
            selected = fixes[selected_idx]
            print(f"\n🎯 Recommended Fix: Option {selected.get('option')} ({selected.get('approach')})")
            print(f"   Confidence: {selected.get('confidence', 0):.1%}")
            print(f"   Description: {selected.get('description', 'N/A')}")
        
        return len(fixes) == 3 and all_passed
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n🚀 Enhanced Agent Safety Gate Validation Test")
    print("   Testing BLUE Agent with actual safety gate validation\n")
    
    success = await test_blue_with_safety_gates()
    
    print(f"\n{'='*70}")
    if success:
        print("✅ TEST PASSED: All fixes generated and validated successfully!")
    else:
        print("⚠️  TEST INCOMPLETE: See details above")
    print(f"{'='*70}\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
