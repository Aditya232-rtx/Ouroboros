# config/security_configs.py
"""
Security configuration for Ouroboros AI.

Per 03_CRITICAL_DO_NOT_FILE: Comprehensive security settings for
safety gates, sandbox restrictions, and compliance requirements.
"""

from typing import Dict, List, Set
from pydantic import BaseModel, Field


class SafetyGateConfig(BaseModel):
    """Configuration for the 5-layer safety gates."""
    
    # Gate 1: Input Validation
    max_input_size_bytes: int = 10_000_000  # 10MB
    allowed_file_extensions: Set[str] = {".py", ".js", ".ts", ".java", ".go", ".rb", ".rs", ".c", ".cpp", ".h"}
    forbidden_patterns: List[str] = [
        r"eval\s*\(",
        r"exec\s*\(",
        r"os\.system\s*\(",
        r"subprocess\.call\s*.*shell\s*=\s*True",
        r"__import__\s*\(",
    ]
    
    # Gate 2: No New Vulnerabilities
    semgrep_rules: List[str] = [
        "p/security-audit",
        "p/owasp-top-10",
        "p/r2c-ci",
    ]
    max_allowed_findings: int = 0  # Zero tolerance for new vulns
    
    # Gate 3: Backward Compatibility
    require_passing_tests: bool = True
    allowed_test_failures: int = 0
    test_timeout_seconds: int = 300
    
    # Gate 4: Performance
    max_performance_degradation_percent: float = 10.0
    max_memory_increase_mb: int = 100
    max_cpu_increase_percent: float = 20.0
    
    # Gate 5: Test Coverage
    min_coverage_percent: float = 80.0
    require_new_tests: bool = True


class SandboxConfig(BaseModel):
    """Docker sandbox security configuration."""
    
    # Network isolation
    network_disabled: bool = True
    
    # Filesystem restrictions
    read_only: bool = True
    allowed_write_paths: List[str] = ["/tmp", "/var/tmp"]
    
    # Resource limits
    memory_limit: str = "512m"
    cpu_quota: int = 50000  # 50% of one CPU
    cpu_period: int = 100000
    pids_limit: int = 100
    
    # Security options
    privileged: bool = False
    cap_drop: List[str] = ["ALL"]
    cap_add: List[str] = []
    security_opt: List[str] = ["no-new-privileges:true"]
    
    # Execution limits
    timeout_seconds: int = 30
    max_output_size_bytes: int = 1_000_000  # 1MB
    
    # Cleanup
    auto_remove: bool = True


class DangerousPatternConfig(BaseModel):
    """Patterns that must NEVER appear in generated fixes."""
    
    # Per 03_CRITICAL_DO_NOT lines 45-80
    forbidden_code_patterns: Dict[str, str] = {
        r"shell\s*=\s*True": "Shell injection risk - use subprocess with list args",
        r"eval\s*\(": "Code injection risk - never use eval",
        r"exec\s*\(": "Code injection risk - never use exec",
        r"os\.system\s*\(": "Shell injection risk - use subprocess.run",
        r"pickle\.loads?\s*\(": "Deserialization risk - use safe alternatives",
        r"yaml\.load\s*\([^,]+\)": "YAML injection - use yaml.safe_load",
        r"xml\.etree\.ElementTree\.fromstring": "XXE risk - use defusedxml",
        r"request\.get\s*\(\s*[\"'][^\"']+{": "SSRF risk - validate URLs",
        r"cursor\.execute\s*\([^,]+%[^,]+,": "SQL injection - use parameterized queries",
        r"verify\s*=\s*False": "SSL bypass - never disable verification",
        r"password\s*=\s*[\"'][^\"']+[\"']": "Hardcoded credential - use secrets manager",
        r"api_key\s*=\s*[\"'][^\"']+[\"']": "Hardcoded credential - use secrets manager",
        r"secret\s*=\s*[\"'][^\"']+[\"']": "Hardcoded credential - use secrets manager",
    }
    
    # Patterns that should trigger extra review
    suspicious_patterns: Dict[str, str] = {
        r"base64\.decode": "Possible obfuscation",
        r"urllib\.request\.urlopen": "External request - verify URL validation",
        r"socket\.connect": "Direct socket - verify security",
        r"ctypes\.": "Native code access - verify necessity",
        r"importlib\.import_module": "Dynamic import - verify source",
    }


class ComplianceConfig(BaseModel):
    """Compliance framework configurations."""
    
    # Enabled frameworks
    enabled_frameworks: List[str] = [
        "SOC2",
        "ISO27001",
        "GDPR",
        "HIPAA",
        "PCI-DSS",
    ]
    
    # Framework-specific requirements
    soc2_controls: List[str] = ["CC6.1", "CC6.6", "CC6.7", "CC7.1", "CC7.2"]
    iso27001_controls: List[str] = ["A.12.6.1", "A.14.2.1", "A.14.2.5"]
    gdpr_requirements: List[str] = ["Art.25", "Art.32", "Art.35"]
    hipaa_requirements: List[str] = ["164.312(a)", "164.312(c)", "164.312(e)"]
    pci_dss_requirements: List[str] = ["6.3", "6.5", "6.6", "11.3"]
    
    # Audit retention
    audit_retention_days: int = 2555  # 7 years for most frameworks


class RateLimitConfig(BaseModel):
    """API rate limiting configuration."""
    
    # Per-API-key limits
    authenticated_requests_per_minute: int = 100
    authenticated_scans_per_hour: int = 10
    
    # Unauthenticated limits
    unauthenticated_requests_per_minute: int = 10
    
    # Burst allowance
    burst_multiplier: float = 1.5


class SecurityConfig(BaseModel):
    """Master security configuration."""
    
    safety_gates: SafetyGateConfig = SafetyGateConfig()
    sandbox: SandboxConfig = SandboxConfig()
    dangerous_patterns: DangerousPatternConfig = DangerousPatternConfig()
    compliance: ComplianceConfig = ComplianceConfig()
    rate_limits: RateLimitConfig = RateLimitConfig()
    
    # V1 Restrictions per 03_CRITICAL_DO_NOT
    allow_auto_merge: bool = False  # MUST be False for V1
    min_human_reviewers: int = 2
    require_two_factor_auth: bool = True
    
    # Kill switch
    emergency_stop_enabled: bool = True
    max_fixes_per_run: int = 10
    max_verification_retries: int = 10


# Global security configuration instance
security_config = SecurityConfig()


def get_security_config() -> SecurityConfig:
    """Get the security configuration."""
    return security_config


def get_safety_gates_config() -> SafetyGateConfig:
    """Get safety gates configuration."""
    return security_config.safety_gates


def get_sandbox_config() -> SandboxConfig:
    """Get sandbox configuration."""
    return security_config.sandbox


def get_dangerous_patterns() -> DangerousPatternConfig:
    """Get dangerous patterns configuration."""
    return security_config.dangerous_patterns


__all__ = [
    "SecurityConfig",
    "SafetyGateConfig",
    "SandboxConfig",
    "DangerousPatternConfig",
    "ComplianceConfig",
    "RateLimitConfig",
    "security_config",
    "get_security_config",
    "get_safety_gates_config",
    "get_sandbox_config",
    "get_dangerous_patterns",
]
