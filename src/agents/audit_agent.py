"""
Ouroboros AI - AUDIT Agent
Immutable compliance logging using Phi-3.5-mini and immudb
"""

import logging
import hashlib
import json
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.models import get_model

logger = logging.getLogger(__name__)


class AuditEvent(BaseModel):
    """Single audit event"""
    event_type: str
    entity_id: str
    details: Dict[str, Any]
    digital_signature: str
    merkle_hash: str


class ComplianceMappings(BaseModel):
    """Compliance framework mappings"""
    soc2: List[str] = Field(default_factory=list)
    iso27001: List[str] = Field(default_factory=list)
    gdpr: List[str] = Field(default_factory=list)
    hipaa: List[str] = Field(default_factory=list)
    pci_dss: List[str] = Field(default_factory=list)


class LedgerEntry(BaseModel):
    """Immutable ledger entry"""
    ledger_id: str
    hash_chain: str
    tamper_proof: bool


class AuditAgentInput(AgentInput):
    """Input schema for AUDIT Agent"""
    event_type: str
    entity_id: str
    details: Dict[str, Any]


class AuditAgentOutput(AgentOutput):
    """Output schema for AUDIT Agent"""
    audit_id: str
    events: List[AuditEvent]
    compliance_mappings: ComplianceMappings
    ledger_entry: LedgerEntry


class AuditAgent(BaseAgent):
    """
    AUDIT Agent - Immutable compliance logging specialist
    
    Uses Phi-3.5-mini-instruct for event normalization
    Logs to immudb for tamper-proof audit trail
    """
    
    # Compliance control mappings by event type
    COMPLIANCE_MAPPINGS = {
        "red_discovery": {
            "soc2": ["CC6.1", "CC7.2"],
            "iso27001": ["A.12.2.1", "A.14.2.1"],
            "gdpr": ["Article 32"],
            "hipaa": ["164.312(a)(2)(i)"],
            "pci_dss": ["6.5.1"]
        },
        "blue_generation": {
            "soc2": ["CC6.1", "CC8.1"],
            "iso27001": ["A.14.2.1", "A.14.2.9"],
            "gdpr": ["Article 32"],
            "hipaa": ["164.308(a)(5)"],
            "pci_dss": ["6.5.1", "6.6"]
        },
        "governance_decision": {
            "soc2": ["CC5.1", "CC5.2"],
            "iso27001": ["A.18.1.1", "A.18.2.1"],
            "gdpr": ["Article 24"],
            "hipaa": ["164.308(a)(1)"],
            "pci_dss": ["12.1"]
        },
        "pr_created": {
            "soc2": ["CC6.1", "CC7.1"],
            "iso27001": ["A.12.1.2", "A.14.2.2"],
            "gdpr": ["Article 32"],
            "hipaa": ["164.312(b)"],
            "pci_dss": ["6.4.5"]
        }
    }
    
    def __init__(self):
        """Initialize AUDIT Agent with Phi-3.5 model"""
        model = get_model("audit")
        super().__init__(model=model, agent_id="AUDIT")
        
        # Hash chain for Merkle tree
        self._previous_hash = "0" * 64  # Genesis hash
        
        self.system_prompt = """You are Phi-3.5, a compliance & audit logging system.

TASK: Normalize security events for immutable logging.

OUTPUT (JSON):
{
  "event_id": "uuid",
  "timestamp": "ISO8601",
  "event_type": "vulnerability_discovered|fix_generated|fix_verified|pr_created",
  "severity": "critical|high|medium|low",
  "entities": {...},
  "compliance_mappings": {
    "SOC2": ["CC6.1"],
    "ISO27001": ["A.12.2.1"],
    "GDPR": ["Article32"],
    "HIPAA": ["§164.308(a)"],
    "PCI_DSS": ["6.5.1"]
  },
  "digital_signature": "sha256-signature",
  "immutable_proof": "merkle-root-hash"
}

CRITICAL: Every field must be populated. No secrets in logs."""
    
    def validate_input(self, input_data: Dict[str, Any]) -> AuditAgentInput:
        """Validate AUDIT Agent input"""
        return AuditAgentInput(**input_data)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute AUDIT Agent to log event"""
        audit_id = f"AUDIT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        self.logger.info(f"Creating audit entry {audit_id}")
        
        try:
            # Create event
            event = self._create_event(input_data)
            
            # Get compliance mappings
            mappings = self._get_compliance_mappings(input_data["event_type"])
            
            # Log to immudb via integrated client
            ledger_entry = await self._log_to_immudb(event)
            
            return {
                "audit_id": audit_id,
                "events": [event],
                "compliance_mappings": mappings,
                "ledger_entry": ledger_entry
            }
            
        except Exception as e:
            self.logger.error(f"Audit logging failed: {e}")
            return {
                "audit_id": audit_id,
                "events": [],
                "compliance_mappings": {},
                "ledger_entry": {"error": str(e)}
            }
    
    def _create_event(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create signed audit event"""
        event_data = {
            "event_type": input_data["event_type"],
            "entity_id": input_data["entity_id"],
            "details": self._redact_sensitive(input_data["details"]),
            "timestamp": datetime.now().isoformat()
        }
        
        # Create digital signature
        signature = self._create_signature(event_data)
        
        # Calculate Merkle hash (chain to previous)
        merkle_hash = self._calculate_merkle_hash(event_data, signature)
        
        return {
            **event_data,
            "digital_signature": signature,
            "merkle_hash": merkle_hash
        }
    
    def _create_signature(self, data: Dict[str, Any]) -> str:
        """Create HMAC-SHA256 signature using secret from settings."""
        import hmac
        
        # Load secret key from settings
        try:
            from config.settings import settings
            secret_key = settings.secret_key
        except Exception:
            secret_key = "ouroboros-hmac-key-default"
        
        data_str = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            secret_key.encode(),
            data_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _calculate_merkle_hash(
        self, 
        data: Dict[str, Any], 
        signature: str
    ) -> str:
        """Calculate Merkle hash for chain integrity"""
        combined = json.dumps(data, sort_keys=True) + signature + self._previous_hash
        current_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        # Update chain
        self._previous_hash = current_hash
        
        return current_hash
    
    def _redact_sensitive(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive fields from logs"""
        sensitive_fields = [
            "password", "api_key", "token", "secret",
            "ssn", "credit_card", "private_key"
        ]
        
        redacted = {}
        for key, value in details.items():
            if any(s in key.lower() for s in sensitive_fields):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self._redact_sensitive(value)
            else:
                redacted[key] = value
        
        return redacted
    
    def _get_compliance_mappings(self, event_type: str) -> Dict[str, List[str]]:
        """Get compliance framework mappings for event type"""
        return self.COMPLIANCE_MAPPINGS.get(event_type, {
            "soc2": [],
            "iso27001": [],
            "gdpr": [],
            "hipaa": [],
            "pci_dss": []
        })
    
    async def _log_to_immudb(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Log event to immudb using the real immudb client."""
        try:
            from src.integrations.immudb_client import immudb_client
            
            # Connect if not connected
            if not immudb_client.connected:
                immudb_client.connect()
            
            # Log the event
            event_hash = immudb_client.log_event(
                event_type=event["event_type"],
                entity_id=event["entity_id"],
                details=event["details"],
                compliance_mappings=None
            )
            
            self.logger.info(f"Logged to immudb: {event_hash[:12]}...")
            
            return {
                "ledger_id": event_hash,
                "hash_chain": event["merkle_hash"],
                "tamper_proof": True
            }
            
        except Exception as e:
            self.logger.error(f"immudb logging failed: {e}")
            # Fallback response
            return {
                "ledger_id": f"local-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "hash_chain": event["merkle_hash"],
                "tamper_proof": False
            }
    
    def format_output(self, result: Dict[str, Any]) -> AuditAgentOutput:
        """Format AUDIT Agent output"""
        return AuditAgentOutput(
            agent_id=self.agent_id,
            timestamp=datetime.now().isoformat(),
            status="success" if result.get("events") else "error",
            audit_id=result["audit_id"],
            events=[AuditEvent(**e) for e in result["events"]],
            compliance_mappings=ComplianceMappings(**result["compliance_mappings"]) if result.get("compliance_mappings") else None,
            ledger_entry=LedgerEntry(**result["ledger_entry"]) if "error" not in result.get("ledger_entry", {}) else None
        )
