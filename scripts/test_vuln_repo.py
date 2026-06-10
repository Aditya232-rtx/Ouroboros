
import asyncio
import logging
import sys
import os

# Ensure we can import from src
sys.path.append(os.getcwd())

from src.agents.red_agent import REDAgent, REDAgentInput

async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("VulnRepoScanner")
    
    target_repo = "https://github.com/Aditya232-rtx/vul.git"
    logger.info(f"Starting Red Agent Scan on {target_repo}...")
    
    agent = REDAgent()
    
    # Run a 'Deep' scan to trigger all Architect features (Proxy, Evasion, PrivEsc)
    input_data = REDAgentInput(
        repo_url=target_repo,
        scan_profile="deep", 
        auth_token="test_token"
    )
    
    try:
        results = await agent.execute(input_data.model_dump())
        logger.info("Scan Complete!")
        
        # Print Summary
        summary = results.get("summary", {})
        logger.info(f"Vulnerabilities Found: {summary.get('critical_vulnerabilities', 0)} Critical, {summary.get('high_vulnerabilities', 0)} High, {summary.get('medium_vulnerabilities', 0)} Medium, {summary.get('low_vulnerabilities', 0)} Low, {summary.get('info_vulnerabilities', 0)} Info")
        
        # Check specific Architect features in output
        if results.get("privesc_info"):
            logger.info("✅ Privilege Escalation Phase Executed")
        
        if results.get("persistence_info"):
            logger.info("✅ Persistence Phase Executed")
            
        if results.get("lateral_movement_info"):
            logger.info("✅ Lateral Movement Phase Executed")
            
    except Exception as e:
        logger.error(f"Scan Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
