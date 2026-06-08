"""
Ouroboros AI - Global Settings
Loads configuration from environment variables and AWS Secrets Manager
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


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
    
    # TEMPORARY: Smaller models for testing (total ~7.2 GB)
    red_agent_model: str = "Qwen2.5-Coder-3B-Instruct-abliterated-Q4_K_M.gguf"  # ~2.4 GB
    blue_agent_model: str = "deepseek-coder-1.3b-instruct.Q6_K.gguf"  # ~2.2 GB
    support_agent_model: str = "Phi-3-mini-4k-instruct-q4.gguf"  # ~2.6 GB
    
    # PRODUCTION: Full models (commented out for GPU constraints)
    # red_agent_model: str = "WhiteRabbitNeo-7B-v1.5a-Q4_K_M.gguf"  # ~4.5 GB
    # blue_agent_model: str = "DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"  # ~4.8 GB
    # support_agent_model: str = "Phi-3.5-mini-instruct-Q6_K.gguf"  # ~3.2 GB
    
    # Model Configuration
    gpu_layers: int = 25  # Reduced for smaller models
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

    def load_secrets_from_aws(self):
        """
        Load secrets from AWS Secrets Manager (production).
        Per 03_CRITICAL_DO_NOT_FILE: ZERO secrets in code.
        
        This method attempts to load secrets from AWS Secrets Manager.
        Falls back to environment variables for local development.
        """
        if self.environment == "local_dev_no_aws":
            # Skip AWS for local development without credentials
            logger.info("Skipping AWS Secrets Manager (local dev mode)")
            return

        try:
            import boto3
            import json
            
            client = boto3.client("secretsmanager", region_name=self.aws_region)
            secret_name = "ouroboros/app-secrets"
            
            response = client.get_secret_value(SecretId=secret_name)
            
            if "SecretString" in response:
                secrets = json.loads(response["SecretString"])
                
                # Update settings with secrets
                self.github_token = secrets.get("GITHUB_TOKEN", self.github_token)
                self.github_webhook_secret = secrets.get("GITHUB_WEBHOOK_SECRET", self.github_webhook_secret)
                self.immudb_password = secrets.get("IMMUDB_PASSWORD", self.immudb_password)
                self.secret_key = secrets.get("SECRET_KEY", self.secret_key)
                
                logger.info("Successfully loaded secrets from AWS Secrets Manager")
        except Exception as e:
            logger.warning(f"Failed to load AWS secrets: {e}. Using environment variables.")


# Global settings instance
settings = Settings()

# Attempt to load secrets on initialization (production)
if settings.environment in ["production", "staging"]:
    settings.load_secrets_from_aws()
