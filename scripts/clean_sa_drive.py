#!/usr/bin/env python3
import pathlib
import sys
from pathlib import Path

# Setup path to import settings
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = str(settings.google_service_account_file)
SCOPES = ["https://www.googleapis.com/auth/drive"]

print(f"🧹 Starting cleanup for Service Account: {SERVICE_ACCOUNT_FILE}")

try:
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    drive = build("drive", "v3", credentials=creds)

    # ----- delete everything that is not trashed -----
    page_token = None
    count = 0
    while True:
        resp = drive.files().list(
            q="trashed = false",
            fields="nextPageToken, files(id, name)",
            pageToken=page_token,
            pageSize=1000
        ).execute()
        
        files = resp.get("files", [])
        if not files:
            print("No active files found to delete.")
            break
            
        for f in files:
            print(f"🗑 Deleting {f['name']} ({f['id']})")
            try:
                drive.files().delete(fileId=f["id"]).execute()
                count += 1
            except Exception as e:
                print(f"⚠️ Failed to delete {f['name']}: {e}")
                
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    # ----- empty the trash (just in case) -----
    print("🗑 Emptying trash...")
    drive.files().emptyTrash().execute()
    print(f"✅ Service‑account Drive is now EMPTY. Deleted {count} files.")

except Exception as e:
    print(f"❌ Cleanup Failed: {e}")
