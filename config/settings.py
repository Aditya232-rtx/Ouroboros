"""
Ouroboros AI - Global Settings
"""

from typing import Dict
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Global application settings"""
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )
    
    # Application
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    
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
    redis_url: str = "redis://localhost:6379/0"
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
    secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600
    
    # Models
    models_dir: Path = Path("./models")
    gpu_layers: int = 25
    n_ctx: int = 4096
    n_threads: int = 8

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    api_keys: Dict[str, str] = {}
    
    # Paths
    semgrep_rules: str = "p/security-audit"
    
settings = Settings()
