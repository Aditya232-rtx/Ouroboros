import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.agents.red_agent import REDAgent
from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    print("🚀 Starting Standalone RED Agent Test...")
    
    # Initialize Agent
    try:
        agent = REDAgent()
    except Exception as e:
        print(f"❌ Failed to initialize RED Agent: {e}")
        return

    # Test Input
    test_input = {
        "repo_url": "https://github.com/Aditya232-rtx/vul.git",
        "branch": "main",
        "scan_profile": "deep"  # deep = semgrep + checkov + nuclei
    }

    print(f"🎯 Target: {test_input['repo_url']}")
    print("⏳ Executing scan...")

    try:
        # Run Execute
        result = await agent.execute(test_input)
        
        print("\n✅ Execution Complete!")
        print(f"Scan ID: {result.get('scan_id')}")
        print(f"Status: {'Success' if result.get('scan_complete') else 'Failed'}")
        
        vulns = result.get('vulnerabilities', [])
        print(f"🔍 Vulnerabilities Found: {len(vulns)}")
        
        for v in vulns:
            # Result is a dict from .model_dump()
            print(f"  - [{v.get('severity')}] {v.get('type')}: {v.get('location', {}).get('file')}:{v.get('location', {}).get('line')}")
            
    except Exception as e:
        print(f"\n❌ Execution Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
