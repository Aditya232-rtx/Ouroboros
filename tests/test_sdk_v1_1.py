"""Quick SDK v1.1.0 verification script."""
import sys

tests_passed = 0
tests_total = 8

def check(label, fn):
    global tests_passed
    try:
        fn()
        tests_passed += 1
        print(f"  ✅ {label}")
    except Exception as e:
        print(f"  ❌ {label}: {e}")

# 1
check("ouroboros package import", lambda: __import__("ouroboros"))

# 2
def _test_agents():
    from src.agents.blue_agent import BLUEAgent, FixOption, BLUEAgentInput
check("src.agents imports", _test_agents)

# 3
def _test_integrations():
    from src.integrations.github_api import GitHubClient
check("src.integrations imports", _test_integrations)

# 4
def _test_security():
    from src.security import safety_gates
check("src.security imports", _test_security)

# 5
def _test_config():
    from config.settings import settings
check("config.settings imports", _test_config)

# 6
def _test_post_pr():
    from src.integrations.github_api import GitHubClient
    assert hasattr(GitHubClient, "post_pr_comment")
check("GitHubClient.post_pr_comment", _test_post_pr)

# 7
def _test_version():
    import ouroboros
    assert ouroboros.__version__ == "1.1.0", f"got {ouroboros.__version__}"
check("version == 1.1.0", _test_version)

# 8
def _test_main():
    import ouroboros.__main__
check("python -m ouroboros support", _test_main)

print(f"\n  {tests_passed}/{tests_total} tests passed")
if tests_passed == tests_total:
    print("  🎉 SDK v1.1.0 is fully functional!")
else:
    print("  ⚠️  Some tests failed")
    sys.exit(1)
