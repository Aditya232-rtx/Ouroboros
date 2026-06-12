"""One-shot runner — captures final_state cleanly to stdout."""
import asyncio
import json
import sys

sys.path.insert(0, "d:/inceptrix")

from src.agents.research_agent import research_app

initial_state = {
    "url": "https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-38408",
    "raw_markdown": "",
    "extracted_json": {},
    "error_message": "",
    "retry_count": 0,
}

print("=== INITIATING RESEARCH GRAPH ===")
final_state = asyncio.run(research_app.ainvoke(initial_state))

print()
print("=== FINAL EXTRACTED INTELLIGENCE ===")
result = final_state.get("extracted_json", {})
print(json.dumps(result, indent=2))
print()
print("retry_count   :", final_state.get("retry_count"))
err = final_state.get("error_message")
print("error_message :", err if err else "None (clean parse on first attempt)")
