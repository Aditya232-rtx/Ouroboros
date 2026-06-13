"""
Ouroboros SDK — smoke tests.

Run with:  pytest tests/test_sdk.py -v
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root is on path for src.* imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ─────────────────────────────────────────────────────────────────
# Basic import / version tests
# ─────────────────────────────────────────────────────────────────

def test_import():
    """SDK package must be importable."""
    from ouroboros import Ouroboros
    assert Ouroboros is not None


def test_version():
    """Version string must be 1.0.0."""
    import ouroboros
    assert ouroboros.__version__ == "1.0.0"


def test_cli_import():
    """CLI entry-point must be importable."""
    from ouroboros.cli import cli
    assert cli is not None


def test_github_client_import():
    """GitHub client must be importable."""
    from ouroboros.github import GitHubClient
    assert GitHubClient is not None


def test_fix_generator_import():
    """Fix generator must be importable."""
    from ouroboros.fixes import FixGenerator
    assert FixGenerator is not None


def test_docs_generator_import():
    """Documentation generator must be importable."""
    from ouroboros.docs import DocumentationGenerator
    assert DocumentationGenerator is not None


def test_continuous_scanner_import():
    """Continuous scanner must be importable."""
    from ouroboros.continuous import ContinuousScanner
    assert ContinuousScanner is not None


# ─────────────────────────────────────────────────────────────────
# Core class tests
# ─────────────────────────────────────────────────────────────────

def test_ouroboros_init_missing_config():
    """Should raise FileNotFoundError when config does not exist."""
    from ouroboros.core import Ouroboros
    with pytest.raises(FileNotFoundError):
        Ouroboros("/nonexistent/path.yaml")


def test_ouroboros_init_with_config(tmp_path):
    """Should initialise cleanly with a valid YAML config."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text('github:\n  token: "test"\n')
    ouro = _make_ouroboros(cfg)
    assert ouro.config["github"]["token"] == "test"


# ─────────────────────────────────────────────────────────────────
# Scan summary builder
# ─────────────────────────────────────────────────────────────────

def test_build_summary_success():
    """_build_summary must return correct counts."""
    ouro = _make_ouroboros_stub()
    state = {
        "scan_id": "SCAN-TEST",
        "vulnerabilities": [
            {"id": "v1", "severity": "CRITICAL"},
            {"id": "v2", "severity": "HIGH"},
        ],
        "fixes": [{"vuln_id": "v1"}],
        "verification_results": [{"verified": True}],
        "all_verified": True,
        "pr_url": "https://github.com/a/b/pull/1",
        "pr_number": 1,
    }
    summary = ouro._build_summary("https://github.com/a/b", state)
    assert summary["success"] is True
    assert summary["vulnerabilities_found"] == 2
    assert summary["critical_count"] == 1
    assert summary["fixes_generated"] == 1
    assert summary["pr_url"] == "https://github.com/a/b/pull/1"


def test_build_summary_aborted():
    """Aborted workflow must set success=False."""
    ouro = _make_ouroboros_stub()
    state = {
        "workflow_aborted": True,
        "abort_reason": "Max retries",
        "vulnerabilities": [],
        "fixes": [],
        "verification_results": [],
    }
    summary = ouro._build_summary("https://github.com/a/b", state)
    assert summary["success"] is False
    assert summary["aborted"] is True


# ─────────────────────────────────────────────────────────────────
# Fix generator tests
# ─────────────────────────────────────────────────────────────────

def test_fix_verify_patches():
    """Patches with content should verify as True."""
    from ouroboros.fixes import FixGenerator
    gen = FixGenerator({})
    assert gen._verify_patches([{"content": "abc"}]) is True
    assert gen._verify_patches([{"content": ""}]) is False


def test_fix_risk_reduction():
    """Risk reduction should be proportional."""
    from ouroboros.fixes import FixGenerator
    gen = FixGenerator({})
    assert gen._estimate_risk_reduction(
        [{"id": 1}, {"id": 2}],
        [{"id": 1}],
    ) == 50


# ─────────────────────────────────────────────────────────────────
# GitHub client tests
# ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_github_clone_repo(tmp_path):
    """clone_repo should parse owner/repo from URL."""
    from ouroboros.github import GitHubClient
    client = GitHubClient("fake-token")

    with patch("ouroboros.github.git.Repo") as MockRepo:
        MockRepo.clone_from = MagicMock()
        result = await client.clone_repo(
            "https://github.com/owner/myrepo.git"
        )

    assert result["owner"] == "owner"
    assert result["repo"] == "myrepo"
    assert MockRepo.clone_from.called


# ─────────────────────────────────────────────────────────────────
# Full pipeline mock test
# ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_full_pipeline_mocked():
    """
    core.scan() must call the workflow and return a summary dict
    with all expected keys — using a fully mocked workflow.
    """
    from ouroboros.core import Ouroboros

    fake_state = {
        "scan_id": "SCAN-MOCK",
        "vulnerabilities": [{"id": "v1", "severity": "HIGH"}],
        "fixes": [{"vuln_id": "v1"}],
        "verification_results": [{"verified": True}],
        "all_verified": True,
        "pr_url": "https://github.com/a/b/pull/99",
        "pr_number": 99,
        "final_report_url": "/tmp/report.pdf",
        "workflow_aborted": False,
    }

    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock(return_value=fake_state)

    ouro = _make_ouroboros_stub()
    ouro._workflow = mock_workflow

    result = await ouro.scan("https://github.com/a/b")

    assert result["success"] is True
    assert result["vulnerabilities_found"] == 1
    assert result["pr_url"] == "https://github.com/a/b/pull/99"
    assert result["docs_path"] == "/tmp/report.pdf"
    assert "scan_id" in result


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _make_ouroboros(cfg_path):
    """Create an Ouroboros instance with a real config file."""
    from ouroboros.core import Ouroboros
    return Ouroboros(str(cfg_path))


def _make_ouroboros_stub():
    """Create an Ouroboros without reading any file."""
    from ouroboros.core import Ouroboros
    ouro = Ouroboros.__new__(Ouroboros)
    ouro.config = {"github": {"token": "test"}}
    ouro._workflow = None
    ouro._gh_client = None
    return ouro
