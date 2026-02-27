"""
Test script to validate all 14 fixes work correctly.
"""
import asyncio
import re
import sys
sys.path.insert(0, '/Users/adityajadhav/ouroboros/Ouroboros')

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS {name}")
    else:
        failed += 1
        print(f"  FAIL {name} -- {detail}")

# ============================================================
print("=== Fix 1: _sanitize_file_path returns cleaned path ===")
from src.agents.blue_agent import BLUEAgent
agent = BLUEAgent()
result = agent._sanitize_file_path("/path/to/app.py")
test("strips /path/to/ prefix", result == "app.py", f"got: {result!r}")
result2 = agent._sanitize_file_path("")
test("empty string returns empty", result2 == "", f"got: {result2!r}")
result3 = agent._sanitize_file_path("clean_file.py")
test("clean path unchanged", result3 == "clean_file.py", f"got: {result3!r}")

# ============================================================
print("\n=== Fix 2+11: Gate 4 regex-based counting ===")
from src.security.safety_gates import SafetyGates
sg = SafetyGates()

# Test: execute() is NOT counted as a new DB query
original = 'query = "SELECT * FROM users WHERE id = " + user_id\nresult = db.query(query)'
fixed = 'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'
result = asyncio.get_event_loop().run_until_complete(sg.gate_4_performance(original, fixed))
test("execute() not counted as new query", result.status.value == "passed", f"status={result.status.value}, reason={result.reason}")

# Test: 'for' in strings not counted as loops
original2 = 'x = "search for items"\ny = "wait for response"'
fixed2 = 'x = "search for items"\ny = "wait for response"\nz = "looking for data"'
result2 = asyncio.get_event_loop().run_until_complete(sg.gate_4_performance(original2, fixed2))
test("'for' in strings not counted as loops", result2.status.value == "passed", f"reason={result2.reason}")

# ============================================================
print("\n=== Fix 3+4: Gate 3 receives fixed_code, test is meaningful ===")
# Gate 3 receives test_code and fixed_code now
# Just verify the method signature works with both args
result3 = asyncio.get_event_loop().run_until_complete(
    sg.gate_3_backward_compatibility(
        test_code="def test_x():\n    with open('module_under_test.py') as f:\n        source = f.read()\n    assert 'eval(' not in source\n",
        fixed_code="import os\nresult = os.path.basename(user_input)\n"
    )
)
test("Gate 3 accepts fixed_code param", result3.status.value == "passed", f"status={result3.status.value}")

# ============================================================
print("\n=== Fix 5: SKIPPED gates dont reject fixes ===")
from src.security.safety_gates import GateStatus
results = asyncio.get_event_loop().run_until_complete(
    sg.validate_fix(
        original_code="x = eval(user_input)",
        fixed_code="import ast\nx = ast.literal_eval(user_input)",
        test_code=None,  # No test code -> Gate 3 SKIPPED
        language="python"
    )
)
all_passed, gate_results = results
skipped_gates = [g for g in gate_results if g.status == GateStatus.SKIPPED]
test("Gate 3 skipped when no test_code", len(skipped_gates) > 0, f"skipped={len(skipped_gates)}")
test("SKIPPED does not cause rejection", all_passed == True, f"all_passed={all_passed}")

# ============================================================
print("\n=== Fix 7: MAX_RETRIES = 3 everywhere ===")
from src.orchestration.edges.verification_router import MAX_RETRIES
test("MAX_RETRIES is 3", MAX_RETRIES == 3, f"got {MAX_RETRIES}")

# ============================================================
print("\n=== Fix 8: Gate 2 fallback uses regex ===")
# '+ user_id' in a comment should NOT trigger
original_code = "# simple code\nresult = db.query(table)"
fixed_code = "# Removed + user_id concat for safety\nresult = db.query(table)"
result8 = asyncio.get_event_loop().run_until_complete(
    sg.gate_2_no_new_vulnerabilities(original_code, fixed_code)
)
test("comment '+ user_id' not flagged", result8.status.value == "passed", f"status={result8.status.value}, reason={result8.reason}")

# ============================================================
print("\n=== Fix 9: Verification engine uses regex ===")
from src.verification.verification_engine import VerificationEngine
ve = VerificationEngine()

# cursor.execute() should NOT trigger false positive
result9 = asyncio.get_event_loop().run_until_complete(
    ve._static_verification(
        fix_code='cursor.execute("SELECT * FROM users WHERE id = %s", (uid,))',
        vulnerability={}
    )
)
test("cursor.execute() passes static verification", result9["verified"] == True, f"verified={result9['verified']}")

# actual exec() SHOULD trigger
result9b = asyncio.get_event_loop().run_until_complete(
    ve._static_verification(
        fix_code='exec(user_input)',
        vulnerability={}
    )
)
test("exec() fails static verification", result9b["verified"] == False, f"verified={result9b['verified']}")

# ============================================================
print("\n=== Fix 12: response initialized before loop ===")
# We check the source code for the initialization
import inspect
source = inspect.getsource(BLUEAgent._generate_fixes)
test("response = '' before for loop", 'response = ""' in source, "not found in source")

# ============================================================
print("\n=== Fix 13: Dockerfile USER 0 caught as root ===")
from src.security.safety_gates import _validate_dockerfile_impl
result13a = _validate_dockerfile_impl("FROM node:18\nUSER 0\nCMD [\"node\", \"app.js\"]")
test("USER 0 detected as root", not any('USER' in c for c in result13a["checks"]), f"checks={result13a['checks']}")

result13b = _validate_dockerfile_impl("FROM node:18\nUSER 0:0\nCMD [\"node\", \"app.js\"]")
test("USER 0:0 detected as root", not any('USER' in c for c in result13b["checks"]), f"checks={result13b['checks']}")

result13c = _validate_dockerfile_impl("FROM node:18\nUSER 1000:1000\nCMD [\"node\", \"app.js\"]")
test("USER 1000:1000 passes", any('USER' in c for c in result13c["checks"]), f"checks={result13c['checks']}")

result13d = _validate_dockerfile_impl("FROM node:18\nUSER node\nCMD [\"node\", \"app.js\"]")
test("USER node passes", any('USER' in c for c in result13d["checks"]), f"checks={result13d['checks']}")

# ============================================================
print("\n=== Fix 14: Dockerfile threshold requires USER ===")
# Only pinned version + no secrets (2 checks) but no USER or HEALTHCHECK
result14 = _validate_dockerfile_impl("FROM node:18.19.0\nCMD [\"node\", \"app.js\"]")
test("pinned version alone fails (no USER)", result14["passed"] == False, f"passed={result14['passed']}, checks={result14['checks']}")

# USER + pinned = passes
result14b = _validate_dockerfile_impl("FROM node:18.19.0\nUSER node\nCMD [\"node\", \"app.js\"]")
test("USER + pinned version passes", result14b["passed"] == True, f"passed={result14b['passed']}")

# ============================================================
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed out of {passed+failed} tests")
if failed:
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
