import sys
import time
import requests

scan_id = sys.argv[1]
base = "http://localhost:8000"

start = time.time()
last = (None, None)

while True:
    s = requests.get(f"{base}/status/{scan_id}", timeout=30)
    s.raise_for_status()
    data = s.json()
    status = data.get("status")
    phase = data.get("current_phase")

    if (status, phase) != last:
        print(f"[{int(time.time()-start):4d}s] status={status} phase={phase} vulns={data.get('vulnerabilities_found')} fixes={data.get('fixes_applied')}")
        last = (status, phase)

    if status in ("completed", "failed"):
        break

    if time.time() - start > 5400:
        print("timeout waiting for completion")
        break

    time.sleep(10)

# final detail snapshot
r = requests.get(f"{base}/status/{scan_id}/detail", timeout=30)
print("detail_status:", r.status_code)
if r.ok:
    d = r.json()
    print("final_status:", d.get("status"))
    print("phase:", d.get("current_phase"))
    print("error_message:", d.get("error_message"))
    print("vulnerabilities_found:", d.get("vulnerabilities_found"))
    print("fixes_applied:", d.get("fixes_applied"))
    print("pr_url:", d.get("pr_url"))
