"""
Ouroboros AI - Global Settings
Loads configuration from environment variables
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Global application settings"""
    
    # Application
    app_name: str = "ouroboros-ai"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # Models
    models_dir: Path = Path("./models")
    red_agent_model: str = "WhiteRabbitNeo-7B-v1.5a-Q4_K_M.gguf"
    blue_agent_model: str = "DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
    support_agent_model: str = "Phi-3.5-mini-instruct-Q6_K.gguf"
    
    # Model Configuration
    gpu_layers: int = 35
    n_ctx: int = 4096
    n_threads: int = 8
    
    # GitHub
    github_token: Optional[str] = None
    github_webhook_secret: Optional[str] = None
    
    # Google Workspace
    google_service_account_file: Optional[Path] = None
    google_docs_folder_id: Optional[str] = None
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/ouroboros"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600
    
    # ImmuDB
    immudb_host: str = "localhost"
    immudb_port: int = 3322
    immudb_username: str = "immudb"
    immudb_password: str = "immudb"
    immudb_database: str = "ouroboros_audit"
    
    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    
    # OPA
    opa_url: str = "http://localhost:8181"
    opa_policy_dir: Path = Path("./config/opa_policies")
    
    # Docker
    docker_network: str = "ouroboros_network"
    docker_sandbox_image: str = "ouroboros-sandbox:latest"
    
    # Security
    secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600
    
    # Scanning Tools
    nuclei_templates_dir: Path = Path("./nuclei-templates")
    semgrep_rules: str = "p/security-audit,p/owasp-top-10"
    checkov_framework: str = "all"
    
    # Monitoring
    prometheus_port: int = 9090
    grafana_port: int = 3000
    
    # Logging
    log_level: str = "INFO"
    log_file: Path = Path("./logs/ouroboros.log")
    log_max_bytes: int = 10485760  # 10MB
    log_backup_count: int = 5
    
    # Performance
    max_workers: int = 4
    timeout_scan: int = 300
    timeout_fix: int = 600
    max_verification_retries: int = 10
    
    # Compliance
    compliance_frameworks: str = "SOC2,ISO27001,GDPR,HIPAA,PCI-DSS"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
