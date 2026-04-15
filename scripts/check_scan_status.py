import sys
import requests

scan_id = sys.argv[1]
base = "http://localhost:8000"

s = requests.get(f"{base}/status/{scan_id}", timeout=30)
d = requests.get(f"{base}/status/{scan_id}/detail", timeout=30)
l = requests.get(f"{base}/status/{scan_id}/logs", timeout=30)

print("STATUS", s.status_code, s.json().get("status"), s.json().get("current_phase"))
print("DETAIL", d.status_code)

jd = d.json() if d.ok else {}
print("FINAL", jd.get("status"))
print("PHASE", jd.get("current_phase"))
print("ERROR", jd.get("error_message"))
print("PR_URL", jd.get("pr_url"))
print("VULNS", jd.get("vulnerabilities_found"))
print("FIXES", jd.get("fixes_applied"))

logs = l.json().get("logs", []) if l.ok else []
print("LOGS", len(logs))
for x in logs[-10:]:
    msg = (x.get("message") or "")[:160]
    print(f"{x.get('timestamp')} | {x.get('level')} | {x.get('source')} | {msg}")
