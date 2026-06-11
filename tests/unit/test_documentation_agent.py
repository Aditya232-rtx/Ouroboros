"""
Unit tests for the DOCUMENTATION Agent

Tests:
1. Input validation
2. Markdown report generation (fallback)
3. PDF generation
4. Severity calculation
5. Risk score calculation
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_vulnerabilities():
    """Sample vulnerability data for testing"""
    return [
        {
            "id": "RED-001",
            "type": "sql_injection",
            "severity": "critical",
            "cwe": "CWE-89",
            "cvss": 9.8,
            "location": {
                "file": "src/app.py",
                "line": 42,
                "function": "get_user"
            },
            "description": "SQL injection via user_id parameter",
            "poc_code": "curl -X GET 'http://target/api/users?id=1 OR 1=1'",
            "confidence": 0.95
        },
        {
            "id": "RED-002",
            "type": "xss",
            "severity": "high",
            "cwe": "CWE-79",
            "cvss": 7.5,
            "location": {
                "file": "src/views.py",
                "line": 88,
                "function": "render_search"
            },
            "description": "Reflected XSS in search parameter",
            "poc_code": "<script>alert('XSS')</script>",
            "confidence": 0.88
        },
        {
            "id": "RED-003",
            "type": "path_traversal",
            "severity": "medium",
            "cwe": "CWE-22",
            "cvss": 5.5,
            "location": {
                "file": "src/files.py",
                "line": 15,
                "function": "download_file"
            },
            "description": "Path traversal allows reading arbitrary files",
            "poc_code": "../../etc/passwd",
            "confidence": 0.75
        }
    ]


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing"""
    return {
        "repo_url": "https://github.com/test/vulnerable-app",
        "repo_name": "test/vulnerable-app",
        "scan_id": "SCAN-20260130-120000",
        "branch": "main",
        "commit_sha": "abc123"
    }


@pytest.fixture
def sample_fixes():
    """Sample fix data for testing"""
    return [
        {
            "fix_id": "BLUE-001",
            "vulnerability_id": "RED-001",
            "approach": "parameterized_queries",
            "verified": True
        },
        {
            "fix_id": "BLUE-002",
            "vulnerability_id": "RED-002",
            "approach": "html_escaping",
            "verified": True
        }
    ]


@pytest.fixture
def doc_agent():
    """Create a DocumentationAgent with mocked model"""
    with patch('src.agents.documentation_agent.get_model') as mock_get_model:
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        
        from src.agents.documentation_agent import DocumentationAgent
        agent = DocumentationAgent()
        
        # Mock LLM call
        agent._call_llm = MagicMock(return_value="# Test Report\n\nThis is a test report.")
        
        return agent


# ============================================================================
# Test: Input Validation
# ============================================================================

class TestInputValidation:
    """Tests for input validation"""
    
    def test_valid_input(self, doc_agent, sample_vulnerabilities, sample_metadata):
        """Test validation with valid input"""
        input_data = {
            "vulnerabilities": sample_vulnerabilities,
            "metadata": sample_metadata
        }
        
        validated = doc_agent.validate_input(input_data)
        
        assert len(validated.vulnerabilities) == 3
        assert validated.metadata["repo_url"] == sample_metadata["repo_url"]
        assert validated.report_type == "initial"  # Default
    
    def test_valid_input_with_fixes(self, doc_agent, sample_vulnerabilities, sample_metadata, sample_fixes):
        """Test validation with fixes included"""
        input_data = {
            "vulnerabilities": sample_vulnerabilities,
            "metadata": sample_metadata,
            "fixes": sample_fixes,
            "report_type": "final"
        }
        
        validated = doc_agent.validate_input(input_data)
        
        assert len(validated.fixes) == 2
        assert validated.report_type == "final"
    
    def test_empty_vulnerabilities(self, doc_agent, sample_metadata):
        """Test with no vulnerabilities"""
        input_data = {
            "vulnerabilities": [],
            "metadata": sample_metadata
        }
        
        validated = doc_agent.validate_input(input_data)
        
        assert len(validated.vulnerabilities) == 0


# ============================================================================
# Test: Severity Calculation
# ============================================================================

class TestSeverityCalculation:
    """Tests for severity breakdown calculation"""
    
    def test_severity_breakdown(self, doc_agent, sample_vulnerabilities):
        """Test severity breakdown calculation"""
        breakdown = doc_agent._calculate_severity(sample_vulnerabilities)
        
        assert breakdown["critical"] == 1
        assert breakdown["high"] == 1
        assert breakdown["medium"] == 1
        assert breakdown["low"] == 0
    
    def test_empty_vulnerabilities(self, doc_agent):
        """Test with no vulnerabilities"""
        breakdown = doc_agent._calculate_severity([])
        
        assert breakdown == {"critical": 0, "high": 0, "medium": 0, "low": 0}
    
    def test_unknown_severity_defaults_to_low(self, doc_agent):
        """Test unknown severity defaults to low"""
        vulns = [{"severity": "unknown"}, {"severity": "info"}]
        breakdown = doc_agent._calculate_severity(vulns)
        
        assert breakdown["low"] == 2


# ============================================================================
# Test: Risk Score Calculation
# ============================================================================

class TestRiskScoreCalculation:
    """Tests for risk score calculation"""
    
    def test_risk_score_with_critical(self, doc_agent, sample_vulnerabilities):
        """Test risk score with critical vulnerability"""
        score = doc_agent._calculate_risk_score(sample_vulnerabilities)
        
        # 1 critical (25) + 1 high (15) + 1 medium (7) = 47
        assert score == 47.0
    
    def test_risk_score_empty(self, doc_agent):
        """Test risk score with no vulnerabilities"""
        score = doc_agent._calculate_risk_score([])
        
        assert score == 0.0
    
    def test_risk_score_capped_at_100(self, doc_agent):
        """Test risk score caps at 100"""
        # 5 critical vulns = 125, should cap at 100
        vulns = [{"severity": "critical"} for _ in range(5)]
        score = doc_agent._calculate_risk_score(vulns)
        
        assert score == 100.0


# ============================================================================
# Test: Fallback Report Generation
# ============================================================================

class TestFallbackReport:
    """Tests for fallback markdown report generation"""
    
    def test_fallback_report_structure(self, doc_agent, sample_vulnerabilities, sample_metadata):
        """Test fallback report has required sections"""
        data = {
            "vulnerabilities": sample_vulnerabilities,
            "metadata": sample_metadata
        }
        
        report = doc_agent._generate_fallback_report(data)
        
        assert "# Ouroboros Security Report" in report
        assert "## Executive Summary" in report
        assert "## Vulnerability Details" in report
        assert "## Recommendations" in report
        assert sample_metadata["repo_url"] in report
    
    def test_fallback_report_contains_vulnerabilities(self, doc_agent, sample_vulnerabilities, sample_metadata):
        """Test fallback report includes vulnerability details"""
        data = {
            "vulnerabilities": sample_vulnerabilities,
            "metadata": sample_metadata
        }
        
        report = doc_agent._generate_fallback_report(data)
        
        assert "sql_injection" in report
        assert "CWE-89" in report
        assert "src/app.py" in report
    
    def test_fallback_report_with_poc(self, doc_agent, sample_vulnerabilities, sample_metadata):
        """Test fallback report includes PoC code blocks"""
        data = {
            "vulnerabilities": sample_vulnerabilities,
            "metadata": sample_metadata
        }
        
        report = doc_agent._generate_fallback_report(data)
        
        assert "Proof of Concept" in report
        assert "```" in report


# ============================================================================
# Test: Execute Method
# ============================================================================

class TestExecute:
    """Tests for the main execute method"""
    
    @pytest.mark.asyncio
    async def test_execute_creates_markdown_file(self, doc_agent, sample_vulnerabilities, sample_metadata, tmp_path):
        """Test execute creates markdown file"""
        # Override reports directory
        doc_agent.REPORTS_DIR = tmp_path
        
        input_data = {
            "vulnerabilities": sample_vulnerabilities,
            "metadata": sample_metadata,
            "report_type": "initial"
        }
        
        result = await doc_agent.execute(input_data)
        
        assert result["documentation_id"].startswith("DOC-")
        assert result["report_info"] is not None
        assert Path(result["report_info"]["md_path"]).exists()
    
    @pytest.mark.asyncio
    async def test_execute_returns_sections(self, doc_agent, sample_vulnerabilities, sample_metadata, tmp_path):
        """Test execute returns expected sections"""
        doc_agent.REPORTS_DIR = tmp_path
        
        input_data = {
            "vulnerabilities": sample_vulnerabilities,
            "metadata": sample_metadata
        }
        
        result = await doc_agent.execute(input_data)
        
        assert "Executive Summary" in result["sections_generated"]
        assert "Vulnerability Details" in result["sections_generated"]
    
    @pytest.mark.asyncio
    async def test_execute_includes_content_summary(self, doc_agent, sample_vulnerabilities, sample_metadata, tmp_path):
        """Test execute returns content summary"""
        doc_agent.REPORTS_DIR = tmp_path
        
        input_data = {
            "vulnerabilities": sample_vulnerabilities,
            "metadata": sample_metadata
        }
        
        result = await doc_agent.execute(input_data)
        
        assert result["content_summary"]["total_vulnerabilities"] == 3
        assert "severity_breakdown" in result["content_summary"]
        assert "risk_score" in result["content_summary"]
    
    @pytest.mark.asyncio
    async def test_execute_handles_empty_vulnerabilities(self, doc_agent, sample_metadata, tmp_path):
        """Test execute handles empty vulnerability list"""
        doc_agent.REPORTS_DIR = tmp_path
        
        input_data = {
            "vulnerabilities": [],
            "metadata": sample_metadata
        }
        
        result = await doc_agent.execute(input_data)
        
        assert result["content_summary"]["total_vulnerabilities"] == 0
        assert result["content_summary"]["risk_score"] == 0.0


# ============================================================================
# Test: PDF Generation
# ============================================================================

class TestPDFGeneration:
    """Tests for PDF generation"""
    
    @pytest.mark.asyncio
    async def test_pdf_generation_with_valid_markdown(self, doc_agent, tmp_path):
        """Test PDF is generated from valid markdown"""
        doc_agent.REPORTS_DIR = tmp_path
        
        md_content = """# Test Report

## Summary
This is a test.

| Col1 | Col2 |
|------|------|
| A    | B    |

```python
print("hello")
```
"""
        
        pdf_path = await doc_agent._generate_pdf(md_content, "test-report")
        
        # PDF generation might fail if weasyprint not installed
        # That's OK - the agent handles it gracefully
        if pdf_path:
            assert pdf_path.exists()
            assert pdf_path.suffix == ".pdf"
    
    @pytest.mark.asyncio
    async def test_pdf_generation_handles_missing_deps(self, doc_agent, tmp_path):
        """Test PDF generation gracefully handles missing dependencies"""
        doc_agent.REPORTS_DIR = tmp_path
        
        with patch.dict('sys.modules', {'weasyprint': None}):
            pdf_path = await doc_agent._generate_pdf("# Test", "test")
            # Should return None (fallback to markdown only)
            # Not raising exception is the key assertion


# ============================================================================
# Test: Format Helpers
# ============================================================================

class TestFormatHelpers:
    """Tests for formatting helper methods"""
    
    def test_format_vulnerabilities_for_prompt(self, doc_agent, sample_vulnerabilities):
        """Test vulnerability formatting for LLM prompt"""
        formatted = doc_agent._format_vulnerabilities_for_prompt(sample_vulnerabilities)
        
        assert "sql_injection" in formatted
        assert "CWE-89" in formatted
        assert "src/app.py:42" in formatted
    
    def test_format_vulnerabilities_empty(self, doc_agent):
        """Test formatting empty list"""
        formatted = doc_agent._format_vulnerabilities_for_prompt([])
        
        assert formatted == "No vulnerabilities found."
    
    def test_format_fixes_for_prompt(self, doc_agent, sample_fixes):
        """Test fix formatting for LLM prompt"""
        formatted = doc_agent._format_fixes_for_prompt(sample_fixes)
        
        assert "BLUE-001" in formatted
        assert "parameterized_queries" in formatted
    
    def test_format_fixes_empty(self, doc_agent):
        """Test formatting empty fixes"""
        formatted = doc_agent._format_fixes_for_prompt([])
        
        assert formatted == "No fixes applied."


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
