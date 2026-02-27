import json
import asyncio
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
import ollama
from src.tools.research_scraper import scrape_vulnerability_data
import requests
import os
from src.security.memory.research_memory import ResearchMemory

memory = ResearchMemory()

# 1. Define the State Dictionary
class ResearchState(TypedDict):
    url: str
    raw_markdown: str
    extracted_json: Dict[str, Any]
    error_message: str
    retry_count: int

# 2. Ingest Node (The Searcher)
async def ingest_node(state: ResearchState):
    cve_id_guess = state['url'].split("name=")[-1] if "name=" in state['url'] else "UNKNOWN"
    if memory.has_been_researched(cve_id_guess):
        print(f"[*] [Node: Ingest] Memory Hit: {cve_id_guess} already researched. Skipping.")
        return {"raw_markdown": "MEMORY_HIT"}

    print(f"[*] [Node: Ingest] Scraping {state['url']}...")
    md = await scrape_vulnerability_data(state['url'])
    return {"raw_markdown": md}

# 3. Reasoning Node (The Brain)
def reasoning_node(state: ResearchState):
    attempt = state.get('retry_count', 0) + 1
    print(f"[*] [Node: Reason] Analyzing Markdown with Qwen 1.5b (Attempt {attempt}/3)...")

    prompt = f"""
Analyze the following security markdown. Extract the vulnerability details into STRICT, raw JSON.
Do NOT include markdown formatting blocks like ```json. Output ONLY the JSON object.
Expected JSON Schema (match the Red Agent's expectations):
{{
    "id": "CVE-...",
    "title": "...",
    "severity": "critical|high|medium|low",
    "cwe": "...",
    "cvss": 0.0,
    "description": "...",
    "poc_code": "..."
}}
Previous Error to Fix (if any): {state.get('error_message', '')}
Markdown Payload:
{state.get('raw_markdown', '')[:3500]} 
"""
    response = ollama.chat(model='qwen2.5-coder:1.5b', messages=[
        {'role': 'system', 'content': 'You are a strict JSON data extractor. You do not converse.'},
        {'role': 'user', 'content': prompt}
    ])
    
    raw_output = response['message']['content']
    
    # Attempt to parse the LLM output into a dictionary
    try:
        clean_output = raw_output.replace('```json', '').replace('```', '').strip()
        parsed_json = json.loads(clean_output)
        return {"extracted_json": parsed_json, "error_message": "", "retry_count": attempt}
    except json.JSONDecodeError as e:
        print(f"[-] JSON Parse Error on attempt {attempt}.")
        return {"error_message": f"Parsing Error: {str(e)}. Raw output was: {raw_output}", "retry_count": attempt}

# 4. Reflector Logic (Conditional Edge)
def reflector_edge(state: ResearchState):
    if state.get('extracted_json'):
        print("[+] [Edge: Reflector] Valid JSON detected. Proceeding to Dispatch.")
        return "dispatch"
    if state.get('retry_count', 0) >= 3:
        print("[-] [Edge: Reflector] Max retries reached. Aborting to prevent infinite loop.")
        return "end"

    print("[!] [Edge: Reflector] Invalid JSON. Looping back to reasoning node.")
    return "retry"

def dispatch_node(state: ResearchState):
    print("\n[*] [Node: Dispatch] Intelligence validated. Initiating Handoff...")
    
    # 1. Save the intelligence to the research_findings directory
    os.makedirs("research_findings", exist_ok=True)
    cve_id_guess = state['url'].split("name=")[-1] if "name=" in state['url'] else "UNKNOWN_CVE"
    cve_id = state['extracted_json'].get('id', cve_id_guess)
    if cve_id_guess != "UNKNOWN_CVE":
        cve_id = cve_id_guess
        state['extracted_json']['id'] = cve_id
    file_path = f"research_findings/{cve_id}_report.json"
    
    with open(file_path, "w") as f:
        json.dump(state['extracted_json'], f, indent=4)
    print(f"[+] Intelligence saved locally to {file_path}")
    
    memory.store_intelligence(cve_id, state['extracted_json'])
    
    # 2. Fire the webhook to the main Ouroboros API (Red/Blue trigger)
    # We simulate an autonomous decision to scan the main repo based on the threat
    api_url = "http://localhost:8000/api/scan"
    payload = {
        "repo_url": "https://github.com/Aditya232-rtx/Ouroboros", # Target repo
        "scan_profile": "deep",
        "auto_fix": True,
        "create_pr": True
    }
    
    try:
        print(f"[*] Firing autonomous scan trigger to {api_url}...")
        response = requests.post(api_url, json=payload, timeout=5)
        if response.status_code in [200, 201, 202]:
            print("[+] SUCCESS: Red and Blue agents have been triggered!")
            print(f"[+] API Response: {response.json()}")
        else:
            print(f"[-] API rejected the trigger. Status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("[-] API unreachable. (Is the FastAPI server running on port 8000?)")
        
    return {"error_message": "dispatched"}

# 5. Graph Compilation
workflow = StateGraph(ResearchState)
workflow.add_node("ingest", ingest_node)
workflow.add_node("reason", reasoning_node)
workflow.add_node("dispatch", dispatch_node)

workflow.set_entry_point("ingest")

def check_memory_hit(state: ResearchState):
    if state.get("raw_markdown") == "MEMORY_HIT":
        return "end"
    return "reason"

workflow.add_conditional_edges(
    "ingest",
    check_memory_hit,
    {
        "end": END,
        "reason": "reason"
    }
)

workflow.add_edge("dispatch", END)
workflow.add_conditional_edges(
    "reason",
    reflector_edge,
    {
        "dispatch": "dispatch",
        "end": END,
        "retry": "reason"
    }
)

research_app = workflow.compile()

# --- Quick Test Block ---
if __name__ == "__main__":
    test_url = "https://nvd.nist.gov/vuln/detail/CVE-2021-44228"
    # To test memory, we need to pass a query param 'name' to satisfy the crude parsing logic given in the prompt test
    # e.g., ?name=CVE-2021-44228
    if "name=" not in test_url:
        test_url = test_url + "?name=CVE-2021-44228"
        
    initial_state = {
        "url": test_url,
        "raw_markdown": "",
        "extracted_json": {},
        "error_message": "",
        "retry_count": 0
    }
    print("\n=== INITIATING RESEARCH GRAPH ===")
    final_state = asyncio.run(research_app.ainvoke(initial_state))
    print("\n=== FINAL EXTRACTED INTELLIGENCE ===")
    print(json.dumps(final_state.get('extracted_json', {}), indent=2))
