"""
Ouroboros AI - Structured Logging Setup
Configures logging for the entire application
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from config.settings import settings


def setup_logging():
    """
    Configure structured logging for Ouroboros AI
    """
    # Create logs directory if it doesn't exist
    log_file = settings.log_file
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO if not settings.debug else logging.DEBUG)
    console_handler.setFormatter(simple_formatter)
    
    # File handler (rotating)
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Log startup
    logger.info("=" * 80)
    logger.info(f"Ouroboros AI v{settings.app_version} - Logging initialized")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 80)
    
    return logger


# Initialize logging on import
setup_logging()
