import asyncio
import logging
import os
import shutil
from pathlib import Path
from src.agents.red_agent import REDAgent
from src.security.tools.executor import PentestExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_llm_sast():
    logger.info("--- Starting LLM SAST Integration Test ---")
    
    # 1. Setup Mock Sandbox
    sandbox_dir = Path("/tmp/ouroboros_test_sast")
    if sandbox_dir.exists():
        shutil.rmtree(sandbox_dir)
    sandbox_dir.mkdir(parents=True)
    
    # Creates a file with an obvious vulnerability (Hardcoded Secret + potential RCE)
    vulnerable_code = """
import os

def login(username, password):
    # VULNERABILITY: Hardcoded secret
    if password == "SuperSecretPassword123":
        print("Login successful")
        
        # VULNERABILITY: Command Injection
        user_input = input("Enter command: ")
        os.system("echo " + user_input) 
    else:
        print("Login failed")
"""
    (sandbox_dir / "app.py").write_text(vulnerable_code)
    
    # 2. Initialize Red Agent
    agent = REDAgent()
    
    # 3. Manually trigger _run_llm_sast_scan (Unit Test style)
    logger.info("Testing _run_llm_sast_scan directly...")
    findings = await agent._run_llm_sast_scan(str(sandbox_dir), "http://mock-repo")
    
    logger.info(f"Findings: {findings}")
    
    # 4. Verify results
    has_secret = any("secret" in str(f).lower() for f in findings)
    has_injection = any("injection" in str(f).lower() for f in findings)
    
    if has_secret or has_injection:
        logger.info("✅ SUCCESS: LLM SAST found vulnerabilities!")
    else:
        logger.error("❌ FAILURE: LLM SAST did not find the obvious vulnerabilities.")

if __name__ == "__main__":
    asyncio.run(test_llm_sast())
