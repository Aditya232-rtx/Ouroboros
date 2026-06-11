import asyncio
import logging
import sys
import os
from pathlib import Path

# Setup Path
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.governance_agent import GovernanceAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_risk_calculation():
    print("🚀 Starting Governance Risk Calculation Test")
    
    agent = GovernanceAgent()
    
    # Mock Findings from Red Agent
    findings = [
        {
            "id": "RED-001",
            "type": "sql_injection",
            "severity": "critical", # Should map to 9.5
            "location": "src/api/auth/login.py",
            "description": "SQL Injection in login query allows authentication bypass.",
            "confidence": 0.95
        },
        {
            "id": "RED-002",
            "type": "hardcoded_secret",
            "severity": "low", # Should map to 3.0
            "location": "scripts/cleanup_unused.sh",
            "description": "Hardcoded API key in unused cleanup script.",
            "confidence": 0.9
        },
        {
            "id": "RED-003",
            "type": "xss",
            "severity": "medium", # Should map to 5.5
            "location": "src/frontend/components/Footer.tsx",
            "description": "Reflected XSS in footer copyright year parameter.",
            "confidence": 0.8
        }
    ]
    
    input_data = {
        "vulnerabilities": findings,
        "environment": "production" # High env multiplier (5.0)
    }
    
    print("\n🔍 Executing Governance Agent...")
    result = await agent.execute(input_data)
    
    print("\n📊 Risk Scores:")
    print("-" * 60)
    print(f"{'ID':<10} | {'Type':<20} | {'CISO Risk (LLM)':<17} | {'Risk Score':<10}")
    print("-" * 65)
    
    for item in result.get("prioritized_queue", []):
         vid = item.get("id")
         # Find decision
         decision = next((d for d in result["decisions"] if d["vulnerability_id"] == vid), {})
         
         risk_mult = decision.get("ciso_risk_multiplier", "N/A")
         score = decision.get("risk_score", 0.0)
         vtype = item.get("type")
         
         print(f"{vid:<10} | {vtype:<20} | {str(risk_mult):<17} | {score:<10.2f}")
         
    print("-" * 65)
    
    # Verification Logic
    # 1. SQLi (Critical, Auth, Internet Facing) should have High Risk (>=2.0)
    # 2. Secret (Low, Script, Internal) should have Low Risk (<=1.5)
    
    decisions = {d["vulnerability_id"]: d for d in result["decisions"]}
    
    sqli = decisions.get("RED-001")
    secret = decisions.get("RED-002")
    
    if sqli and secret:
        if sqli["ciso_risk_multiplier"] > secret["ciso_risk_multiplier"]:
            print("✅ TEST PASS: Critical CISO Risk is higher than low usage script.")
        else:
            print("❌ TEST FAIL: CISO Risk logic seems incorrect.")
            
    print("\nTest Complete.")

if __name__ == "__main__":
    asyncio.run(test_risk_calculation())
