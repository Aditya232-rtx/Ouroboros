"""
Ouroboros AI - Global Settings
"""

from typing import Dict
from pathlib import Path
from datetime import timezone, datetime
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

class Settings(BaseSettings):
    """Global application settings"""
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )
    
    # Application
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    
    # Logging
    log_level: str = "INFO"
    log_file: Path = Path("logs/app.log")
    log_max_bytes: int = 10485760  # 10MB
    log_backup_count: int = 5

    # Database
    database_url: str = "postgresql://ouroboros_user:postgres@localhost:5432/ouroboros"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Redis
    redis_url: str = "redis://:rediss@localhost:6379/0"
    redis_cache_ttl: int = 3600

    # GitHub Integration
    github_token: str = ""
    github_webhook_secret: str = ""
    
    # Google Workspace
    google_service_account_file: str = ""
    google_docs_folder_id: str = ""

    # immudb
    immudb_host: str = "localhost"
    immudb_port: int = 3322
    immudb_username: str = "immudb"
    immudb_password: str = "immudb"
    immudb_database: str = "ouroboros_audit"

    # OPA
    opa_url: str = "http://localhost:8181"
    opa_policy_dir: Path = Path("./config/opa_policies")

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    
    # Security
    secret_key: str = ""
    jwt_secret_key: str = ""  # Alias resolved from secret_key
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600
    
    # Models
    models_dir: Path = Path("./models")
    gpu_layers: int = 25
    n_ctx: int = 4096
    n_threads: int = 8

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_reload: bool = True
    api_keys: Dict[str, str] = {}
    
    # Paths
    semgrep_rules: str = "p/security-audit"
    
    # Jira MCP integration example
    mcp: Dict[str, Dict[str, str]] = {
        'jira': {
            'api_key': 'ATATT3xFfGF0PIyuBtEyDVjEe_ewuYeijWQdY_RvF8Bwn8f1h-QFsndxEg1-Lwh0Sh87yQEyfdaCF3Ejv_EaNGsibLp9bvU0QeVMyhx5YZgQ9RLjvB9QEgmdzqNA9Rwm6cB7Mah7Dm2Slh0dkAszwgi7ASowyI1wHVH0zBpCY_BIO275BtFQGXM=16E53A04',
            'url': 'https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3'
        }
    }

    @model_validator(mode="after")
    def validate_critical_settings(self):
        """Validate that critical settings are not defaults."""
        insecure_secrets = [
            "your-secret-key-change-in-production",
            "dev-secret-key-change-in-production",
            "",
        ]
        if self.secret_key in insecure_secrets:
            if self.environment == "production":
                raise ValueError(
                    "SECRET_KEY must be set to a secure random value in production! "
                    "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
                )
            else:
                import logging
                logging.getLogger(__name__).warning(
                    "⚠️  SECRET_KEY is not set — using insecure default for development only!"
                )
                self.secret_key = "dev-only-insecure-key-do-not-use-in-production"
        
        # Sync jwt_secret_key from secret_key
        if not self.jwt_secret_key:
            self.jwt_secret_key = self.secret_key
        
        if self.immudb_password == "immudb" and self.environment == "production":
            raise ValueError("IMMUDB_PASSWORD must be changed from default in production!")

        return self
    
settings = Settings()
