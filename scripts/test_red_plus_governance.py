#!/usr/bin/env python3
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# Setup path to import from src
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.red_agent import REDAgent
from src.agents.governance_agent import GovernanceAgent
from config.settings import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_joint_agents():
    logger.info("🚀 Starting Joint Red + Governance Agent Test")
    
    # Target for testing
    target_repo = "https://github.com/Aditya232-rtx/vul.git"
    
    # Init Red Agent
    red_agent = REDAgent()
    
    # Run Red Agent Scan
    logger.info(f"🔴 Running Red Agent Scan against {target_repo}")
    red_result = await red_agent.execute({
        "repo_url": target_repo,
        "scan_profile": "standard"
    })
    
    vulnerabilities = red_result.get("vulnerabilities", [])
    logger.info(f"✅ Red Agent found {len(vulnerabilities)} vulnerabilities")
    
    # Save the output of Red Agent for inspection
    with open("red_agent_output.json", "w") as f:
        json.dump(red_result, f, indent=2)
    logger.info("💾 Red Agent output saved to red_agent_output.json")

    # Init Governance Agent
    gov_agent = GovernanceAgent()
    
    # Run Governance Agent (Prioritization)
    logger.info("⚖️ Running Governance Agent for Risk Assessment & Prioritization")
    gov_result = await gov_agent.execute({
        "vulnerabilities": vulnerabilities,
        "environment": "production"
    })
    
    # The output of Governance Agent that goes to Blue Agent
    prioritized_queue = gov_result.get("prioritized_queue", [])
    logger.info(f"✅ Governance complete. {len(prioritized_queue)} items in prioritized queue.")
    
    # Save the output of Governance Agent for inspection
    with open("governance_agent_output.json", "w") as f:
        json.dump(gov_result, f, indent=2)
    logger.info("💾 Governance Agent output saved to governance_agent_output.json")

    print("\n" + "="*80)
    print("📋 DATA PASSED TO BLUE AGENT (Top 3 items from Prioritized Queue)")
    print("="*80)
    
    for i, item in enumerate(prioritized_queue[:3]):
        print(f"\n[{i+1}] VULNERABILITY: {item.get('id')}")
        print(f"    Type: {item.get('type')}")
        print(f"    Severity: {item.get('severity')}")
        print(f"    Risk Score: {gov_result.get('risk_scores', {}).get(item.get('id'), 'N/A')}")
        print(f"    Location: {item.get('location', {}).get('file', 'N/A')}:{item.get('location', {}).get('line', 0)}")
        print(f"    CWE: {item.get('cwe', 'N/A')}")
        print(f"    CVSS: {item.get('cvss', 0.0)}")
        print(f"    Description: {item.get('description')[:100]}...")

    print("\n" + "="*80)
    logger.info("🏁 Test complete.")

if __name__ == "__main__":
    asyncio.run(test_joint_agents())
