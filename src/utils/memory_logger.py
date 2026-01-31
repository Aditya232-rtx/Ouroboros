import logging
from datetime import datetime
from typing import List

class ScanLogHandler(logging.Handler):
    """
    Custom logging handler to capture logs into an in-memory list
    for a specific scan.
    """
    def __init__(self, logs_list: List[dict]):
        super().__init__()
        self.logs_list = logs_list
        # Set a formatter that includes the logger name as 'source'
        self.setFormatter(logging.Formatter('%(message)s'))

    def emit(self, record):
        try:
            # Map standard python log levels to our frontend levels
            level_map = {
                logging.DEBUG: "debug",
                logging.INFO: "info",
                logging.WARNING: "warning",
                logging.ERROR: "error",
                logging.CRITICAL: "error"
            }
            
            # Determine source based on logger name
            # e.g., src.agents.red_agent -> RED_AGENT
            # or agent.RED -> RED_AGENT (BaseAgent convention)
            name = record.name.lower()
            source = "SYSTEM"
            
            if "red" in name and "agent" in name:
                source = "RED_AGENT"
            elif "blue" in name and "agent" in name:
                source = "BLUE_AGENT"
            
            # Expanded Mapping for Helper Modules
            elif "security.tools" in name or "exploitation" in name or "pentest" in name:
                source = "RED_AGENT"
            elif "safety_gates" in name:
                source = "BLUE_AGENT"

            elif "governance" in name:
                source = "GOVERNANCE"
            elif "audit" in name:
                source = "AUDIT"
            elif "doc" in name and "agent" in name:
                source = "DOCUMENTATION"
            elif "orchestrator" in name or "workflow" in name:
                source = "ORCHESTRATOR"
            
            log_entry = {
                "id": f"{record.created}",
                "timestamp": datetime.fromtimestamp(record.created).strftime('%H:%M:%S'),
                "level": level_map.get(record.levelno, "info"),
                "source": source,
                "message": record.getMessage()
            }
            
            self.logs_list.append(log_entry)
            
        except Exception:
            self.handleError(record)


import json
from src.database.redis import get_redis_client

class RedisScanLogHandler(logging.Handler):
    """
    Logging handler to push logs to a Redis list for a specific scan.
    """
    def __init__(self, scan_id: str):
        super().__init__()
        self.scan_id = scan_id
        self.redis = get_redis_client()
        self.redis_key = f"scan:{scan_id}:logs"
        self.setFormatter(logging.Formatter('%(message)s'))

    def emit(self, record):
        try:
            level_map = {
                logging.DEBUG: "debug",
                logging.INFO: "info",
                logging.WARNING: "warning",
                logging.ERROR: "error",
                logging.CRITICAL: "error"
            }
            
            name = record.name.lower()
            source = "SYSTEM"
            
            if "red" in name and "agent" in name: source = "RED_AGENT"
            elif "blue" in name and "agent" in name: source = "BLUE_AGENT"
            
            # Expanded Mapping for Helper Modules
            elif "security.tools" in name or "exploitation" in name or "pentest" in name: source = "RED_AGENT"
            elif "safety_gates" in name: source = "BLUE_AGENT"
            
            elif "governance" in name: source = "GOVERNANCE"
            elif "audit" in name: source = "AUDIT"
            elif "doc" in name and "agent" in name: source = "DOCUMENTATION"
            elif "orchestrator" in name or "workflow" in name: source = "ORCHESTRATOR"
            
            log_entry = {
                "id": str(record.created),
                "timestamp": datetime.fromtimestamp(record.created).strftime('%H:%M:%S'),
                "level": level_map.get(record.levelno, "info"),
                "source": source,
                "message": record.getMessage()
            }
            
            # Push to Redis List (Right Push)
            self.redis.rpush(self.redis_key, json.dumps(log_entry))
            
            # Optional: Set expiry on key update (e.g. 24 hours) to prevent stale data
            self.redis.expire(self.redis_key, 86400)
            
        except Exception:
            self.handleError(record)
