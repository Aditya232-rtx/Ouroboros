import sys
import requests

scan_id = sys.argv[1]
base = "http://localhost:8000"

s = requests.get(f"{base}/status/{scan_id}", timeout=30)
d = requests.get(f"{base}/status/{scan_id}/detail", timeout=30)

sj = s.json() if s.ok else {}
dj = d.json() if d.ok else {}

print("status_code:", s.status_code)
print("status:", sj.get("status"))
print("phase:", sj.get("current_phase"))
print("detail_status:", d.status_code)
print("error_message:", dj.get("error_message"))
print("pr_url:", dj.get("pr_url"))
print("vulnerabilities_found:", dj.get("vulnerabilities_found"))
print("fixes_applied:", dj.get("fixes_applied"))
