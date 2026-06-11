import asyncio
import logging
import os
import sys
import json
from pathlib import Path

# Ensure src is in pythonpath
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.red_agent import REDAgent
from src.integrations.mcp_manager import MCPManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_full_scan():
    target_url = "https://github.com/Aditya232-rtx/vul.git"
    logger.info(f"🚀 Starting Full Red Agent Test against: {target_url}")
    
    # 1. Setup Environment
    # Add local bin to PATH for tools
    project_root = Path(__file__).parent.parent
    bin_dir = project_root / "bin"
    os.environ["PATH"] = f"{bin_dir}:{os.environ['PATH']}"
    
    # Git SSL Bypass (for safety in dev envs)
    os.environ["GIT_SSL_NO_VERIFY"] = "true"

    try:
        # 2. Initialize Agent
        logger.info("Initializing RED Agent (loading Qwen2.5-Coder)...")
        agent = REDAgent()
        
        # 3. Prepare Input
        input_data = {
            "repo_url": target_url,
            "branch": "main",
            "scan_profile": "standard", # Triggers SAST + DAST + LLM
            "timeout_seconds": 600
        }
        
        # 4. Execute Scan
        logger.info("Executing Red Agent Workflow (Clone -> Sandbox -> SAST -> DAST -> LLM)...")
        result = await agent.execute(input_data)
        
        # 5. Report Findings
        print("\n" + "="*80)
        print(f"🛑 RED AGENT SCAN RESULTS for {target_url}")
        print("="*80)
        
        if not result.get("scan_complete"):
            print("❌ Scan Failed!")
            return

        vulnerabilities = result.get("vulnerabilities", [])
        print(f"📊 Total Findings: {len(vulnerabilities)}")
        print("-" * 80)
        
        # Sort by severity
        severity_map = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        vulnerabilities.sort(key=lambda x: severity_map.get(x.get("severity", "info").lower(), 5))
        
        for i, vuln in enumerate(vulnerabilities, 1):
            severity = vuln.get("severity", "UNKNOWN").upper()
            title = vuln.get("type", "Unknown Vulnerability")
            
            # Extract location
            loc = vuln.get("location", {})
            if isinstance(loc, dict):
                file_path = loc.get("file", "unknown")
                line = loc.get("line", 0)
            else:
                file_path = str(loc)
                line = 0
                
            tools = vuln.get("tools_detected_by", ["unknown"])
            tools_str = ", ".join(tools)
            
            print(f"{i}. [{severity}] {title}")
            print(f"   📍 Location: {file_path}:{line}")
            print(f"   🛠️  Found by: {tools_str}")
            print(f"   📝 Description: {vuln.get('description', '')[:200]}...")
            print("-" * 40)

        # 6. Check for LLM SAST specific findings
        llm_findings = [v for v in vulnerabilities if "llm_sast" in v.get("tools_detected_by", [])]
        print(f"\n🧠 AI-Specific Findings (Active LLM Scan): {len(llm_findings)}")
        for i, vuln in enumerate(llm_findings, 1):
             print(f"   - {vuln.get('type')} in {vuln.get('location', {}).get('file')}")

        print("="*80)

    except Exception as e:
        logger.error(f"Test Execution Failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_full_scan())
