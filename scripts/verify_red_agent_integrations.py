
import asyncio
import logging
import sys
import os

# Ensure we can import from src
sys.path.append(os.getcwd())

from src.security.tools.proxy import ProxyManager
from src.security.tools.evasion import EvasionTools
from src.security.tools.privesc import LinuxPrivEsc
from src.security.tools.lateral import LateralMovementTools
from src.security.tools.browser import BrowserTool
from src.agents.red_agent import REDAgent

# Mock LLM for testing
async def mock_llm(prompt):
    return '{"detected": false, "risk_score": 2, "improvements": ["None"]}'

async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("RedAgentVerifier")
    
    logger.info("1. Testing ProxyManager...")
    try:
        proxy = ProxyManager()
        logger.info(f"Proxy Available: {proxy.available}")
    except Exception as e:
        logger.error(f"Proxy Init Failed: {e}")
    
    logger.info("2. Testing EvasionTools...")
    try:
        evasion = EvasionTools()
        res = await evasion.check_stealth("Test Scan Plan", mock_llm)
        logger.info(f"Stealth Check Result: {res}")
    except Exception as e:
        logger.error(f"Evasion Testing Failed: {e}")
    
    logger.info("3. Testing PrivEsc Tools...")
    try:
        privesc = LinuxPrivEsc()
        enum = privesc.enumerate()
        logger.info(f"PrivEsc Enumeration (Keys): {list(enum.keys())}")
    except Exception as e:
        logger.error(f"PrivEsc Failed: {e}")
    
    logger.info("4. Testing Lateral Movement...")
    try:
        lateral = LateralMovementTools()
        neighbors = await lateral.discover_neighbors("192.168.1.0/24")
        logger.info(f"Neighbors Discovered: {len(neighbors)}")
    except Exception as e:
        logger.error(f"Lateral Movement Failed: {e}")
    
    logger.info("5. Testing Browser Tool (Headless)...")
    try:
        browser = BrowserTool()
        # Just init, don't launch to save time/resources if not needed
        logger.info("Browser Tool Initialized.")
    except Exception as e:
        logger.error(f"Browser Init Failed: {e}")

    logger.info("6. Testing RedAgent Import & Init...")
    try:
        agent = REDAgent()
        logger.info("RedAgent Initialized Successfully.")
    except Exception as e:
        logger.error(f"RedAgent Init Failed: {e}")
        import traceback
        traceback.print_exc()
        
    logger.info("Verification Complete.")

if __name__ == "__main__":
    asyncio.run(main())
