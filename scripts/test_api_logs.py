
import requests
import time
import json

API_URL = "http://localhost:8000"

def test_logs():
    repo_url="https://github.com/Aditya232-rtx/vul.git"
    # 1. Start a scan
    print(f"🚀 Starting scan for {repo_url}...")
    response = requests.post(f"{API_URL}/scan", json={
        "repo_url": repo_url, 
        "scan_profile": "quick",
        "auto_fix": False
    })
    
    if response.status_code != 200:
        print(f"❌ Failed to start scan: {response.text}")
        return
        
    data = response.json()
    scan_id = data["scan_id"]
    print(f"✅ Scan started: {scan_id}")
    
    # Wait a bit for logs to generate
    time.sleep(5)
    
    # 2. Poll for logs using specific ID (Warloop behavior)
    print("📡 Polling logs (Warloop behavior)...")
    log_resp = requests.get(f"{API_URL}/status/{scan_id}/logs")
    if log_resp.status_code == 200:
        logs = log_resp.json().get("logs", [])
        print(f"   ✅ Warloop: Received {len(logs)} logs")
    else:
        print(f"   ❌ Warloop: Failed to fetch logs: {log_resp.status_code}")

    # 3. Poll for logs using 'latest' (Red Agent page behavior)
    print("📡 Polling logs via 'latest' (Red Agent behavior)...")
    latest_resp = requests.get(f"{API_URL}/status/latest/logs")
    if latest_resp.status_code == 200:
        latest_logs = latest_resp.json().get("logs", [])
        print(f"   ✅ Red Agent Page ('latest'): Received {len(latest_logs)} logs")
        
        # 4. Verify Red Agent Filtering
        red_logs = [l for l in latest_logs if l.get("source") == "RED_AGENT"]
        print(f"   ✅ Red Agent Filtered: Found {len(red_logs)} logs from RED_AGENT")
        if red_logs:
            print(f"      Sample: {red_logs[0]['message']}")
    else:
        print(f"   ❌ Red Agent Page: Failed to fetch 'latest' logs: {latest_resp.status_code}")
            
if __name__ == "__main__":
    test_logs()
