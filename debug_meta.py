from src.database.session import SessionLocal
from src.database.models import Scan
from sqlalchemy import desc
import json

db = SessionLocal()
scan = db.query(Scan).order_by(desc(Scan.created_at)).first()

if scan:
    print(f"Scan ID: {scan.scan_id}")
    print(f"Status: {scan.status}")
    meta = scan.scan_metadata or {}
    print(f"Metadata Keys: {list(meta.keys())}")
    
    gov_queue = meta.get("governance_queue", [])
    print(f"Governance Queue Length: {len(gov_queue)}")
    
    if gov_queue:
        print("First Item Keys:", gov_queue[0].keys())
        if "original_vulnerability" in gov_queue[0]:
            print("Original Vuln Found: Yes")
        else:
            print("Original Vuln Found: NO")
            print("First Item Content:", json.dumps(gov_queue[0], indent=2))
else:
    print("No scan found")

db.close()
