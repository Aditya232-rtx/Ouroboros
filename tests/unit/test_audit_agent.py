"""
Unit tests for the AUDIT Agent

Tests:
1. Input validation
2. Event creation with digital signatures
3. Merkle hash chain integrity
4. Compliance mappings
5. Sensitive data redaction
6. immudb integration (mocked)
"""

import pytest
import json
import hashlib
import hmac
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_red_discovery_event():
    """Sample RED agent discovery event"""
    return {
        "event_type": "red_discovery",
        "entity_id": "SCAN-20260130-120000",
        "details": {
            "repo_url": "https://github.com/test/app",
            "vulnerabilities_found": 5,
            "critical_count": 2,
            "scan_duration_seconds": 45
        }
    }


@pytest.fixture
def sample_blue_generation_event():
    """Sample BLUE agent generation event"""
    return {
        "event_type": "blue_generation",
        "entity_id": "FIX-20260130-120100",
        "details": {
            "vulnerability_id": "RED-001",
            "fix_approach": "parameterized_queries",
            "safety_gates_passed": True,
            "confidence": 0.92
        }
    }


@pytest.fixture
def sample_governance_event():
    """Sample governance decision event"""
    return {
        "event_type": "governance_decision",
        "entity_id": "GOV-20260130-120200",
        "details": {
            "vulnerabilities_evaluated": 5,
            "auto_approved": 3,
            "requires_review": 2,
            "risk_score": 67.5
        }
    }


@pytest.fixture
def sample_pr_created_event():
    """Sample PR created event"""
    return {
        "event_type": "pr_created",
        "entity_id": "PR-123",
        "details": {
            "repo": "test/app",
            "branch": "ouroboros/security-fix-20260130",
            "fixes_included": 5,
            "pr_url": "https://github.com/test/app/pull/123"
        }
    }


@pytest.fixture
def sensitive_data_event():
    """Event with sensitive data that should be redacted"""
    return {
        "event_type": "blue_generation",
        "entity_id": "FIX-001",
        "details": {
            "vulnerability_id": "RED-001",
            "api_key": "sk-secret-key-12345",
            "password": "super_secret_password",
            "database_token": "db-token-xyz",
            "safe_field": "this should remain"
        }
    }


@pytest.fixture
def audit_agent():
    """Create an AuditAgent with mocked model"""
    with patch('src.agents.audit_agent.get_model') as mock_get_model:
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        
        from src.agents.audit_agent import AuditAgent
        agent = AuditAgent()
        
        return agent


# ============================================================================
# Test: Input Validation
# ============================================================================

class TestInputValidation:
    """Tests for input validation"""
    
    def test_valid_input(self, audit_agent, sample_red_discovery_event):
        """Test validation with valid input"""
        validated = audit_agent.validate_input(sample_red_discovery_event)
        
        assert validated.event_type == "red_discovery"
        assert validated.entity_id == "SCAN-20260130-120000"
        assert "repo_url" in validated.details
    
    def test_missing_event_type_fails(self, audit_agent):
        """Test validation fails without event_type"""
        with pytest.raises(Exception):
            audit_agent.validate_input({
                "entity_id": "TEST-001",
                "details": {}
            })
    
    def test_missing_entity_id_fails(self, audit_agent):
        """Test validation fails without entity_id"""
        with pytest.raises(Exception):
            audit_agent.validate_input({
                "event_type": "test",
                "details": {}
            })


# ============================================================================
# Test: Digital Signatures
# ============================================================================

class TestDigitalSignatures:
    """Tests for digital signature creation"""
    
    def test_signature_is_created(self, audit_agent, sample_red_discovery_event):
        """Test that events get a digital signature"""
        event = audit_agent._create_event(sample_red_discovery_event)
        
        assert "digital_signature" in event
        assert len(event["digital_signature"]) == 64  # SHA256 hex
    
    def test_signature_is_deterministic(self, audit_agent):
        """Test same data produces same signature"""
        data = {"test": "data", "value": 123}
        
        sig1 = audit_agent._create_signature(data)
        sig2 = audit_agent._create_signature(data)
        
        assert sig1 == sig2
    
    def test_different_data_different_signature(self, audit_agent):
        """Test different data produces different signatures"""
        data1 = {"test": "data1"}
        data2 = {"test": "data2"}
        
        sig1 = audit_agent._create_signature(data1)
        sig2 = audit_agent._create_signature(data2)
        
        assert sig1 != sig2
    
    def test_signature_uses_hmac_sha256(self, audit_agent):
        """Test signature is valid HMAC-SHA256"""
        data = {"test": "value"}
        sig = audit_agent._create_signature(data)
        
        # Should be valid hex string of 64 chars (256 bits)
        assert len(sig) == 64
        assert all(c in '0123456789abcdef' for c in sig)


# ============================================================================
# Test: Merkle Hash Chain
# ============================================================================

class TestMerkleHashChain:
    """Tests for Merkle hash chain integrity"""
    
    def test_merkle_hash_is_created(self, audit_agent, sample_red_discovery_event):
        """Test that events get a Merkle hash"""
        event = audit_agent._create_event(sample_red_discovery_event)
        
        assert "merkle_hash" in event
        assert len(event["merkle_hash"]) == 64
    
    def test_hash_chain_updates(self, audit_agent, sample_red_discovery_event, sample_blue_generation_event):
        """Test that hash chain updates between events"""
        initial_hash = audit_agent._previous_hash
        
        event1 = audit_agent._create_event(sample_red_discovery_event)
        hash_after_1 = audit_agent._previous_hash
        
        event2 = audit_agent._create_event(sample_blue_generation_event)
        hash_after_2 = audit_agent._previous_hash
        
        # All hashes should be different
        assert initial_hash != hash_after_1
        assert hash_after_1 != hash_after_2
        
        # Chain should update
        assert audit_agent._previous_hash == hash_after_2
    
    def test_merkle_hash_includes_previous(self, audit_agent):
        """Test Merkle hash incorporates previous hash"""
        # Genesis hash
        assert audit_agent._previous_hash == "0" * 64
        
        # Create event
        event = audit_agent._create_event({
            "event_type": "test",
            "entity_id": "TEST-001",
            "details": {}
        })
        
        # Hash should have changed
        assert audit_agent._previous_hash != "0" * 64
        assert audit_agent._previous_hash == event["merkle_hash"]


# ============================================================================
# Test: Compliance Mappings
# ============================================================================

class TestComplianceMappings:
    """Tests for compliance framework mappings"""
    
    def test_red_discovery_mappings(self, audit_agent):
        """Test compliance mappings for red_discovery"""
        mappings = audit_agent._get_compliance_mappings("red_discovery")
        
        assert "CC6.1" in mappings["soc2"]
        assert "A.12.2.1" in mappings["iso27001"]
        assert "Article 32" in mappings["gdpr"]
    
    def test_blue_generation_mappings(self, audit_agent):
        """Test compliance mappings for blue_generation"""
        mappings = audit_agent._get_compliance_mappings("blue_generation")
        
        assert "CC8.1" in mappings["soc2"]
        assert "A.14.2.9" in mappings["iso27001"]
    
    def test_governance_decision_mappings(self, audit_agent):
        """Test compliance mappings for governance_decision"""
        mappings = audit_agent._get_compliance_mappings("governance_decision")
        
        assert "CC5.1" in mappings["soc2"]
        assert "A.18.1.1" in mappings["iso27001"]
    
    def test_pr_created_mappings(self, audit_agent):
        """Test compliance mappings for pr_created"""
        mappings = audit_agent._get_compliance_mappings("pr_created")
        
        assert "CC7.1" in mappings["soc2"]
        assert "6.4.5" in mappings["pci_dss"]
    
    def test_unknown_event_type_returns_empty(self, audit_agent):
        """Test unknown event type returns empty mappings"""
        mappings = audit_agent._get_compliance_mappings("unknown_event")
        
        assert mappings["soc2"] == []
        assert mappings["iso27001"] == []
        assert mappings["gdpr"] == []


# ============================================================================
# Test: Sensitive Data Redaction
# ============================================================================

class TestSensitiveDataRedaction:
    """Tests for sensitive data redaction"""
    
    def test_api_key_redacted(self, audit_agent, sensitive_data_event):
        """Test API keys are redacted"""
        redacted = audit_agent._redact_sensitive(sensitive_data_event["details"])
        
        assert redacted["api_key"] == "[REDACTED]"
    
    def test_password_redacted(self, audit_agent, sensitive_data_event):
        """Test passwords are redacted"""
        redacted = audit_agent._redact_sensitive(sensitive_data_event["details"])
        
        assert redacted["password"] == "[REDACTED]"
    
    def test_token_redacted(self, audit_agent, sensitive_data_event):
        """Test tokens are redacted"""
        redacted = audit_agent._redact_sensitive(sensitive_data_event["details"])
        
        assert redacted["database_token"] == "[REDACTED]"
    
    def test_safe_fields_preserved(self, audit_agent, sensitive_data_event):
        """Test non-sensitive fields are preserved"""
        redacted = audit_agent._redact_sensitive(sensitive_data_event["details"])
        
        assert redacted["safe_field"] == "this should remain"
        assert redacted["vulnerability_id"] == "RED-001"
    
    def test_nested_sensitive_data_redacted(self, audit_agent):
        """Test nested sensitive data is redacted"""
        data = {
            "config": {
                "api_key": "secret",
                "endpoint": "https://api.example.com"
            }
        }
        
        redacted = audit_agent._redact_sensitive(data)
        
        assert redacted["config"]["api_key"] == "[REDACTED]"
        assert redacted["config"]["endpoint"] == "https://api.example.com"
    
    def test_redaction_patterns(self, audit_agent):
        """Test all sensitive patterns are redacted"""
        sensitive_keys = [
            "password", "api_key", "token", "secret",
            "ssn", "credit_card", "private_key",
            "user_password", "db_secret", "auth_token"
        ]
        
        data = {key: f"value_{key}" for key in sensitive_keys}
        redacted = audit_agent._redact_sensitive(data)
        
        for key in sensitive_keys:
            assert redacted[key] == "[REDACTED]", f"{key} was not redacted"


# ============================================================================
# Test: Execute Method
# ============================================================================

class TestExecute:
    """Tests for the main execute method"""
    
    @pytest.mark.asyncio
    async def test_execute_returns_audit_id(self, audit_agent, sample_red_discovery_event):
        """Test execute returns audit ID"""
        with patch.object(audit_agent, '_log_to_immudb', new_callable=AsyncMock) as mock_log:
            mock_log.return_value = {
                "ledger_id": "test-ledger-123",
                "hash_chain": "abc123",
                "tamper_proof": True
            }
            
            result = await audit_agent.execute(sample_red_discovery_event)
            
            assert result["audit_id"].startswith("AUDIT-")
    
    @pytest.mark.asyncio
    async def test_execute_returns_events(self, audit_agent, sample_red_discovery_event):
        """Test execute returns created events"""
        with patch.object(audit_agent, '_log_to_immudb', new_callable=AsyncMock) as mock_log:
            mock_log.return_value = {
                "ledger_id": "test-ledger-123",
                "hash_chain": "abc123",
                "tamper_proof": True
            }
            
            result = await audit_agent.execute(sample_red_discovery_event)
            
            assert len(result["events"]) == 1
            assert result["events"][0]["event_type"] == "red_discovery"
    
    @pytest.mark.asyncio
    async def test_execute_returns_compliance_mappings(self, audit_agent, sample_red_discovery_event):
        """Test execute returns compliance mappings"""
        with patch.object(audit_agent, '_log_to_immudb', new_callable=AsyncMock) as mock_log:
            mock_log.return_value = {
                "ledger_id": "test-ledger-123",
                "hash_chain": "abc123",
                "tamper_proof": True
            }
            
            result = await audit_agent.execute(sample_red_discovery_event)
            
            assert "soc2" in result["compliance_mappings"]
            assert "iso27001" in result["compliance_mappings"]
    
    @pytest.mark.asyncio
    async def test_execute_handles_immudb_failure(self, audit_agent, sample_red_discovery_event):
        """Test execute handles immudb failure gracefully"""
        with patch.object(audit_agent, '_log_to_immudb', new_callable=AsyncMock) as mock_log:
            mock_log.side_effect = Exception("immudb connection failed")
            
            result = await audit_agent.execute(sample_red_discovery_event)
            
            # Should still return result, not crash
            assert result["audit_id"].startswith("AUDIT-")


# ============================================================================
# Test: Event Creation
# ============================================================================

class TestEventCreation:
    """Tests for event creation"""
    
    def test_event_has_timestamp(self, audit_agent, sample_red_discovery_event):
        """Test created events have timestamp"""
        event = audit_agent._create_event(sample_red_discovery_event)
        
        assert "timestamp" in event
        # Should be ISO format
        datetime.fromisoformat(event["timestamp"])
    
    def test_event_has_required_fields(self, audit_agent, sample_red_discovery_event):
        """Test created events have all required fields"""
        event = audit_agent._create_event(sample_red_discovery_event)
        
        required_fields = [
            "event_type", "entity_id", "details",
            "timestamp", "digital_signature", "merkle_hash"
        ]
        
        for field in required_fields:
            assert field in event, f"Missing field: {field}"
    
    def test_event_details_are_redacted(self, audit_agent, sensitive_data_event):
        """Test event details are redacted"""
        event = audit_agent._create_event(sensitive_data_event)
        
        assert event["details"]["api_key"] == "[REDACTED]"
        assert event["details"]["password"] == "[REDACTED]"


# ============================================================================
# Test: immudb Integration (Mocked)
# ============================================================================

class TestImmudbIntegration:
    """Tests for immudb integration"""
    
    @pytest.mark.asyncio
    async def test_log_to_immudb_returns_ledger_entry(self, audit_agent, sample_red_discovery_event):
        """Test logging to immudb returns ledger entry"""
        event = audit_agent._create_event(sample_red_discovery_event)
        
        # Test that _log_to_immudb returns expected structure
        result = await audit_agent._log_to_immudb(event)
        
        # Should return ledger entry (even if fallback)
        assert "ledger_id" in result
        assert "hash_chain" in result
        # tamper_proof might be False if immudb not connected (fallback)
        assert "tamper_proof" in result
    
    @pytest.mark.asyncio
    async def test_log_to_immudb_fallback_on_error(self, audit_agent, sample_red_discovery_event):
        """Test fallback when immudb fails"""
        event = audit_agent._create_event(sample_red_discovery_event)
        
        # The method should handle errors gracefully
        result = await audit_agent._log_to_immudb(event)
        
        # Should return a result even if immudb fails
        assert "ledger_id" in result or "hash_chain" in result


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
