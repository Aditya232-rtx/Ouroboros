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
            source = "SYSTEM"
            if "red_agent" in record.name:
                source = "RED_AGENT"
            elif "blue_agent" in record.name:
                source = "BLUE_AGENT"
            elif "governance" in record.name:
                source = "GOVERNANCE"
            elif "audit" in record.name:
                source = "AUDIT"
            elif "orchestration" in record.name:
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
