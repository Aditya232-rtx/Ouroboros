"""
Ouroboros SDK — Rigorous Test Suite
====================================
Covers every public class, method, edge case, and integration path.

Run:  pytest tests/test_sdk_rigorous.py -v --tb=short
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ═══════════════════════════════════════════════════════════════════
# SECTION 1: Package-level imports & metadata
# ═══════════════════════════════════════════════════════════════════

class TestPackageMetadata:

    def test_import_ouroboros(self):
        import ouroboros
        assert ouroboros is not None

    def test_version_is_semver(self):
        import ouroboros
        parts = ouroboros.__version__.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_version_is_1_1_0(self):
        import ouroboros
        assert ouroboros.__version__ == "1.1.0"

    def test_all_exports(self):
        import ouroboros
        assert "Ouroboros" in ouroboros.__all__
        assert "cli" in ouroboros.__all__

    def test_ouroboros_class_accessible(self):
        from ouroboros import Ouroboros
        assert callable(Ouroboros)

    def test_cli_accessible(self):
        from ouroboros import cli
        assert callable(cli)


# ═══════════════════════════════════════════════════════════════════
# SECTION 2: All module imports
# ═══════════════════════════════════════════════════════════════════

class TestModuleImports:

    def test_core_module(self):
        from ouroboros.core import Ouroboros
        assert Ouroboros is not None

    def test_cli_module(self):
        from ouroboros.cli import cli, scan, watch, info
        assert all(c is not None for c in [cli, scan, watch, info])

    def test_github_module(self):
        from ouroboros.github import GitHubClient
        assert GitHubClient is not None

    def test_fixes_module(self):
        from ouroboros.fixes import FixGenerator, TEMPLATES_DIR
        assert FixGenerator is not None
        assert isinstance(TEMPLATES_DIR, Path)

    def test_docs_module(self):
        from ouroboros.docs import DocumentationGenerator
        assert DocumentationGenerator is not None

    def test_continuous_module(self):
        from ouroboros.continuous import ContinuousScanner
        assert ContinuousScanner is not None


# ═══════════════════════════════════════════════════════════════════
# SECTION 3: Ouroboros Core class
# ═══════════════════════════════════════════════════════════════════

class TestOuroborosCore:
    """Tests for ouroboros.core.Ouroboros"""

    def _make_config(self, tmp_path, extra=""):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(f'github:\n  token: "test-token"\n{extra}')
        return str(cfg)

    def _make_stub(self):
        from ouroboros.core import Ouroboros
        ouro = Ouroboros.__new__(Ouroboros)
        ouro.config = {"github": {"token": "test"}}
        ouro._workflow = None
        ouro._gh_client = None
        return ouro

    # --- Config loading ---

    def test_init_with_valid_config(self, tmp_path):
        from ouroboros.core import Ouroboros
        cfg_path = self._make_config(tmp_path)
        ouro = Ouroboros(cfg_path)
        assert ouro.config["github"]["token"] == "test-token"

    def test_init_missing_config_raises(self):
        from ouroboros.core import Ouroboros
        with pytest.raises(FileNotFoundError, match="Config not found"):
            Ouroboros("/does/not/exist.yaml")

    def test_init_empty_yaml(self, tmp_path):
        cfg = tmp_path / "empty.yaml"
        cfg.write_text("")
        from ouroboros.core import Ouroboros
        ouro = Ouroboros(str(cfg))
        assert ouro.config == {}

    def test_load_config_returns_dict(self, tmp_path):
        ouro = self._make_stub()
        cfg = tmp_path / "test.yaml"
        cfg.write_text('foo: bar\nnested:\n  key: val\n')
        result = ouro._load_config(str(cfg))
        assert result == {"foo": "bar", "nested": {"key": "val"}}

    # --- Env overrides ---

    def test_apply_env_overrides_sets_github_token(self, tmp_path):
        from ouroboros.core import Ouroboros
        cfg_path = self._make_config(tmp_path)
        # Remove any pre-existing env var
        os.environ.pop("GITHUB_TOKEN", None)
        ouro = Ouroboros(cfg_path)
        assert os.environ.get("GITHUB_TOKEN") == "test-token"
        # Clean up
        os.environ.pop("GITHUB_TOKEN", None)

    def test_apply_env_overrides_does_not_overwrite(self, tmp_path):
        from ouroboros.core import Ouroboros
        os.environ["GITHUB_TOKEN"] = "existing"
        cfg_path = self._make_config(tmp_path)
        ouro = Ouroboros(cfg_path)
        assert os.environ["GITHUB_TOKEN"] == "existing"
        os.environ.pop("GITHUB_TOKEN", None)

    def test_apply_env_overrides_ollama(self, tmp_path):
        from ouroboros.core import Ouroboros
        os.environ.pop("OLLAMA_BASE_URL", None)
        cfg = tmp_path / "cfg.yaml"
        cfg.write_text('github:\n  token: "t"\nollama:\n  url: "http://test:11434"\n')
        ouro = Ouroboros(str(cfg))
        assert os.environ.get("OLLAMA_BASE_URL") == "http://test:11434"
        os.environ.pop("OLLAMA_BASE_URL", None)

    # --- Lazy loading ---

    def test_workflow_lazy_loaded(self):
        ouro = self._make_stub()
        assert ouro._workflow is None

    def test_github_client_lazy_loaded(self):
        ouro = self._make_stub()
        assert ouro._gh_client is None

    def test_get_github_client_returns_client(self):
        ouro = self._make_stub()
        client = ouro._get_github_client()
        from ouroboros.github import GitHubClient
        assert isinstance(client, GitHubClient)

    def test_get_github_client_cached(self):
        ouro = self._make_stub()
        c1 = ouro._get_github_client()
        c2 = ouro._get_github_client()
        assert c1 is c2

    # --- _build_summary ---

    def test_build_summary_all_fields_present(self):
        ouro = self._make_stub()
        state = {
            "scan_id": "SCAN-1",
            "vulnerabilities": [],
            "fixes": [],
            "verification_results": [],
            "all_verified": False,
            "pr_url": None,
            "pr_number": None,
            "final_report_url": None,
            "workflow_aborted": False,
            "abort_reason": None,
            "governance_decisions": {},
            "risk_scores": {},
            "errors": [],
        }
        s = ouro._build_summary("https://github.com/a/b", state)
        required_keys = [
            "success", "repo_url", "scan_id", "vulnerabilities_found",
            "critical_count", "fixes_generated", "verified_count",
            "all_verified", "risk_reduction_pct", "pr_url", "pr_number",
            "docs_path", "deploy_safe", "governance_decisions",
            "risk_scores", "errors", "aborted", "abort_reason",
        ]
        for key in required_keys:
            assert key in s, f"Missing key: {key}"

    def test_build_summary_success_state(self):
        ouro = self._make_stub()
        state = {
            "scan_id": "SCAN-42",
            "vulnerabilities": [
                {"id": "v1", "severity": "CRITICAL", "cvss_score": 9.5},
                {"id": "v2", "severity": "HIGH"},
                {"id": "v3", "severity": "CRITICAL"},
            ],
            "fixes": [{"id": "f1"}, {"id": "f2"}],
            "verification_results": [
                {"verified": True},
                {"verified": False},
            ],
            "all_verified": False,
            "pr_url": "https://github.com/x/y/pull/7",
            "pr_number": 7,
            "final_report_url": "/tmp/report.pdf",
            "workflow_aborted": False,
        }
        s = ouro._build_summary("https://github.com/x/y", state)
        assert s["success"] is True
        assert s["vulnerabilities_found"] == 3
        assert s["critical_count"] == 2
        assert s["fixes_generated"] == 2
        assert s["verified_count"] == 1
        assert s["risk_reduction_pct"] == 33  # 1/3 = 33%
        assert s["pr_url"] == "https://github.com/x/y/pull/7"
        assert s["docs_path"] == "/tmp/report.pdf"

    def test_build_summary_aborted_state(self):
        ouro = self._make_stub()
        state = {
            "workflow_aborted": True,
            "abort_reason": "Max retries exceeded",
            "vulnerabilities": [{"id": "v1"}],
            "fixes": [],
            "verification_results": [],
        }
        s = ouro._build_summary("url", state)
        assert s["success"] is False
        assert s["aborted"] is True
        assert s["abort_reason"] == "Max retries exceeded"

    def test_build_summary_zero_vulns_no_division_error(self):
        ouro = self._make_stub()
        state = {
            "vulnerabilities": [],
            "fixes": [],
            "verification_results": [],
        }
        s = ouro._build_summary("url", state)
        assert s["risk_reduction_pct"] == 0

    def test_build_summary_cvss_based_critical(self):
        """Vulns with cvss_score >= 9.0 should count as critical even without severity field."""
        ouro = self._make_stub()
        state = {
            "vulnerabilities": [
                {"id": "v1", "cvss_score": 9.8},
                {"id": "v2", "cvss_score": 7.5},
            ],
            "fixes": [],
            "verification_results": [],
        }
        s = ouro._build_summary("url", state)
        assert s["critical_count"] == 1

    # --- scan() with mocked workflow ---

    @pytest.mark.asyncio
    async def test_scan_calls_workflow_run(self):
        ouro = self._make_stub()
        mock_wf = MagicMock()
        mock_wf.run = AsyncMock(return_value={
            "scan_id": "S1",
            "vulnerabilities": [{"id": "v1", "severity": "HIGH"}],
            "fixes": [{"id": "f1"}],
            "verification_results": [{"verified": True}],
            "all_verified": True,
            "pr_url": "https://github.com/a/b/pull/1",
            "pr_number": 1,
            "final_report_url": "/tmp/r.pdf",
            "workflow_aborted": False,
        })
        ouro._workflow = mock_wf

        result = await ouro.scan("https://github.com/a/b")

        mock_wf.run.assert_called_once()
        call_args = mock_wf.run.call_args[0][0]
        assert call_args["repo_url"] == "https://github.com/a/b"
        assert call_args["scan_profile"] == "standard"
        assert call_args["create_pr"] is True
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_scan_quick_sets_profile(self):
        ouro = self._make_stub()
        mock_wf = MagicMock()
        mock_wf.run = AsyncMock(return_value={
            "vulnerabilities": [], "fixes": [],
            "verification_results": [], "workflow_aborted": False,
        })
        ouro._workflow = mock_wf

        await ouro.scan_quick("https://github.com/a/b")
        call_args = mock_wf.run.call_args[0][0]
        assert call_args["scan_profile"] == "quick"
        assert call_args["create_pr"] is False

    @pytest.mark.asyncio
    async def test_scan_deep_sets_profile(self):
        ouro = self._make_stub()
        mock_wf = MagicMock()
        mock_wf.run = AsyncMock(return_value={
            "vulnerabilities": [], "fixes": [],
            "verification_results": [], "workflow_aborted": False,
        })
        ouro._workflow = mock_wf

        await ouro.scan_deep("https://github.com/a/b")
        call_args = mock_wf.run.call_args[0][0]
        assert call_args["scan_profile"] == "deep"
        assert call_args["create_pr"] is True

    @pytest.mark.asyncio
    async def test_scan_custom_kwargs(self):
        ouro = self._make_stub()
        mock_wf = MagicMock()
        mock_wf.run = AsyncMock(return_value={
            "vulnerabilities": [], "fixes": [],
            "verification_results": [], "workflow_aborted": False,
        })
        ouro._workflow = mock_wf

        await ouro.scan(
            "https://github.com/a/b",
            scan_id="CUSTOM-ID",
            user_id="tester",
            branch="develop",
            commit_sha="abc123",
        )
        call_args = mock_wf.run.call_args[0][0]
        assert call_args["scan_id"] == "CUSTOM-ID"
        assert call_args["user_id"] == "tester"
        assert call_args["branch"] == "develop"
        assert call_args["commit_sha"] == "abc123"


# ═══════════════════════════════════════════════════════════════════
# SECTION 4: GitHubClient
# ═══════════════════════════════════════════════════════════════════

class TestGitHubClient:

    def test_init_with_token(self):
        from ouroboros.github import GitHubClient
        client = GitHubClient("fake-token")
        assert client.token == "fake-token"
        assert client._gh is not None

    def test_init_without_token(self):
        from ouroboros.github import GitHubClient
        client = GitHubClient("")
        assert client._gh is None

    @pytest.mark.asyncio
    async def test_clone_repo_parses_url(self):
        from ouroboros.github import GitHubClient
        client = GitHubClient("tok")

        with patch("ouroboros.github.git.Repo") as MockRepo:
            MockRepo.clone_from = MagicMock()
            result = await client.clone_repo(
                "https://github.com/myorg/myrepo.git"
            )

        assert result["owner"] == "myorg"
        assert result["repo"] == "myrepo"
        assert result["url"] == "https://github.com/myorg/myrepo.git"
        assert "local_path" in result

    @pytest.mark.asyncio
    async def test_clone_repo_strips_trailing_slash(self):
        from ouroboros.github import GitHubClient
        client = GitHubClient("tok")

        with patch("ouroboros.github.git.Repo") as MockRepo:
            MockRepo.clone_from = MagicMock()
            result = await client.clone_repo(
                "https://github.com/org/repo/"
            )
        assert result["owner"] == "org"
        assert result["repo"] == "repo"

    @pytest.mark.asyncio
    async def test_clone_injects_auth_token(self):
        from ouroboros.github import GitHubClient
        client = GitHubClient("secret123")

        with patch("ouroboros.github.git.Repo") as MockRepo:
            MockRepo.clone_from = MagicMock()
            await client.clone_repo("https://github.com/o/r.git")

        call_url = MockRepo.clone_from.call_args[0][0]
        assert "x-access-token:secret123@" in call_url

    @pytest.mark.asyncio
    async def test_clone_no_token_uses_plain_url(self):
        from ouroboros.github import GitHubClient
        client = GitHubClient("")

        with patch("ouroboros.github.git.Repo") as MockRepo:
            MockRepo.clone_from = MagicMock()
            await client.clone_repo("https://github.com/o/r.git")

        call_url = MockRepo.clone_from.call_args[0][0]
        assert "x-access-token" not in call_url

    @pytest.mark.asyncio
    async def test_create_fix_pr_requires_token(self):
        from ouroboros.github import GitHubClient
        client = GitHubClient("")  # no token
        with pytest.raises(RuntimeError, match="token is required"):
            await client.create_fix_pr(
                repo_url="https://github.com/o/r",
                patches=[{"file_path": "f.py", "content": "x"}],
            )

    @pytest.mark.asyncio
    async def test_create_fix_pr_requires_owner_repo(self):
        from ouroboros.github import GitHubClient
        client = GitHubClient("tok")
        with pytest.raises(ValueError, match="Must supply"):
            await client.create_fix_pr(patches=[])

    @pytest.mark.asyncio
    async def test_create_fix_pr_resolves_owner_from_url(self):
        from github import GithubException
        from ouroboros.github import GitHubClient
        client = GitHubClient("tok")

        mock_repo = MagicMock()
        mock_repo.default_branch = "main"
        mock_branch = MagicMock()
        mock_branch.commit.sha = "abc123"
        mock_repo.get_branch.return_value = mock_branch
        mock_repo.create_git_ref = MagicMock()
        mock_repo.get_contents.side_effect = GithubException(404, "Not Found", None)
        mock_repo.create_file = MagicMock()
        mock_pr = MagicMock()
        mock_pr.html_url = "https://github.com/own/rep/pull/1"
        mock_repo.create_pull.return_value = mock_pr

        client._gh = MagicMock()
        client._gh.get_repo.return_value = mock_repo

        url = await client.create_fix_pr(
            repo_url="https://github.com/own/rep.git",
            patches=[{"file_path": "x.py", "content": "fix"}],
        )
        client._gh.get_repo.assert_called_with("own/rep")
        assert url == "https://github.com/own/rep/pull/1"


# ═══════════════════════════════════════════════════════════════════
# SECTION 5: FixGenerator
# ═══════════════════════════════════════════════════════════════════

class TestFixGenerator:

    def _make_gen(self):
        from ouroboros.fixes import FixGenerator
        return FixGenerator({})

    def test_init(self):
        gen = self._make_gen()
        assert gen.config == {}
        assert gen.jinja_env is not None

    def test_verify_patches_all_have_content(self):
        gen = self._make_gen()
        assert gen._verify_patches([
            {"content": "a"},
            {"content": "b"},
        ]) is True

    def test_verify_patches_empty_content_fails(self):
        gen = self._make_gen()
        assert gen._verify_patches([{"content": ""}]) is False

    def test_verify_patches_missing_content_fails(self):
        gen = self._make_gen()
        assert gen._verify_patches([{"file": "x.py"}]) is False

    def test_verify_patches_empty_list_is_true(self):
        gen = self._make_gen()
        assert gen._verify_patches([]) is True

    def test_risk_reduction_full(self):
        gen = self._make_gen()
        vulns = [{"id": 1}, {"id": 2}]
        patches = [{"id": 1}, {"id": 2}]
        assert gen._estimate_risk_reduction(vulns, patches) == 100

    def test_risk_reduction_partial(self):
        gen = self._make_gen()
        assert gen._estimate_risk_reduction(
            [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}],
            [{"id": 1}],
        ) == 25

    def test_risk_reduction_zero_vulns(self):
        gen = self._make_gen()
        assert gen._estimate_risk_reduction([], []) == 0

    def test_pick_template_docker(self):
        gen = self._make_gen()
        assert gen._pick_template({"description": "Docker container escape"}) == "docker-security.patch.j2"

    def test_pick_template_api(self):
        gen = self._make_gen()
        assert gen._pick_template({"description": "SQL injection in API"}) == "api-hardening.patch.j2"

    def test_pick_template_auth(self):
        gen = self._make_gen()
        assert gen._pick_template({"type": "auth bypass"}) == "api-hardening.patch.j2"

    def test_pick_template_unknown(self):
        gen = self._make_gen()
        assert gen._pick_template({"description": "memory leak"}) is None

    @pytest.mark.asyncio
    async def test_generate_template_mode_docker(self):
        gen = self._make_gen()
        vulns = [{
            "id": "VULN-1",
            "description": "Docker container running as root",
            "file": "Dockerfile",
            "severity": "HIGH",
            "vulnerable_code": "FROM python:3.11\nUSER root",
        }]
        result = await gen.generate("/tmp/repo", vulns, mode="template")
        assert len(result["patches"]) == 1
        assert result["patches"][0]["vuln_id"] == "VULN-1"
        assert result["patches"][0]["severity"] == "HIGH"
        assert "content" in result["patches"][0]
        assert result["verified"] is True

    @pytest.mark.asyncio
    async def test_generate_template_mode_api(self):
        gen = self._make_gen()
        vulns = [{
            "id": "VULN-2",
            "description": "SQL injection vulnerability",
            "file": "app.py",
            "severity": "CRITICAL",
            "vulnerable_code": "cursor.execute(f'SELECT * FROM users WHERE id={uid}')",
        }]
        result = await gen.generate("/tmp/repo", vulns, mode="template")
        assert len(result["patches"]) == 1
        assert result["risk_reduction"] == 100

    @pytest.mark.asyncio
    async def test_generate_template_no_matching_template(self):
        gen = self._make_gen()
        vulns = [{
            "id": "V",
            "description": "memory leak in module",
            "file": "m.py",
        }]
        result = await gen.generate("/tmp/repo", vulns, mode="template")
        assert len(result["patches"]) == 0
        assert result["risk_reduction"] == 0

    @pytest.mark.asyncio
    async def test_generate_empty_vulns(self):
        gen = self._make_gen()
        result = await gen.generate("/tmp/repo", [], mode="template")
        assert result["patches"] == []
        assert result["verified"] is True
        assert result["risk_reduction"] == 0


# ═══════════════════════════════════════════════════════════════════
# SECTION 6: DocumentationGenerator — PDF generation
# ═══════════════════════════════════════════════════════════════════

class TestDocumentationGenerator:

    @pytest.mark.asyncio
    async def test_generate_creates_pdf(self, tmp_path):
        from ouroboros.docs import DocumentationGenerator
        gen = DocumentationGenerator({})
        repo_path = str(tmp_path / "repo")
        os.makedirs(repo_path, exist_ok=True)

        fixes = {
            "patches": [
                {"vuln_id": "V1", "file_path": "a.py", "severity": "HIGH", "content": "fix"},
                {"vuln_id": "V2", "file_path": "b.py", "severity": "CRITICAL", "content": "fix2"},
            ],
            "risk_reduction": 75,
            "verified": True,
        }
        pdf_path = await gen.generate(repo_path, fixes)
        assert os.path.exists(pdf_path)
        assert pdf_path.endswith(".pdf")
        # PDF should have non-trivial size
        assert os.path.getsize(pdf_path) > 500

    @pytest.mark.asyncio
    async def test_generate_empty_patches(self, tmp_path):
        from ouroboros.docs import DocumentationGenerator
        gen = DocumentationGenerator({})
        repo_path = str(tmp_path / "repo")
        os.makedirs(repo_path, exist_ok=True)

        fixes = {"patches": [], "risk_reduction": 0, "verified": True}
        pdf_path = await gen.generate(repo_path, fixes)
        assert os.path.exists(pdf_path)

    @pytest.mark.asyncio
    async def test_pdf_output_path_correct(self, tmp_path):
        from ouroboros.docs import DocumentationGenerator
        gen = DocumentationGenerator({})
        repo_path = str(tmp_path / "myrepo")
        os.makedirs(repo_path, exist_ok=True)

        pdf_path = await gen.generate(
            repo_path, {"patches": [], "risk_reduction": 0, "verified": True}
        )
        assert "ouroboros-security-report.pdf" in pdf_path
        assert str(tmp_path) in pdf_path


# ═══════════════════════════════════════════════════════════════════
# SECTION 7: ContinuousScanner
# ═══════════════════════════════════════════════════════════════════

class TestContinuousScanner:

    def test_init(self):
        from ouroboros.continuous import ContinuousScanner
        mock_sdk = MagicMock()
        scanner = ContinuousScanner(mock_sdk, "https://github.com/a/b", 60)
        assert scanner.repo_url == "https://github.com/a/b"
        assert scanner.interval_seconds == 60
        assert scanner.sdk is mock_sdk

    def test_default_interval(self):
        from ouroboros.continuous import ContinuousScanner
        scanner = ContinuousScanner(MagicMock(), "url")
        assert scanner.interval_seconds == 300

    @pytest.mark.asyncio
    async def test_start_runs_scan_then_sleeps(self):
        from ouroboros.continuous import ContinuousScanner
        mock_sdk = MagicMock()
        mock_sdk.scan = AsyncMock(return_value={
            "vulnerabilities_found": 2,
            "pr_url": "https://github.com/a/b/pull/1",
            "fixes_generated": 1,
        })

        scanner = ContinuousScanner(mock_sdk, "https://github.com/a/b", 1)

        # Run for one iteration then break
        call_count = 0
        original_sleep = asyncio.sleep

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                raise KeyboardInterrupt()

        with patch("ouroboros.continuous.asyncio.sleep", side_effect=mock_sleep):
            # ContinuousScanner catches KeyboardInterrupt inside the loop
            # but asyncio.sleep raising it will propagate
            try:
                await scanner.start()
            except KeyboardInterrupt:
                pass

        mock_sdk.scan.assert_called_once_with("https://github.com/a/b")


# ═══════════════════════════════════════════════════════════════════
# SECTION 8: CLI (Click) tests
# ═══════════════════════════════════════════════════════════════════

class TestCLI:

    def test_cli_help(self):
        from click.testing import CliRunner
        from ouroboros.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Ouroboros" in result.output
        assert "scan" in result.output
        assert "watch" in result.output
        assert "info" in result.output

    def test_scan_help(self):
        from click.testing import CliRunner
        from ouroboros.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["scan", "--help"])
        assert result.exit_code == 0
        assert "--repo" in result.output
        assert "--config" in result.output
        assert "--profile" in result.output
        assert "--no-pr" in result.output
        assert "--json-output" in result.output

    def test_watch_help(self):
        from click.testing import CliRunner
        from ouroboros.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["watch", "--help"])
        assert result.exit_code == 0
        assert "--repo" in result.output
        assert "--interval" in result.output

    def test_info_command(self):
        from click.testing import CliRunner
        from ouroboros.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        assert "Ouroboros SDK" in result.output
        assert "v1.1.0" in result.output
        assert "Python" in result.output

    def test_scan_missing_config(self):
        from click.testing import CliRunner
        from ouroboros.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, [
            "scan", "--repo", "https://github.com/a/b",
            "--config", "/nonexistent/config.yaml",
        ])
        assert result.exit_code == 1
        assert "Config not found" in result.output or "❌" in result.output

    def test_scan_with_json_output(self, tmp_path):
        from click.testing import CliRunner
        from ouroboros.cli import cli

        cfg = tmp_path / "config.yaml"
        cfg.write_text('github:\n  token: "t"\n')

        fake_result = {
            "success": True,
            "vulnerabilities_found": 3,
            "critical_count": 1,
            "fixes_generated": 2,
            "risk_reduction_pct": 66,
            "pr_url": "https://github.com/a/b/pull/5",
            "docs_path": "/tmp/report.pdf",
            "scan_id": "SCAN-TEST",
            "verified_count": 2,
            "errors": [],
        }

        with patch("ouroboros.core.Ouroboros") as MockOuro:
            mock_instance = MagicMock()
            mock_instance.scan = AsyncMock(return_value=fake_result)
            MockOuro.return_value = mock_instance

            runner = CliRunner()
            result = runner.invoke(cli, [
                "scan", "-r", "https://github.com/a/b",
                "-c", str(cfg), "--json-output",
            ])

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["success"] is True
        assert parsed["vulnerabilities_found"] == 3

    def test_scan_text_output(self, tmp_path):
        from click.testing import CliRunner
        from ouroboros.cli import cli

        cfg = tmp_path / "config.yaml"
        cfg.write_text('github:\n  token: "t"\n')

        fake_result = {
            "success": True,
            "scan_id": "SCAN-X",
            "vulnerabilities_found": 5,
            "critical_count": 2,
            "fixes_generated": 4,
            "verified_count": 3,
            "risk_reduction_pct": 80,
            "pr_url": "https://github.com/a/b/pull/10",
            "docs_path": "/tmp/report.pdf",
            "errors": [],
        }

        with patch("ouroboros.core.Ouroboros") as MockOuro:
            mock_instance = MagicMock()
            mock_instance.scan = AsyncMock(return_value=fake_result)
            MockOuro.return_value = mock_instance

            runner = CliRunner()
            result = runner.invoke(cli, [
                "scan", "-r", "https://github.com/a/b", "-c", str(cfg),
            ])

        assert result.exit_code == 0
        assert "Scan complete" in result.output
        assert "5" in result.output       # vulns
        assert "80%" in result.output     # risk reduction
        assert "pull/10" in result.output # PR URL

    def test_version_flag(self):
        from click.testing import CliRunner
        from ouroboros.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.1.0" in result.output


# ═══════════════════════════════════════════════════════════════════
# SECTION 9: Integration — src.* modules importable from SDK
# ═══════════════════════════════════════════════════════════════════

class TestSrcIntegration:
    """Verify the SDK can import the existing src.* modules."""

    def test_import_workflow(self):
        from src.orchestration.workflow import OuroborosWorkflow
        assert OuroborosWorkflow is not None

    def test_import_red_agent(self):
        from src.agents import REDAgent
        assert REDAgent is not None

    def test_import_blue_agent(self):
        from src.agents import BLUEAgent
        assert BLUEAgent is not None

    def test_import_safety_gates(self):
        from src.security.safety_gates import SafetyGates
        assert SafetyGates is not None

    def test_import_verification_engine(self):
        from src.verification.verification_engine import VerificationEngine
        assert VerificationEngine is not None

    def test_import_github_client(self):
        from src.integrations.github_api import GitHubClient
        assert GitHubClient is not None

    def test_import_settings(self):
        from config.settings import Settings
        assert Settings is not None


# ═══════════════════════════════════════════════════════════════════
# SECTION 10: Templates exist and are valid Jinja2
# ═══════════════════════════════════════════════════════════════════

class TestTemplates:

    def test_templates_dir_exists(self):
        from ouroboros.fixes import TEMPLATES_DIR
        assert TEMPLATES_DIR.exists()

    def test_api_hardening_template_exists(self):
        from ouroboros.fixes import TEMPLATES_DIR
        assert (TEMPLATES_DIR / "api-hardening.patch.j2").exists()

    def test_docker_security_template_exists(self):
        from ouroboros.fixes import TEMPLATES_DIR
        assert (TEMPLATES_DIR / "docker-security.patch.j2").exists()

    def test_api_template_renders(self):
        from ouroboros.fixes import FixGenerator
        gen = FixGenerator({})
        tpl = gen.jinja_env.get_template("api-hardening.patch.j2")
        result = tpl.render(
            vuln={"id": "TEST-1", "severity": "HIGH", "description": "SQL injection"},
            file_path="app.py",
            file_content="cursor.execute(query)",
        )
        assert "TEST-1" in result
        assert "HIGH" in result

    def test_docker_template_renders(self):
        from ouroboros.fixes import FixGenerator
        gen = FixGenerator({})
        tpl = gen.jinja_env.get_template("docker-security.patch.j2")
        result = tpl.render(
            vuln={"id": "D-1", "severity": "MEDIUM"},
            file_path="Dockerfile",
            file_content="FROM python:latest\nUSER root",
        )
        assert "appuser" in result
        assert "non-root" in result


# ═══════════════════════════════════════════════════════════════════
# SECTION 11: Edge cases & error handling
# ═══════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_config_with_only_github_section(self, tmp_path):
        from ouroboros.core import Ouroboros
        cfg = tmp_path / "cfg.yaml"
        cfg.write_text('github:\n  token: "x"\n')
        ouro = Ouroboros(str(cfg))
        # Should not crash even without ollama/database sections
        assert ouro.config["github"]["token"] == "x"

    def test_config_with_all_sections(self, tmp_path):
        from ouroboros.core import Ouroboros
        cfg = tmp_path / "cfg.yaml"
        cfg.write_text(
            'github:\n  token: "t"\n'
            'ollama:\n  url: "http://localhost:11434"\n'
            'database:\n  url: "postgresql://localhost/db"\n'
            'redis:\n  url: "redis://localhost:6379"\n'
        )
        ouro = Ouroboros(str(cfg))
        assert ouro.config["ollama"]["url"] == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_scan_propagates_workflow_errors(self):
        from ouroboros.core import Ouroboros
        ouro = Ouroboros.__new__(Ouroboros)
        ouro.config = {"github": {"token": "t"}}
        ouro._workflow = MagicMock()
        ouro._workflow.run = AsyncMock(side_effect=RuntimeError("boom"))
        ouro._gh_client = None

        with pytest.raises(RuntimeError, match="boom"):
            await ouro.scan("https://github.com/a/b")

    def test_build_summary_missing_optional_fields(self):
        """State dict with minimal fields should not crash."""
        from ouroboros.core import Ouroboros
        ouro = Ouroboros.__new__(Ouroboros)
        ouro.config = {}
        ouro._workflow = None
        ouro._gh_client = None

        # Minimal state — many fields missing
        state = {}
        s = ouro._build_summary("url", state)
        assert s["success"] is True  # workflow_aborted defaults to False
        assert s["vulnerabilities_found"] == 0
        assert s["fixes_generated"] == 0

    @pytest.mark.asyncio
    async def test_fix_generator_template_graceful_on_bad_template(self):
        """If template rendering fails, should skip gracefully."""
        from ouroboros.fixes import FixGenerator
        gen = FixGenerator({})
        # Force a bad template lookup
        gen._pick_template = lambda v: "nonexistent.j2"
        vulns = [{"id": "X", "description": "test", "file": "f.py"}]
        result = await gen.generate("/tmp", vulns, mode="template")
        assert result["patches"] == []  # graceful failure


# ═══════════════════════════════════════════════════════════════════
# SECTION 12: Build artifacts check
# ═══════════════════════════════════════════════════════════════════

class TestBuildArtifacts:

    def test_wheel_exists(self):
        wheel = Path(__file__).parent.parent / "dist" / "ouroboros_sdk-1.1.0-py3-none-any.whl"
        assert wheel.exists(), f"Wheel not found at {wheel}"

    def test_sdist_exists(self):
        sdist = Path(__file__).parent.parent / "dist" / "ouroboros_sdk-1.1.0.tar.gz"
        assert sdist.exists(), f"Sdist not found at {sdist}"

    def test_pyproject_exists(self):
        assert (Path(__file__).parent.parent / "pyproject.toml").exists()

    def test_config_example_exists(self):
        assert (Path(__file__).parent.parent / "config.example.yaml").exists()

    def test_examples_demo_exists(self):
        assert (Path(__file__).parent.parent / "examples" / "demo.py").exists()
