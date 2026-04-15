import sys
import requests

scan_id = sys.argv[1]
base = "http://localhost:8000"

logs_resp = requests.get(f"{base}/status/{scan_id}/logs", timeout=30)
detail_resp = requests.get(f"{base}/status/{scan_id}/detail", timeout=30)

print("logs_status:", logs_resp.status_code)
print("detail_status:", detail_resp.status_code)

if detail_resp.ok:
    d = detail_resp.json()
    print("status:", d.get("status"))
    print("current_phase:", d.get("current_phase"))
    print("error_message:", d.get("error_message"))
    print("pr_url:", d.get("pr_url"))
    print("vulnerabilities_found:", d.get("vulnerabilities_found"))
    print("fixes_applied:", d.get("fixes_applied"))

if logs_resp.ok:
    logs = logs_resp.json().get("logs", [])
    keys = [
        "pr",
        "pull request",
        "github",
        "token",
        "bad credentials",
        "401",
        "expired",
        "fork",
        "step 7/7",
        "no verified fix files",
    ]

    print("total_logs:", len(logs))
    matched = []
    for x in logs:
        msg = (x.get("message") or "").lower()
        if any(k in msg for k in keys):
            matched.append(x)

    print("matched_logs:", len(matched))
    for x in matched[-80:]:
        print(f"{x.get('timestamp')} | {x.get('level')} | {x.get('source')} | {(x.get('message') or '')}")
