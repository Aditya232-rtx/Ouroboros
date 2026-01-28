import asyncio
import logging
import sys
import os
from pathlib import Path

# Setup Path
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.documentation_agent import DocumentationAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_documentation_export():
    print("🚀 Starting Documentation Agent Verification")
    
    agent = DocumentationAgent()
    
    # Mock Data (Red Agent Findings + Governance Decisions)
    findings = [
        {
            "id": "RED-001",
            "type": "sql_injection",
            "severity": "critical",
            "location": "src/api/auth/login.py",
            "description": "SQL Injection in login query allows authentication bypass.",
            "cvss": 9.8
        },
        {
            "id": "RED-002",
            "type": "hardcoded_secret",
            "severity": "medium",
            "location": "config/app_settings.py",
            "description": "Hardcoded AWS secret key in settings.",
            "cvss": 6.5
        }
    ]
    
    metadata = {
        "repo_name": "Ouroboros-Demo-Target",
        "scan_id": "SCAN-TEST-001",
        "exported_by": "DocumentationAgent"
    }
    
    input_data = {
        "vulnerabilities": findings,
        "metadata": metadata,
        "governance_plan": [], 
        "fixes": [] 
    }
    
    print("\n📝 Generating Report (Phi-3.5)...")
    result = await agent.execute(input_data)
    
    print("\n✅ Generation Complete!")
    print(f"Documentation ID: {result['documentation_id']}")
    
    doc_info = result.get("google_doc")
    
    if doc_info:
        url = doc_info.get("doc_url", "")
        print(f"📄 Report URL: {url}")
        
        if url.startswith("file://"):
            print("📂 Mode: Local Fallback (Google Workspace not configured)")
            path = url.replace("file://", "")
            if os.path.exists(path):
                print(f"✅ File verified on disk: {path}")
                print(f"Size: {os.path.getsize(path)} bytes")
                
                # Print preview
                print("\n--- Report Preview (First 500 chars) ---")
                try:
                    with open(path, "r") as f:
                        print(f.read()[:500] + "...")
                except Exception as e:
                    print(f"Could not read file: {e}")
                print("----------------------------------------")
            else:
                 print("❌ File NOT found on disk!")
        else:
             print("☁️ Mode: Google Drive Upload Successful")
    else:
        print("❌ Report generation failed entirely (No doc info returned).")
        if result.get("content_summary", {}).get("error"):
            print(f"Error: {result['content_summary']['error']}")

    print("\nTest Complete.")

if __name__ == "__main__":
    asyncio.run(test_documentation_export())
