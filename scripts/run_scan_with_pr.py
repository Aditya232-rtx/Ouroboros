import requests
import time

BASE = "http://localhost:8000"
REPO = "https://github.com/samoylenko/vulnerable-app-nodejs-express.git"

payload = {
    "repo_url": REPO,
    "branch": "main",
    "scan_profile": "standard",
    "auto_fix": True,
    "create_pr": True,
}

print("Submitting scan...")
r = requests.post(f"{BASE}/scan", json=payload, timeout=30)
print("POST /scan", r.status_code)
r.raise_for_status()
scan_id = r.json()["scan_id"]
print("scan_id:", scan_id)

start = time.time()
last_phase = None
last_status = None
while True:
    s = requests.get(f"{BASE}/status/{scan_id}", timeout=30)
    s.raise_for_status()
    data = s.json()
    status = data.get("status")
    phase = data.get("current_phase")
    if phase != last_phase or status != last_status:
        print(
            f"[{int(time.time() - start):4d}s] "
            f"status={status} phase={phase} "
            f"vulns={data.get('vulnerabilities_found')} "
            f"fixes={data.get('fixes_applied')}"
        )
        last_phase = phase
        last_status = status
    if status in ("completed", "failed"):
        break
    if time.time() - start > 3600:
        print("Timed out waiting for scan completion")
        break
    time.sleep(10)

detail = requests.get(f"{BASE}/status/{scan_id}/detail", timeout=30)
logs = requests.get(f"{BASE}/status/{scan_id}/logs", timeout=30)

print("\nDETAIL_STATUS:", detail.status_code)
if detail.ok:
    d = detail.json()
    print("final_status:", d.get("status"))
    print("phase:", d.get("current_phase"))
    print("error_message:", d.get("error_message"))
    print("vulnerabilities_found:", d.get("vulnerabilities_found"))
    print("fixes_applied:", d.get("fixes_applied"))
    print("pr_url:", d.get("pr_url"))

    vulns = d.get("vulnerabilities", [])
    print("top_vulns:", len(vulns))
    for v in vulns[:5]:
        print("-", v.get("id"), v.get("type"), v.get("severity"), v.get("file"), v.get("line"))

print("\nLOG_STATUS:", logs.status_code)
if logs.ok:
    lst = logs.json().get("logs", [])
    print("log_entries:", len(lst))
    for x in lst[-12:]:
        msg = (x.get("message") or "")[:140]
        print(f"{x.get('timestamp')} | {x.get('level')} | {x.get('source')} | {msg}")
